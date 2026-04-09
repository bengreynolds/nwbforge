"""Read-only local file preview helpers for desktop review surfaces."""

from __future__ import annotations

from csv import Sniffer, reader
from dataclasses import dataclass
from enum import StrEnum
import mimetypes
from pathlib import Path


class FilePreviewKind(StrEnum):
    """Supported file-preview content kinds."""

    EMPTY = "empty"
    MISSING = "missing"
    ERROR = "error"
    DIRECTORY = "directory"
    TEXT = "text"
    TABLE = "table"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    NWB = "nwb"
    BINARY = "binary"


@dataclass(frozen=True, slots=True)
class FilePreviewTable:
    """A bounded tabular preview."""

    headers: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]


@dataclass(frozen=True, slots=True)
class FilePreviewResult:
    """Structured file-preview payload for widget rendering."""

    kind: FilePreviewKind
    path: Path | None
    title: str
    summary: str
    metadata_lines: tuple[str, ...] = ()
    text_content: str | None = None
    table: FilePreviewTable | None = None
    media_path: Path | None = None


class LocalFilePreviewService:
    """Build small read-only previews for common local file types."""

    _TEXT_SUFFIXES = {
        ".cfg",
        ".csv",
        ".ini",
        ".json",
        ".log",
        ".md",
        ".py",
        ".rst",
        ".text",
        ".toml",
        ".tsv",
        ".txt",
        ".xml",
        ".yaml",
        ".yml",
    }
    _TABLE_SUFFIXES = {".csv", ".tsv", ".tab"}
    _IMAGE_SUFFIXES = {
        ".bmp",
        ".gif",
        ".jpeg",
        ".jpg",
        ".png",
        ".tif",
        ".tiff",
        ".webp",
    }
    _VIDEO_SUFFIXES = {".avi", ".m4v", ".mkv", ".mov", ".mp4", ".mpeg", ".mpg", ".wmv"}
    _AUDIO_SUFFIXES = {".aac", ".flac", ".m4a", ".mp3", ".ogg", ".wav", ".wma"}
    _TEXT_READ_LIMIT = 16_384
    _TABLE_ROW_LIMIT = 20
    _TABLE_COLUMN_LIMIT = 8
    _DIRECTORY_ENTRY_LIMIT = 40

    def build_preview(self, path: Path | None) -> FilePreviewResult:
        """Return a bounded preview for the given path."""

        if path is None:
            return FilePreviewResult(
                kind=FilePreviewKind.EMPTY,
                path=None,
                title="No file selected",
                summary="Select a source or artifact to preview it here.",
            )

        resolved = path.resolve()
        if not resolved.exists():
            return FilePreviewResult(
                kind=FilePreviewKind.MISSING,
                path=resolved,
                title=resolved.name,
                summary="The selected path no longer exists.",
                metadata_lines=(str(resolved),),
            )

        try:
            stat = resolved.stat()
        except OSError as exc:
            return FilePreviewResult(
                kind=FilePreviewKind.ERROR,
                path=resolved,
                title=resolved.name,
                summary=f"Preview failed: {exc}",
                metadata_lines=(str(resolved),),
            )

        metadata_lines = self._metadata_lines(resolved, stat.st_size)
        try:
            if resolved.is_dir():
                return self._directory_preview(resolved, metadata_lines)

            suffix = resolved.suffix.lower()
            if suffix == ".nwb":
                return FilePreviewResult(
                    kind=FilePreviewKind.NWB,
                    path=resolved,
                    title=resolved.name,
                    summary="Use the integrated NWB viewer for structured NWB inspection.",
                    metadata_lines=metadata_lines,
                )
            if suffix in self._TABLE_SUFFIXES:
                return self._table_preview(resolved, metadata_lines)
            if suffix in self._IMAGE_SUFFIXES:
                return FilePreviewResult(
                    kind=FilePreviewKind.IMAGE,
                    path=resolved,
                    title=resolved.name,
                    summary="Image preview loaded from the selected file.",
                    metadata_lines=metadata_lines,
                    media_path=resolved,
                )
            if suffix in self._VIDEO_SUFFIXES:
                return FilePreviewResult(
                    kind=FilePreviewKind.VIDEO,
                    path=resolved,
                    title=resolved.name,
                    summary="Video preview loaded from the selected file.",
                    metadata_lines=metadata_lines,
                    media_path=resolved,
                )
            if suffix in self._AUDIO_SUFFIXES:
                return FilePreviewResult(
                    kind=FilePreviewKind.AUDIO,
                    path=resolved,
                    title=resolved.name,
                    summary="Audio preview loaded from the selected file.",
                    metadata_lines=metadata_lines,
                    media_path=resolved,
                )
            if self._looks_like_text(resolved, suffix):
                return self._text_preview(resolved, metadata_lines)
            return FilePreviewResult(
                kind=FilePreviewKind.BINARY,
                path=resolved,
                title=resolved.name,
                summary="Binary or unsupported preview format. Metadata only.",
                metadata_lines=metadata_lines,
            )
        except Exception as exc:
            return FilePreviewResult(
                kind=FilePreviewKind.ERROR,
                path=resolved,
                title=resolved.name,
                summary=f"Preview failed: {exc}",
                metadata_lines=metadata_lines,
            )

    def _directory_preview(self, path: Path, metadata_lines: tuple[str, ...]) -> FilePreviewResult:
        entries = sorted(path.iterdir(), key=lambda item: (item.is_file(), item.name.lower()))
        displayed_entries = entries[: self._DIRECTORY_ENTRY_LIMIT]
        lines = [
            f"{'[dir]' if entry.is_dir() else '[file]'} {entry.name}"
            for entry in displayed_entries
        ]
        if len(entries) > len(displayed_entries):
            lines.append(f"... and {len(entries) - len(displayed_entries)} more entries")
        return FilePreviewResult(
            kind=FilePreviewKind.DIRECTORY,
            path=path,
            title=path.name,
            summary=f"Directory preview with {len(entries)} visible entries.",
            metadata_lines=metadata_lines,
            text_content="\n".join(lines) if lines else "Directory is empty.",
        )

    def _text_preview(self, path: Path, metadata_lines: tuple[str, ...]) -> FilePreviewResult:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            text = handle.read(self._TEXT_READ_LIMIT + 1)
        truncated = len(text) > self._TEXT_READ_LIMIT
        if truncated:
            text = text[: self._TEXT_READ_LIMIT]
        summary = "Text preview loaded."
        if truncated:
            summary = "Text preview loaded. Showing the first portion of the file."
        return FilePreviewResult(
            kind=FilePreviewKind.TEXT,
            path=path,
            title=path.name,
            summary=summary,
            metadata_lines=metadata_lines,
            text_content=text,
        )

    def _table_preview(self, path: Path, metadata_lines: tuple[str, ...]) -> FilePreviewResult:
        with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
            sample = handle.read(2048)
            handle.seek(0)
            delimiter = self._detect_table_delimiter(path, sample)
            parsed_rows = list(
                self._bounded_rows(reader(handle, delimiter=delimiter))
            )
        if not parsed_rows:
            return FilePreviewResult(
                kind=FilePreviewKind.TABLE,
                path=path,
                title=path.name,
                summary="Tabular file is empty.",
                metadata_lines=metadata_lines,
                table=FilePreviewTable(headers=(), rows=()),
            )
        header_row = self._normalize_table_row(parsed_rows[0])
        data_rows = tuple(self._normalize_table_row(row) for row in parsed_rows[1:])
        summary = f"Tabular preview loaded with delimiter '{delimiter}'."
        if len(parsed_rows) > self._TABLE_ROW_LIMIT:
            summary = "Tabular preview loaded. Showing the first rows only."
        return FilePreviewResult(
            kind=FilePreviewKind.TABLE,
            path=path,
            title=path.name,
            summary=summary,
            metadata_lines=metadata_lines,
            table=FilePreviewTable(headers=header_row, rows=data_rows),
        )

    @classmethod
    def _bounded_rows(cls, rows) -> tuple[tuple[str, ...], ...]:
        captured: list[tuple[str, ...]] = []
        for row in rows:
            captured.append(tuple(str(value) for value in row[: cls._TABLE_COLUMN_LIMIT]))
            if len(captured) >= cls._TABLE_ROW_LIMIT + 1:
                break
        return tuple(captured)

    @classmethod
    def _normalize_table_row(cls, row: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(value.strip() for value in row[: cls._TABLE_COLUMN_LIMIT])
        if not normalized:
            return ()
        return normalized

    @classmethod
    def _detect_table_delimiter(cls, path: Path, sample: str) -> str:
        if path.suffix.lower() in {".tsv", ".tab"}:
            return "\t"
        try:
            dialect = Sniffer().sniff(sample, delimiters=",\t;")
        except Exception:
            return ","
        return str(dialect.delimiter or ",")

    @classmethod
    def _looks_like_text(cls, path: Path, suffix: str) -> bool:
        if suffix in cls._TEXT_SUFFIXES:
            return True
        guessed_type, _ = mimetypes.guess_type(path.name)
        if guessed_type is not None and (
            guessed_type.startswith("text/")
            or guessed_type in {"application/json", "application/xml"}
        ):
            return True
        try:
            sample = path.read_bytes()[:1024]
        except OSError:
            return False
        if not sample:
            return True
        if b"\x00" in sample:
            return False
        try:
            sample.decode("utf-8")
        except UnicodeDecodeError:
            return False
        return True

    @staticmethod
    def _metadata_lines(path: Path, size_bytes: int) -> tuple[str, ...]:
        return (
            str(path),
            f"Type: {'Directory' if path.is_dir() else 'File'}",
            f"Size: {LocalFilePreviewService._format_size(size_bytes)}",
        )

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        thresholds = ("B", "KB", "MB", "GB")
        size = float(size_bytes)
        for unit in thresholds:
            if size < 1024 or unit == thresholds[-1]:
                if unit == "B":
                    return f"{int(size)} {unit}"
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size_bytes} B"
