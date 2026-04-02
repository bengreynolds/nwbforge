"""NeuroConv-backed adapters for supported ecephys routes."""

from __future__ import annotations

import re
from pathlib import Path

try:
    from neuroconv.datainterfaces import AlphaOmegaRecordingInterface
except ImportError:  # pragma: no cover - optional route dependency gate
    AlphaOmegaRecordingInterface = None

try:
    from neuroconv.datainterfaces import AxonRecordingInterface
except ImportError:  # pragma: no cover - optional route dependency gate
    AxonRecordingInterface = None

try:
    from neuroconv.datainterfaces import AxonaRecordingInterface
except ImportError:  # pragma: no cover - optional route dependency gate
    AxonaRecordingInterface = None

try:
    from neuroconv.datainterfaces import BlackrockRecordingInterface
except ImportError:  # pragma: no cover - optional route dependency gate
    BlackrockRecordingInterface = None

try:
    from neuroconv.datainterfaces import EDFRecordingInterface
except ImportError:  # pragma: no cover - optional route dependency gate
    EDFRecordingInterface = None

try:
    from neuroconv.datainterfaces import IntanRecordingInterface
except ImportError:  # pragma: no cover - optional route dependency gate
    IntanRecordingInterface = None

try:
    from neuroconv.datainterfaces import NeuralynxRecordingInterface
except ImportError:  # pragma: no cover - optional route dependency gate
    NeuralynxRecordingInterface = None

try:
    from neuroconv.datainterfaces import OpenEphysBinaryRecordingInterface
except ImportError:  # pragma: no cover - optional route dependency gate
    OpenEphysBinaryRecordingInterface = None

try:
    from neuroconv.datainterfaces import OpenEphysLegacyRecordingInterface
except ImportError:  # pragma: no cover - optional route dependency gate
    OpenEphysLegacyRecordingInterface = None

try:
    from neuroconv.datainterfaces import PlexonRecordingInterface
except ImportError:  # pragma: no cover - optional route dependency gate
    PlexonRecordingInterface = None

try:
    from neuroconv.datainterfaces import SpikeGadgetsRecordingInterface
except ImportError:  # pragma: no cover - optional route dependency gate
    SpikeGadgetsRecordingInterface = None

try:
    from neuroconv.datainterfaces import SpikeGLXRecordingInterface
except ImportError:  # pragma: no cover - optional route dependency gate
    SpikeGLXRecordingInterface = None

try:
    from neuroconv.datainterfaces import TdtRecordingInterface
except ImportError:  # pragma: no cover - optional route dependency gate
    TdtRecordingInterface = None

try:
    from neuroconv.datainterfaces import WhiteMatterRecordingInterface
except ImportError:  # pragma: no cover - optional route dependency gate
    WhiteMatterRecordingInterface = None

from nwbforge.adapters.base import AdapterCapabilities
from nwbforge.adapters.neuroconv import (
    NeuroConvDirectConversionAdapter,
    NeuroConvSourceConfig,
    extracted_fields_from_mapping,
)
from nwbforge.domain.enums import ConversionPathway, SourceType
from nwbforge.domain.models import ExtractedField, ReviewIssue, SourceReference


def _directory_has_any_suffix(folder_path: Path, suffixes: tuple[str, ...]) -> bool:
    return any(path.is_file() and path.suffix.lower() in suffixes for path in folder_path.rglob("*"))


def _config_has_keys(config: NeuroConvSourceConfig, required_keys: tuple[str, ...]) -> bool:
    return all(key in config.interface_kwargs for key in required_keys)


