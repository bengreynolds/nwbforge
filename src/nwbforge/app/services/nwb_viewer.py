"""Read-only NWB viewer services built on top of PyNWB."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable

from hdmf.common import DynamicTable
from hdmf.container import AbstractContainer
from pynwb import NWBHDF5IO, TimeSeries
from pynwb.file import NWBFile, Subject


@dataclass(frozen=True, slots=True)
class NwbViewerError(Exception):
    """User-facing error raised by the NWB viewer backend."""

    message: str
    detail: str | None = None

    def __str__(self) -> str:
        return self.message


@dataclass(frozen=True, slots=True)
class NwbTreeNode:
    """Normalized node used by the standalone NWB viewer tree."""

    label: str
    node_type: str
    path: str
    child_count: int
    object_ref: Any = field(repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class NwbDetailTable:
    """Tabular detail content for a selected NWB node."""

    headers: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]


@dataclass(frozen=True, slots=True)
class NwbNodeDetail:
    """Structured detail content for a selected NWB node."""

    title: str
    node_type: str
    path: str
    summary_rows: tuple[tuple[str, str], ...]
    text_content: str | None = None
    table: NwbDetailTable | None = None


class BaseNodeRenderer:
    """Backend renderer contract for node-detail generation."""

    def can_render(self, value: Any) -> bool:
        raise NotImplementedError

    def render(self, node: NwbTreeNode) -> NwbNodeDetail:
        raise NotImplementedError


class TimeSeriesRenderer(BaseNodeRenderer):
    """Detail renderer for NWB `TimeSeries` objects."""

    def can_render(self, value: Any) -> bool:
        return isinstance(value, TimeSeries)

    def render(self, node: NwbTreeNode) -> NwbNodeDetail:
        timeseries = node.object_ref
        summary_rows = (
            ("name", str(timeseries.name)),
            ("neurodata_type", type(timeseries).__name__),
            ("unit", _stringify_scalar(getattr(timeseries, "unit", None))),
            ("rate", _stringify_scalar(getattr(timeseries, "rate", None))),
            ("resolution", _stringify_scalar(getattr(timeseries, "resolution", None))),
            ("description", _stringify_scalar(getattr(timeseries, "description", None))),
            ("data", _array_summary(getattr(timeseries, "data", None))),
            ("timestamps", _array_summary(getattr(timeseries, "timestamps", None))),
        )
        preview_lines = [
            "Time series preview",
            f"data: {_array_preview(getattr(timeseries, 'data', None))}",
        ]
        timestamps = getattr(timeseries, "timestamps", None)
        if timestamps is not None:
            preview_lines.append(f"timestamps: {_array_preview(timestamps)}")
        return NwbNodeDetail(
            title=node.label,
            node_type=node.node_type,
            path=node.path,
            summary_rows=tuple((key, value) for key, value in summary_rows if value != ""),
            text_content="\n".join(preview_lines),
        )


class TableRenderer(BaseNodeRenderer):
    """Detail renderer for HDMF/NWB dynamic tables."""

    _max_rows = 25

    def can_render(self, value: Any) -> bool:
        return isinstance(value, DynamicTable)

    def render(self, node: NwbTreeNode) -> NwbNodeDetail:
        table = node.object_ref
        headers = tuple(str(name) for name in table.colnames)
        row_count = len(table.id[:]) if hasattr(table.id, "__getitem__") else len(table)
        preview_rows: list[tuple[str, ...]] = []
        preview_count = min(row_count, self._max_rows)
        for row_index in range(preview_count):
            preview_rows.append(
                tuple(_stringify_scalar(table[column][row_index]) for column in headers)
            )

        summary_rows = (
            ("name", str(table.name)),
            ("neurodata_type", type(table).__name__),
            ("rows", str(row_count)),
            ("columns", ", ".join(headers)),
        )
        return NwbNodeDetail(
            title=node.label,
            node_type=node.node_type,
            path=node.path,
            summary_rows=summary_rows,
            table=NwbDetailTable(headers=headers, rows=tuple(preview_rows)),
            text_content=None if row_count <= preview_count else f"Showing first {preview_count} of {row_count} rows.",
        )


class TextValueRenderer(BaseNodeRenderer):
    """Detail renderer for scalar and text values."""

    def can_render(self, value: Any) -> bool:
        return _is_scalar(value)

    def render(self, node: NwbTreeNode) -> NwbNodeDetail:
        value = node.object_ref
        return NwbNodeDetail(
            title=node.label,
            node_type=node.node_type,
            path=node.path,
            summary_rows=(("value", _stringify_scalar(value)),),
            text_content=_stringify_scalar(value),
        )


class ArrayRenderer(BaseNodeRenderer):
    """Detail renderer for arrays, datasets, and sequence-like values."""

    def can_render(self, value: Any) -> bool:
        return _is_array_like(value)

    def render(self, node: NwbTreeNode) -> NwbNodeDetail:
        value = node.object_ref
        return NwbNodeDetail(
            title=node.label,
            node_type=node.node_type,
            path=node.path,
            summary_rows=(("shape", _shape_string(value)), ("preview", _array_preview(value)),),
            text_content=_array_preview(value),
        )


class FallbackRenderer(BaseNodeRenderer):
    """Fallback detail renderer for mappings and NWB containers."""

    def can_render(self, value: Any) -> bool:
        return True

    def render(self, node: NwbTreeNode) -> NwbNodeDetail:
        value = node.object_ref
        summary_rows = _summarize_object_rows(value)
        if not summary_rows:
            summary_rows = (("summary", _describe_value(value)),)
        return NwbNodeDetail(
            title=node.label,
            node_type=node.node_type,
            path=node.path,
            summary_rows=summary_rows,
            text_content=_describe_value(value),
        )


class NwbTreeModel:
    """Lazy navigable tree model for a read-only `NWBFile`."""

    def __init__(self, nwbfile: NWBFile) -> None:
        self._nwbfile = nwbfile
        self._nodes: dict[str, NwbTreeNode] = {}
        self._child_loaders: dict[str, Callable[[], tuple[NwbTreeNode, ...]]] = {}
        self._children_cache: dict[str, tuple[NwbTreeNode, ...]] = {}
        self._root_nodes = self._register_children("/", self._build_root_nodes)

    @property
    def root_nodes(self) -> tuple[NwbTreeNode, ...]:
        return self._root_nodes

    @property
    def default_expanded_path(self) -> str | None:
        for node in self._root_nodes:
            if node.path == "/metadata":
                return node.path
        return self._root_nodes[0].path if self._root_nodes else None

    def node_for_path(self, path: str) -> NwbTreeNode:
        return self._nodes[path]

    def children_for_path(self, path: str) -> tuple[NwbTreeNode, ...]:
        if path in self._children_cache:
            return self._children_cache[path]
        loader = self._child_loaders.get(path)
        if loader is None:
            return ()
        children = loader()
        self._children_cache[path] = children
        return children

    def _register_node(
        self,
        *,
        label: str,
        object_ref: Any,
        path: str,
        child_loader: Callable[[], tuple[NwbTreeNode, ...]] | None = None,
        child_count: int | None = None,
    ) -> NwbTreeNode:
        resolved_child_count = child_count if child_count is not None else 0
        if child_loader is not None and child_count is None:
            resolved_child_count = 1
        node = NwbTreeNode(
            label=label,
            node_type=type(object_ref).__name__,
            path=path,
            child_count=resolved_child_count,
            object_ref=object_ref,
        )
        self._nodes[path] = node
        if child_loader is not None:
            self._child_loaders[path] = child_loader
        return node

    def _register_children(
        self,
        path: str,
        loader: Callable[[], tuple[NwbTreeNode, ...]],
    ) -> tuple[NwbTreeNode, ...]:
        self._child_loaders[path] = loader
        children = loader()
        self._children_cache[path] = children
        return children

    def _build_root_nodes(self) -> tuple[NwbTreeNode, ...]:
        nodes: list[NwbTreeNode] = [
            self._register_node(
                label="Metadata",
                object_ref=self._nwbfile,
                path="/metadata",
                child_loader=self._build_metadata_children,
                child_count=max(1, len(self._metadata_scalar_rows()) + int(self._nwbfile.subject is not None)),
            )
        ]

        section_specs = (
            ("Acquisition", getattr(self._nwbfile, "acquisition", None), "/acquisition"),
            ("Processing", getattr(self._nwbfile, "processing", None), "/processing"),
            ("Stimulus", getattr(self._nwbfile, "stimulus", None), "/stimulus"),
            ("Stimulus Templates", getattr(self._nwbfile, "stimulus_template", None), "/stimulus_template"),
            ("Intervals", self._build_interval_root(), "/intervals"),
            ("Analysis", getattr(self._nwbfile, "analysis", None), "/analysis"),
            ("Scratch", getattr(self._nwbfile, "scratch", None), "/scratch"),
            ("Lab Metadata", getattr(self._nwbfile, "lab_meta_data", None), "/lab_meta_data"),
        )
        for label, value, path in section_specs:
            if _is_empty(value):
                continue
            nodes.append(
                self._register_node(
                    label=label,
                    object_ref=value,
                    path=path,
                    child_loader=lambda value=value, path=path: self._build_children_for_value(value, path),
                    child_count=_child_count_hint(value),
                )
            )

        if getattr(self._nwbfile, "units", None) is not None:
            nodes.append(
                self._register_node(
                    label="Units",
                    object_ref=self._nwbfile.units,
                    path="/units",
                    child_loader=lambda: self._build_children_for_value(self._nwbfile.units, "/units"),
                    child_count=_child_count_hint(self._nwbfile.units),
                )
            )
        if getattr(self._nwbfile, "electrodes", None) is not None:
            nodes.append(
                self._register_node(
                    label="Electrodes",
                    object_ref=self._nwbfile.electrodes,
                    path="/electrodes",
                    child_loader=lambda: self._build_children_for_value(self._nwbfile.electrodes, "/electrodes"),
                    child_count=_child_count_hint(self._nwbfile.electrodes),
                )
            )

        return tuple(nodes)

    def _build_interval_root(self) -> dict[str, Any] | None:
        intervals: dict[str, Any] = {}
        if getattr(self._nwbfile, "trials", None) is not None:
            intervals["trials"] = self._nwbfile.trials
        interval_mapping = getattr(self._nwbfile, "intervals", None)
        if interval_mapping:
            for key, value in interval_mapping.items():
                if key == "trials":
                    continue
                intervals[str(key)] = value
        return intervals or None

    def _build_metadata_children(self) -> tuple[NwbTreeNode, ...]:
        children: list[NwbTreeNode] = []
        for key, value in self._metadata_scalar_rows():
            child_path = f"/metadata/{key}"
            children.append(self._register_leaf_node(label=key, object_ref=value, path=child_path))
        if self._nwbfile.subject is not None:
            children.append(
                self._register_node(
                    label="subject",
                    object_ref=self._nwbfile.subject,
                    path="/metadata/subject",
                    child_loader=lambda: self._build_children_for_value(self._nwbfile.subject, "/metadata/subject"),
                    child_count=_child_count_hint(self._nwbfile.subject),
                )
            )
        devices = getattr(self._nwbfile, "devices", None)
        if devices:
            children.append(
                self._register_node(
                    label="devices",
                    object_ref=devices,
                    path="/metadata/devices",
                    child_loader=lambda: self._build_children_for_value(devices, "/metadata/devices"),
                    child_count=_child_count_hint(devices),
                )
            )
        return tuple(children)

    def _metadata_scalar_rows(self) -> tuple[tuple[str, Any], ...]:
        return tuple(
            (key, value)
            for key, value in (
                ("identifier", getattr(self._nwbfile, "identifier", None)),
                ("session_description", getattr(self._nwbfile, "session_description", None)),
                ("session_start_time", getattr(self._nwbfile, "session_start_time", None)),
                ("session_id", getattr(self._nwbfile, "session_id", None)),
                ("experiment_description", getattr(self._nwbfile, "experiment_description", None)),
                ("experimenter", getattr(self._nwbfile, "experimenter", None)),
                ("institution", getattr(self._nwbfile, "institution", None)),
                ("lab", getattr(self._nwbfile, "lab", None)),
                ("keywords", getattr(self._nwbfile, "keywords", None)),
                ("notes", getattr(self._nwbfile, "notes", None)),
            )
            if not _is_empty(value)
        )

    def _build_children_for_value(self, value: Any, parent_path: str) -> tuple[NwbTreeNode, ...]:
        if _is_empty(value):
            return ()

        if isinstance(value, DynamicTable):
            children: list[NwbTreeNode] = []
            for column_name in value.colnames:
                column_path = f"{parent_path}/{column_name}"
                children.append(self._register_leaf_node(label=str(column_name), object_ref=value[column_name], path=column_path))
            return tuple(children)

        if _is_mapping_like(value):
            return tuple(
                self._register_generic_child(
                    label=str(key),
                    object_ref=child,
                    path=f"{parent_path}/{_sanitize_path_component(str(key))}",
                )
                for key, child in value.items()
            )

        if isinstance(value, Subject):
            return tuple(
                self._register_leaf_node(
                    label=key,
                    object_ref=getattr(value, key),
                    path=f"{parent_path}/{key}",
                )
                for key in (
                    "subject_id",
                    "species",
                    "sex",
                    "age",
                    "description",
                    "genotype",
                )
                if not _is_empty(getattr(value, key, None))
            )

        if isinstance(value, AbstractContainer):
            fields = _container_fields(value)
            return tuple(
                self._register_generic_child(
                    label=str(key),
                    object_ref=child,
                    path=f"{parent_path}/{_sanitize_path_component(str(key))}",
                )
                for key, child in fields
                if not _is_empty(child)
            )

        if isinstance(value, (list, tuple)):
            return tuple(
                self._register_generic_child(
                    label=f"[{index}]",
                    object_ref=child,
                    path=f"{parent_path}/{index}",
                )
                for index, child in enumerate(value)
            )

        return ()

    def _register_generic_child(self, *, label: str, object_ref: Any, path: str) -> NwbTreeNode:
        child_count = _child_count_hint(object_ref)
        if child_count > 0:
            return self._register_node(
                label=label,
                object_ref=object_ref,
                path=path,
                child_loader=lambda object_ref=object_ref, path=path: self._build_children_for_value(object_ref, path),
                child_count=child_count,
            )
        return self._register_leaf_node(label=label, object_ref=object_ref, path=path)

    def _register_leaf_node(self, *, label: str, object_ref: Any, path: str) -> NwbTreeNode:
        return self._register_node(
            label=label,
            object_ref=object_ref,
            path=path,
            child_loader=None,
            child_count=0,
        )


class NwbFileController:
    """Controller that owns read-only NWB file access and tree/detail conversion."""

    def __init__(self) -> None:
        self._io: NWBHDF5IO | None = None
        self._nwbfile: NWBFile | None = None
        self._file_path: Path | None = None
        self._tree_model: NwbTreeModel | None = None
        self._renderers: tuple[BaseNodeRenderer, ...] = (
            TimeSeriesRenderer(),
            TableRenderer(),
            TextValueRenderer(),
            ArrayRenderer(),
            FallbackRenderer(),
        )

    @property
    def file_path(self) -> Path | None:
        return self._file_path

    @property
    def nwbfile(self) -> NWBFile | None:
        return self._nwbfile

    @property
    def is_open(self) -> bool:
        return self._tree_model is not None

    @property
    def root_nodes(self) -> tuple[NwbTreeNode, ...]:
        return () if self._tree_model is None else self._tree_model.root_nodes

    @property
    def default_expanded_path(self) -> str | None:
        return None if self._tree_model is None else self._tree_model.default_expanded_path

    def open_file(self, file_path: Path) -> tuple[NwbTreeNode, ...]:
        resolved_path = file_path.resolve()
        if not resolved_path.exists():
            raise NwbViewerError("The selected NWB file does not exist.", str(resolved_path))
        if resolved_path.suffix.lower() != ".nwb":
            raise NwbViewerError("The selected file is not an NWB file.", str(resolved_path))
        if not NWBHDF5IO.can_read(path=str(resolved_path)):
            raise NwbViewerError("PyNWB could not read the selected NWB file.", str(resolved_path))

        self.close()
        try:
            io = NWBHDF5IO(path=str(resolved_path), mode="r", load_namespaces=True)
            nwbfile = io.read()
        except Exception as exc:  # pragma: no cover - exercised via wrapper tests
            raise NwbViewerError("Failed to open the NWB file for read-only viewing.", str(exc)) from exc

        self._io = io
        self._nwbfile = nwbfile
        self._file_path = resolved_path
        self._tree_model = NwbTreeModel(nwbfile)
        return self._tree_model.root_nodes

    def reload(self) -> tuple[NwbTreeNode, ...]:
        if self._file_path is None:
            raise NwbViewerError("No NWB file is currently loaded.")
        return self.open_file(self._file_path)

    def close(self) -> None:
        if self._io is not None:
            self._io.close()
        self._io = None
        self._nwbfile = None
        self._file_path = None
        self._tree_model = None

    def children_for_path(self, path: str) -> tuple[NwbTreeNode, ...]:
        if self._tree_model is None:
            return ()
        return self._tree_model.children_for_path(path)

    def detail_for_path(self, path: str) -> NwbNodeDetail:
        if self._tree_model is None:
            raise NwbViewerError("No NWB file is currently loaded.")
        node = self._tree_model.node_for_path(path)
        for renderer in self._renderers:
            if renderer.can_render(node.object_ref):
                return renderer.render(node)
        raise NwbViewerError("Could not render the selected NWB node.")


def _is_scalar(value: Any) -> bool:
    return isinstance(value, (str, bytes, int, float, bool, datetime, date)) or value is None


def _is_mapping_like(value: Any) -> bool:
    return hasattr(value, "items") and callable(value.items)


def _is_array_like(value: Any) -> bool:
    if value is None or isinstance(value, (str, bytes, DynamicTable, AbstractContainer)):
        return False
    return hasattr(value, "shape") or isinstance(value, (list, tuple))


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value == ""
    if isinstance(value, (list, tuple, dict)):
        return len(value) == 0
    if hasattr(value, "__len__") and not isinstance(value, (DynamicTable, AbstractContainer)):
        try:
            return len(value) == 0
        except TypeError:
            return False
    return False


def _child_count_hint(value: Any) -> int:
    if _is_empty(value):
        return 0
    if isinstance(value, DynamicTable):
        return len(value.colnames)
    if _is_mapping_like(value):
        try:
            return len(value)
        except TypeError:
            return 1
    if isinstance(value, Subject):
        return len([1 for key in ("subject_id", "species", "sex", "age", "description", "genotype") if not _is_empty(getattr(value, key, None))])
    if isinstance(value, AbstractContainer):
        return len(_container_fields(value))
    if isinstance(value, (list, tuple)):
        return len(value)
    return 0


def _sanitize_path_component(component: str) -> str:
    return component.replace("/", "_")


def _container_fields(container: AbstractContainer) -> tuple[tuple[str, Any], ...]:
    fields = getattr(container, "fields", {})
    if hasattr(fields, "items"):
        return tuple(
            (str(key), value)
            for key, value in fields.items()
            if key not in {"parent", "children"}
        )
    return ()


def _describe_value(value: Any) -> str:
    if isinstance(value, DynamicTable):
        return f"{type(value).__name__} with {len(value)} rows"
    if isinstance(value, AbstractContainer):
        name = getattr(value, "name", None)
        return f"{type(value).__name__}{f' ({name})' if name else ''}"
    if _is_mapping_like(value):
        try:
            return f"Mapping with {len(value)} entries"
        except TypeError:
            return "Mapping"
    if _is_array_like(value):
        return _array_summary(value)
    return _stringify_scalar(value)


def _summarize_object_rows(value: Any) -> tuple[tuple[str, str], ...]:
    if isinstance(value, NWBFile):
        return tuple((key, _stringify_scalar(item)) for key, item in (
            ("identifier", value.identifier),
            ("session_description", value.session_description),
            ("session_start_time", value.session_start_time),
        ))
    if isinstance(value, AbstractContainer):
        rows = [("name", _stringify_scalar(getattr(value, "name", None))), ("type", type(value).__name__)]
        for key, child in _container_fields(value):
            if _is_scalar(child) or _is_array_like(child):
                rows.append((key, _describe_value(child)))
        return tuple((key, val) for key, val in rows if val != "")
    if _is_mapping_like(value):
        return tuple((str(key), _describe_value(child)) for key, child in value.items())
    return ()


def _stringify_scalar(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, (tuple, list)):
        return ", ".join(_stringify_scalar(item) for item in value[:10])
    return str(value)


def _shape_string(value: Any) -> str:
    shape = getattr(value, "shape", None)
    if shape is not None:
        return str(tuple(shape))
    if isinstance(value, (list, tuple)):
        return f"({len(value)},)"
    return ""


def _array_summary(value: Any) -> str:
    if value is None:
        return ""
    shape_text = _shape_string(value)
    type_text = type(value).__name__
    if shape_text:
        return f"{type_text} {shape_text}"
    return type_text


def _array_preview(value: Any, *, max_items: int = 8) -> str:
    if value is None:
        return ""
    try:
        if hasattr(value, "shape"):
            shape = tuple(value.shape)
            if len(shape) == 0:
                sample = value[()]
            elif len(shape) == 1:
                sample = value[: min(shape[0], max_items)]
            else:
                sample = value[: min(shape[0], max_items)]
            return repr(sample)
        if isinstance(value, (list, tuple)):
            return repr(value[:max_items])
    except Exception:  # pragma: no cover - defensive preview fallback
        return _array_summary(value)
    return repr(value)