class _NeuroConvEcephysRecordingAdapter(NeuroConvDirectConversionAdapter):
    """Shared extraction helpers for NeuroConv-backed ecephys recording routes."""

    extraction_prefix = "ecephys.generic"
    default_device_name = "RecordingDevice"
    source_format = "recording"

    def extract(
        self,
        *,
        source: SourceReference,
        interface,
        config: NeuroConvSourceConfig,
    ) -> tuple[dict[str, ExtractedField], list[ReviewIssue], tuple[str, ...]]:
        metadata = interface.get_metadata()
        ecephys_metadata = metadata.get("Ecephys", {})
        device_metadata = ecephys_metadata.get("Device") or [{}]
        electrode_groups = ecephys_metadata.get("ElectrodeGroup") or ()
        fields = extracted_fields_from_mapping(
            prefix=self.extraction_prefix,
            payload={
                "source_format": self.source_format,
                "device_name": device_metadata[0].get("name", self.default_device_name),
                "electrode_group_count": len(electrode_groups),
                "electrical_series_name": config.interface_kwargs.get("es_key", "ElectricalSeries"),
                "has_session_start_time": "session_start_time" in metadata.get("NWBFile", {}),
                **self.additional_payload(source=source, metadata=metadata, config=config),
            },
            source_id=source.source_id,
        )
        return fields, [], self.extraction_notes()

    def additional_payload(
        self,
        *,
        source: SourceReference,
        metadata: dict[str, object],
        config: NeuroConvSourceConfig,
    ) -> dict[str, object]:
        del source, metadata, config
        return {}

    def extraction_notes(self) -> tuple[str, ...]:
        return ("Prepared NeuroConv ecephys conversion into acquisition data.",)


if AlphaOmegaRecordingInterface is not None:

    class NeuroConvAlphaOmegaAdapter(_NeuroConvEcephysRecordingAdapter):
        """Inspect and convert AlphaOmega folders through NeuroConv."""

        adapter_id = "neuroconv_alphaomega"
        display_name = "NeuroConv AlphaOmega adapter"
        version = "0.1.0"
        interface_cls = AlphaOmegaRecordingInterface
        source_path_kwarg = "folder_path"
        record_type = "neuroconv_alphaomega"
        source_types = (SourceType.DIRECTORY,)
        capabilities = AdapterCapabilities(
            supported_pathways=(ConversionPathway.SUPPORTED,),
            supports_multi_source_sessions=True,
        )
        extraction_prefix = "ecephys.alphaomega"
        default_device_name = "AlphaOmega"
        source_format = "alphaomega_folder"

        def matches_source(self, source: SourceReference, config: NeuroConvSourceConfig) -> bool:
            del config
            return source.location.is_dir() and _directory_has_any_suffix(source.location, (".mpx",))

        def additional_payload(
            self,
            *,
            source: SourceReference,
            metadata: dict[str, object],
            config: NeuroConvSourceConfig,
        ) -> dict[str, object]:
            del metadata, config
            mpx_count = sum(1 for path in source.location.rglob("*") if path.is_file() and path.suffix.lower() == ".mpx")
            return {
                "stream_id": "RAW",
                "mpx_file_count": mpx_count,
            }

        def extraction_notes(self) -> tuple[str, ...]:
            return (
                "Prepared NeuroConv AlphaOmega conversion into ecephys acquisition data.",
                "AlphaOmega route matching prefers directories containing distinctive .mpx files.",
            )


if AxonRecordingInterface is not None:

    class NeuroConvAxonAdapter(_NeuroConvEcephysRecordingAdapter):
        """Inspect and convert Axon/ABF sources through NeuroConv."""

        adapter_id = "neuroconv_axon"
        display_name = "NeuroConv Axon adapter"
        version = "0.1.0"
        interface_cls = AxonRecordingInterface
        record_type = "neuroconv_axon"
        source_types = (SourceType.FILE,)
        capabilities = AdapterCapabilities(
            supported_pathways=(ConversionPathway.SUPPORTED,),
            supports_multi_source_sessions=True,
        )
        supported_suffixes = (".abf",)
        extraction_prefix = "ecephys.axon"
        default_device_name = "Axon Instruments"
        source_format = "abf"

        def matches_source(self, source: SourceReference, config: NeuroConvSourceConfig) -> bool:
            del config
            return source.location.suffix.lower() in self.supported_suffixes

        def extraction_notes(self) -> tuple[str, ...]:
            return (
                "Prepared NeuroConv Axon conversion into ecephys acquisition data.",
                "Axon route matching prefers distinctive .abf files rather than generic electrophysiology readers.",
            )


if AxonaRecordingInterface is not None:

    class NeuroConvAxonaAdapter(_NeuroConvEcephysRecordingAdapter):
        """Inspect and convert Axona sources through NeuroConv."""

        adapter_id = "neuroconv_axona"
        display_name = "NeuroConv Axona adapter"
        version = "0.1.0"
        interface_cls = AxonaRecordingInterface
        record_type = "neuroconv_axona"
        source_types = (SourceType.FILE,)
        capabilities = AdapterCapabilities(
            supported_pathways=(ConversionPathway.SUPPORTED,),
            supports_multi_source_sessions=True,
        )
        supported_suffixes = (".set", ".bin")
        extraction_prefix = "ecephys.axona"
        default_device_name = "Axona"
        source_format = "axona"

        def matches_source(self, source: SourceReference, config: NeuroConvSourceConfig) -> bool:
            del config
            suffix = source.location.suffix.lower()
            if suffix == ".set":
                return True
            if suffix == ".bin":
                return source.location.with_suffix(".set").exists()
            return False

        def additional_payload(
            self,
            *,
            source: SourceReference,
            metadata: dict[str, object],
            config: NeuroConvSourceConfig,
        ) -> dict[str, object]:
            del metadata, config
            return {
                "source_format": source.location.suffix.lower().lstrip("."),
                "has_set_sidecar": source.location.with_suffix(".set").exists(),
            }

        def extraction_notes(self) -> tuple[str, ...]:
            return (
                "Prepared NeuroConv Axona conversion into ecephys acquisition data.",
                "Axona route matching prefers .set files or .bin files with a sibling .set descriptor to avoid generic binary collisions.",
            )


if BlackrockRecordingInterface is not None:

    class NeuroConvBlackrockAdapter(_NeuroConvEcephysRecordingAdapter):
        """Inspect and convert Blackrock NSx sources through NeuroConv."""

        adapter_id = "neuroconv_blackrock"
        display_name = "NeuroConv Blackrock adapter"
        version = "0.1.0"
        interface_cls = BlackrockRecordingInterface
        record_type = "neuroconv_blackrock"
        source_types = (SourceType.FILE,)
        capabilities = AdapterCapabilities(
            supported_pathways=(ConversionPathway.SUPPORTED,),
            supports_multi_source_sessions=True,
        )
        supported_suffixes = (".ns0", ".ns1", ".ns2", ".ns3", ".ns4", ".ns5", ".ns6")
        extraction_prefix = "ecephys.blackrock"
        default_device_name = "Blackrock"
        source_format = "blackrock_nsx"

        def matches_source(self, source: SourceReference, config: NeuroConvSourceConfig) -> bool:
            del config
            return source.location.suffix.lower() in self.supported_suffixes

        def additional_payload(
            self,
            *,
            source: SourceReference,
            metadata: dict[str, object],
            config: NeuroConvSourceConfig,
        ) -> dict[str, object]:
            del metadata
            return {
                "nsx_suffix": source.location.suffix.lower(),
                "has_nsx_override": "nsx_override" in config.interface_kwargs,
            }

        def extraction_notes(self) -> tuple[str, ...]:
            return (
                "Prepared NeuroConv Blackrock conversion into ecephys acquisition data.",
                "Blackrock route matching prefers distinctive .nsx recording files rather than .nev spike-sorting files.",
            )


if EDFRecordingInterface is not None:

    class NeuroConvEdfAdapter(_NeuroConvEcephysRecordingAdapter):
        """Inspect and convert EDF sources through NeuroConv."""

        adapter_id = "neuroconv_edf"
        display_name = "NeuroConv EDF adapter"
        version = "0.1.0"
        interface_cls = EDFRecordingInterface
        record_type = "neuroconv_edf"
        source_types = (SourceType.FILE,)
        capabilities = AdapterCapabilities(
            supported_pathways=(ConversionPathway.SUPPORTED,),
            supports_multi_source_sessions=True,
        )
        supported_suffixes = (".edf",)
        extraction_prefix = "ecephys.edf"
        default_device_name = "EDF Recording"
        source_format = "edf"

        def matches_source(self, source: SourceReference, config: NeuroConvSourceConfig) -> bool:
            del config
            return source.location.suffix.lower() in self.supported_suffixes

        def additional_payload(
            self,
            *,
            source: SourceReference,
            metadata: dict[str, object],
            config: NeuroConvSourceConfig,
        ) -> dict[str, object]:
            del source, metadata
            channels_to_skip = tuple(config.interface_kwargs.get("channels_to_skip", ()))
            return {"channels_to_skip_count": len(channels_to_skip)}

        def extraction_notes(self) -> tuple[str, ...]:
            return (
                "Prepared NeuroConv EDF conversion into ecephys acquisition data.",
                "EDF route matching prefers distinctive .edf files and can skip configured non-neural channels.",
            )


if IntanRecordingInterface is not None:

    class NeuroConvIntanAdapter(_NeuroConvEcephysRecordingAdapter):
        """Inspect and convert Intan `.rhd` and `.rhs` sources through NeuroConv."""

        adapter_id = "neuroconv_intan"
        display_name = "NeuroConv Intan adapter"
        version = "0.1.0"
        interface_cls = IntanRecordingInterface
        record_type = "neuroconv_intan"
        source_types = (SourceType.FILE,)
        capabilities = AdapterCapabilities(
            supported_pathways=(ConversionPathway.SUPPORTED,),
            supports_multi_source_sessions=True,
        )
        supported_suffixes = (".rhd", ".rhs")
        extraction_prefix = "ecephys.intan"
        default_device_name = "Intan"
        source_format = "intan"

        def matches_source(self, source: SourceReference, config: NeuroConvSourceConfig) -> bool:
            del config
            return source.location.suffix.lower() in self.supported_suffixes

        def additional_payload(
            self,
            *,
            source: SourceReference,
            metadata: dict[str, object],
            config: NeuroConvSourceConfig,
        ) -> dict[str, object]:
            del metadata
            return {
                "source_format": source.location.suffix.lower().lstrip("."),
                "ignore_integrity_checks": bool(config.interface_kwargs.get("ignore_integrity_checks", False)),
            }

        def extraction_notes(self) -> tuple[str, ...]:
            return (
                "Prepared NeuroConv Intan conversion into ecephys acquisition data.",
                "Intan route matching prefers distinctive .rhd and .rhs acquisition files rather than broader ecephys catch-all readers.",
            )


if NeuralynxRecordingInterface is not None:

    class NeuroConvNeuralynxAdapter(_NeuroConvEcephysRecordingAdapter):
        """Inspect and convert Neuralynx folders through NeuroConv."""

        adapter_id = "neuroconv_neuralynx"
        display_name = "NeuroConv Neuralynx adapter"
        version = "0.1.0"
        interface_cls = NeuralynxRecordingInterface
        source_path_kwarg = "folder_path"
        record_type = "neuroconv_neuralynx"
        source_types = (SourceType.DIRECTORY,)
        capabilities = AdapterCapabilities(
            supported_pathways=(ConversionPathway.SUPPORTED,),
            supports_multi_source_sessions=True,
        )
        extraction_prefix = "ecephys.neuralynx"
        default_device_name = "Neuralynx"
        source_format = "neuralynx_folder"
        _SIGNATURE_SUFFIXES = (".ncs", ".nse", ".ntt", ".nev")

        def matches_source(self, source: SourceReference, config: NeuroConvSourceConfig) -> bool:
            if not source.location.is_dir() or not _directory_has_any_suffix(source.location, self._SIGNATURE_SUFFIXES):
                return False
            if config.interface_kwargs.get("stream_name") is not None:
                return True
            try:
                return len(self.interface_cls.get_stream_names(folder_path=source.location)) <= 1
            except Exception:
                return False

        def build_interface(self, source: SourceReference, config: NeuroConvSourceConfig):
            interface_kwargs = {"folder_path": source.location}
            interface_kwargs.update(config.interface_kwargs)
            interface_kwargs.setdefault("verbose", False)
            return self.interface_cls(**interface_kwargs)

        def additional_payload(
            self,
            *,
            source: SourceReference,
            metadata: dict[str, object],
            config: NeuroConvSourceConfig,
        ) -> dict[str, object]:
            del source, metadata
            return {
                "stream_name": config.interface_kwargs.get("stream_name"),
            }

        def extraction_notes(self) -> tuple[str, ...]:
            return (
                "Prepared NeuroConv Neuralynx conversion into ecephys acquisition data.",
                "Neuralynx route matching prefers directories containing Neuralynx stream files and requires stream selection only when multiple streams are detected.",
            )


if OpenEphysBinaryRecordingInterface is not None:

    class NeuroConvOpenEphysBinaryAdapter(_NeuroConvEcephysRecordingAdapter):
        """Inspect and convert OpenEphys Binary folders through NeuroConv."""

        adapter_id = "neuroconv_openephys_binary"
        display_name = "NeuroConv OpenEphys Binary adapter"
        version = "0.1.0"
        interface_cls = OpenEphysBinaryRecordingInterface
        record_type = "neuroconv_openephys_binary"
        source_types = (SourceType.DIRECTORY,)
        capabilities = AdapterCapabilities(
            supported_pathways=(ConversionPathway.SUPPORTED,),
            supports_multi_source_sessions=True,
        )
        extraction_prefix = "ecephys.openephys_binary"
        default_device_name = "OpenEphys Binary"
        source_format = "openephys_binary"

        def matches_source(self, source: SourceReference, config: NeuroConvSourceConfig) -> bool:
            if not source.location.is_dir() or not any(source.location.glob("**/*.oebin")):
                return False
            stream_name = config.interface_kwargs.get("stream_name")
            if stream_name is not None:
                return True
            try:
                return len(self.interface_cls.get_stream_names(folder_path=source.location)) <= 1
            except Exception:
                return False

        def build_interface(self, source: SourceReference, config: NeuroConvSourceConfig):
            interface_kwargs = {"folder_path": source.location}
            interface_kwargs.update(config.interface_kwargs)
            interface_kwargs.setdefault("verbose", False)
            return self.interface_cls(**interface_kwargs)

        def additional_payload(
            self,
            *,
            source: SourceReference,
            metadata: dict[str, object],
            config: NeuroConvSourceConfig,
        ) -> dict[str, object]:
            del source, metadata
            return {
                "stream_name": config.interface_kwargs.get("stream_name"),
                "block_index": config.interface_kwargs.get("block_index"),
            }

        def extraction_notes(self) -> tuple[str, ...]:
            return (
                "Prepared NeuroConv OpenEphys Binary conversion into ecephys acquisition data.",
                "OpenEphys Binary route matching prefers directories with .oebin manifests instead of generic .dat files.",
            )


if SpikeGadgetsRecordingInterface is not None:

    class NeuroConvSpikeGadgetsAdapter(_NeuroConvEcephysRecordingAdapter):
        """Inspect and convert SpikeGadgets `.rec` sources through NeuroConv."""

        adapter_id = "neuroconv_spikegadgets"
        display_name = "NeuroConv SpikeGadgets adapter"
        version = "0.1.0"
        interface_cls = SpikeGadgetsRecordingInterface
        record_type = "neuroconv_spikegadgets"
        source_types = (SourceType.FILE,)
        capabilities = AdapterCapabilities(
            supported_pathways=(ConversionPathway.SUPPORTED,),
            supports_multi_source_sessions=True,
        )
        supported_suffixes = (".rec",)
        extraction_prefix = "ecephys.spikegadgets"
        default_device_name = "SpikeGadgets"
        source_format = "spikegadgets_rec"

        def matches_source(self, source: SourceReference, config: NeuroConvSourceConfig) -> bool:
            del config
            return source.location.suffix.lower() in self.supported_suffixes

        def additional_payload(
            self,
            *,
            source: SourceReference,
            metadata: dict[str, object],
            config: NeuroConvSourceConfig,
        ) -> dict[str, object]:
            del source, metadata
            gains = config.interface_kwargs.get("gains")
            return {
                "stream_id": config.interface_kwargs.get("stream_id", "trodes"),
                "has_manual_gains": gains is not None,
            }

        def extraction_notes(self) -> tuple[str, ...]:
            return (
                "Prepared NeuroConv SpikeGadgets conversion into ecephys acquisition data.",
                "SpikeGadgets route matching prefers distinctive .rec files.",
            )


if SpikeGLXRecordingInterface is not None:

    class NeuroConvSpikeGLXAdapter(_NeuroConvEcephysRecordingAdapter):
        """Inspect and convert SpikeGLX recording folders through NeuroConv."""

        adapter_id = "neuroconv_spikeglx"
        display_name = "NeuroConv SpikeGLX adapter"
        version = "0.1.0"
        interface_cls = SpikeGLXRecordingInterface
        record_type = "neuroconv_spikeglx"
        source_types = (SourceType.DIRECTORY,)
        capabilities = AdapterCapabilities(
            supported_pathways=(ConversionPathway.SUPPORTED,),
            supports_multi_source_sessions=True,
        )
        extraction_prefix = "ecephys.spikeglx"
        default_device_name = "Neuropixels"
        source_format = "spikeglx_folder"
        _STREAM_PATTERN = re.compile(r"(imec\d+\.(?:ap|lf))", re.IGNORECASE)

        def matches_source(self, source: SourceReference, config: NeuroConvSourceConfig) -> bool:
            if not source.location.is_dir():
                return False
            discovered = self._discover_stream_ids(source.location)
            if not discovered:
                return False
            return "stream_id" in config.interface_kwargs or len(discovered) == 1

        def build_interface(self, source: SourceReference, config: NeuroConvSourceConfig):
            interface_kwargs = {"folder_path": source.location}
            interface_kwargs.update(config.interface_kwargs)
            stream_id = interface_kwargs.get("stream_id")
            if stream_id is None:
                discovered = self._discover_stream_ids(source.location)
                if len(discovered) != 1:
                    raise ValueError(
                        "SpikeGLX conversion requires stream_id when more than one imec stream is present."
                    )
                interface_kwargs["stream_id"] = discovered[0]
            interface_kwargs.setdefault("verbose", False)
            return self.interface_cls(**interface_kwargs)

        def additional_payload(
            self,
            *,
            source: SourceReference,
            metadata: dict[str, object],
            config: NeuroConvSourceConfig,
        ) -> dict[str, object]:
            del metadata
            discovered = self._discover_stream_ids(source.location)
            return {
                "stream_id": config.interface_kwargs.get("stream_id") or (discovered[0] if len(discovered) == 1 else None),
                "stream_count": len(discovered),
            }

        def extraction_notes(self) -> tuple[str, ...]:
            return (
                "Prepared NeuroConv SpikeGLX conversion into ecephys acquisition data.",
                "SpikeGLX route matching prefers folders with distinctive imec .ap/.lf stream files instead of generic binary readers.",
            )

        def _discover_stream_ids(self, folder_path: Path) -> tuple[str, ...]:
            stream_ids: set[str] = set()
            for path in folder_path.rglob("*"):
                if not path.is_file():
                    continue
                match = self._STREAM_PATTERN.search(path.name)
                if match is not None:
                    stream_ids.add(match.group(1))
            return tuple(sorted(stream_ids))


if OpenEphysLegacyRecordingInterface is not None:

    class NeuroConvOpenEphysLegacyAdapter(_NeuroConvEcephysRecordingAdapter):
        """Inspect and convert OpenEphys legacy folders through NeuroConv."""

        adapter_id = "neuroconv_openephys_legacy"
        display_name = "NeuroConv OpenEphys Legacy adapter"
        version = "0.1.0"
        interface_cls = OpenEphysLegacyRecordingInterface
        source_path_kwarg = "folder_path"
        record_type = "neuroconv_openephys_legacy"
        source_types = (SourceType.DIRECTORY,)
        capabilities = AdapterCapabilities(
            supported_pathways=(ConversionPathway.SUPPORTED,),
            supports_multi_source_sessions=True,
        )
        extraction_prefix = "ecephys.openephys_legacy"
        default_device_name = "OpenEphys Legacy"
        source_format = "openephys_legacy_folder"

        def matches_source(self, source: SourceReference, config: NeuroConvSourceConfig) -> bool:
            if not source.location.is_dir():
                return False
            has_legacy_stream = any(path.is_file() and path.suffix.lower() == ".continuous" for path in source.location.rglob("*"))
            if not has_legacy_stream:
                return False
            if config.interface_kwargs.get("stream_name") is not None:
                return True
            try:
                return len(self.interface_cls.get_stream_names(folder_path=source.location)) <= 1
            except Exception:
                return False

        def build_interface(self, source: SourceReference, config: NeuroConvSourceConfig):
            interface_kwargs = {"folder_path": source.location}
            interface_kwargs.update(config.interface_kwargs)
            interface_kwargs.setdefault("verbose", False)
            return self.interface_cls(**interface_kwargs)

        def additional_payload(
            self,
            *,
            source: SourceReference,
            metadata: dict[str, object],
            config: NeuroConvSourceConfig,
        ) -> dict[str, object]:
            del source, metadata
            return {
                "stream_name": config.interface_kwargs.get("stream_name"),
                "block_index": config.interface_kwargs.get("block_index"),
            }

        def extraction_notes(self) -> tuple[str, ...]:
            return (
                "Prepared NeuroConv OpenEphys Legacy conversion into ecephys acquisition data.",
                "OpenEphys Legacy route matching prefers directories with .continuous streams and requires stream selection only when multiple streams are present.",
            )


if PlexonRecordingInterface is not None:

    class NeuroConvPlexonAdapter(_NeuroConvEcephysRecordingAdapter):
        """Inspect and convert Plexon `.plx` recordings through NeuroConv."""

        adapter_id = "neuroconv_plexon"
        display_name = "NeuroConv Plexon adapter"
        version = "0.1.0"
        interface_cls = PlexonRecordingInterface
        record_type = "neuroconv_plexon"
        source_types = (SourceType.FILE,)
        capabilities = AdapterCapabilities(
            supported_pathways=(ConversionPathway.SUPPORTED,),
            supports_multi_source_sessions=True,
        )
        supported_suffixes = (".plx",)
        extraction_prefix = "ecephys.plexon"
        default_device_name = "Plexon"
        source_format = "plexon_plx"

        def matches_source(self, source: SourceReference, config: NeuroConvSourceConfig) -> bool:
            del config
            return source.location.suffix.lower() in self.supported_suffixes

        def additional_payload(
            self,
            *,
            source: SourceReference,
            metadata: dict[str, object],
            config: NeuroConvSourceConfig,
        ) -> dict[str, object]:
            del source, metadata
            return {"stream_name": config.interface_kwargs.get("stream_name", "WB-Wideband")}

        def extraction_notes(self) -> tuple[str, ...]:
            return (
                "Prepared NeuroConv Plexon conversion into ecephys acquisition data.",
                "Plexon route matching prefers distinctive .plx files.",
            )


if TdtRecordingInterface is not None:

    class NeuroConvTdtAdapter(_NeuroConvEcephysRecordingAdapter):
        """Inspect and convert TDT folders through NeuroConv."""

        adapter_id = "neuroconv_tdt"
        display_name = "NeuroConv TDT adapter"
        version = "0.1.0"
        interface_cls = TdtRecordingInterface
        source_path_kwarg = "folder_path"
        record_type = "neuroconv_tdt"
        source_types = (SourceType.DIRECTORY,)
        capabilities = AdapterCapabilities(
            supported_pathways=(ConversionPathway.SUPPORTED,),
            supports_multi_source_sessions=True,
        )
        extraction_prefix = "ecephys.tdt"
        default_device_name = "TDT"
        source_format = "tdt_folder"
        _SIGNATURE_SUFFIXES = (".tbk", ".tbx", ".tev", ".tsq")

        def matches_source(self, source: SourceReference, config: NeuroConvSourceConfig) -> bool:
            return (
                source.location.is_dir()
                and _directory_has_any_suffix(source.location, self._SIGNATURE_SUFFIXES)
                and _config_has_keys(config, ("gain",))
            )

        def build_interface(self, source: SourceReference, config: NeuroConvSourceConfig):
            interface_kwargs = {"folder_path": source.location}
            interface_kwargs.update(config.interface_kwargs)
            interface_kwargs.setdefault("verbose", False)
            return self.interface_cls(**interface_kwargs)

        def additional_payload(
            self,
            *,
            source: SourceReference,
            metadata: dict[str, object],
            config: NeuroConvSourceConfig,
        ) -> dict[str, object]:
            del source, metadata
            return {
                "gain": config.interface_kwargs.get("gain"),
                "stream_id": config.interface_kwargs.get("stream_id", "0"),
                "stream_name": config.interface_kwargs.get("stream_name"),
            }

        def extraction_notes(self) -> tuple[str, ...]:
            return (
                "Prepared NeuroConv TDT conversion into ecephys acquisition data.",
                "TDT route matching prefers directories with TSQ/TBK/TEV/TBX files and requires an explicit gain in source configuration.",
            )


if WhiteMatterRecordingInterface is not None:

    class NeuroConvWhiteMatterAdapter(_NeuroConvEcephysRecordingAdapter):
        """Inspect and convert WhiteMatter binaries through NeuroConv."""

        adapter_id = "neuroconv_whitematter"
        display_name = "NeuroConv WhiteMatter adapter"
        version = "0.1.0"
        interface_cls = WhiteMatterRecordingInterface
        record_type = "neuroconv_whitematter"
        source_types = (SourceType.FILE,)
        capabilities = AdapterCapabilities(
            supported_pathways=(ConversionPathway.SUPPORTED,),
            supports_multi_source_sessions=True,
        )
        supported_suffixes = (".bin",)
        extraction_prefix = "ecephys.whitematter"
        default_device_name = "WhiteMatter"
        source_format = "whitematter_bin"

        def matches_source(self, source: SourceReference, config: NeuroConvSourceConfig) -> bool:
            if source.location.suffix.lower() != ".bin":
                return False
            if source.location.with_suffix(".set").exists():
                return False
            return _config_has_keys(config, ("sampling_frequency", "num_channels"))

        def additional_payload(
            self,
            *,
            source: SourceReference,
            metadata: dict[str, object],
            config: NeuroConvSourceConfig,
        ) -> dict[str, object]:
            del source, metadata
            channel_ids = config.interface_kwargs.get("channel_ids") or ()
            return {
                "sampling_frequency": config.interface_kwargs.get("sampling_frequency"),
                "num_channels": config.interface_kwargs.get("num_channels"),
                "channel_id_count": len(channel_ids),
                "is_filtered": config.interface_kwargs.get("is_filtered"),
            }

        def extraction_notes(self) -> tuple[str, ...]:
            return (
                "Prepared NeuroConv WhiteMatter conversion into ecephys acquisition data.",
                "WhiteMatter route matching prefers .bin files only when required acquisition parameters are configured and no Axona .set sidecar is present.",
            )
