"""Concrete NWB assembly services."""

from __future__ import annotations

from datetime import UTC, datetime
from math import nan
from pathlib import Path

import numpy as np
from pynwb import NWBHDF5IO, NWBFile, TimeSeries
from pynwb.behavior import BehavioralTimeSeries, Position, SpatialSeries
from pynwb.ecephys import ElectricalSeries
from pynwb.file import Subject
from pynwb.image import ImageSeries

from nwbforge.domain.contracts import AssemblyService
from nwbforge.domain.models import MappingPlan, NormalizedMetadataBundle, ProvenanceArtifact, ConversionSession


class PyNWBAssemblyService(AssemblyService):
    """Write a minimal NWB file from normalized metadata and the current mapping plan."""

    def build_nwbfile(
        self,
        session: ConversionSession,
        metadata: NormalizedMetadataBundle,
        mapping_plan: MappingPlan,
        *,
        include_acquisition_streams: bool = True,
        include_time_interval_tables: bool = True,
    ) -> NWBFile:
        nwbfile = NWBFile(
            session_description=self._required_text(metadata.session.session_description, "session_description"),
            identifier=self._identifier(metadata, session),
            session_start_time=self._required_datetime(metadata.session.start_time, "session_start_time"),
            experiment_description=self._optional_text(metadata.session.experiment_description),
            experimenter=self._optional_list(metadata.session.experimenter),
            lab=self._optional_text(metadata.session.lab),
            institution=self._optional_text(metadata.session.institution),
            session_id=self._optional_text(metadata.session.session_id),
            keywords=self._optional_keywords(metadata),
        )
        subject = self._subject(metadata)
        if subject is not None:
            nwbfile.subject = subject
        for device in metadata.devices:
            nwbfile.create_device(
                name=str(device.name.value),
                description=self._optional_text(device.description),
                manufacturer=self._optional_text(device.manufacturer),
            )
        if include_acquisition_streams:
            self._write_acquisition_streams(nwbfile, metadata)
        if include_time_interval_tables:
            self._write_time_interval_tables(nwbfile, metadata)
        return nwbfile

    def write(
        self,
        session: ConversionSession,
        metadata: NormalizedMetadataBundle,
        mapping_plan: MappingPlan,
        output_path: str,
    ) -> tuple[ProvenanceArtifact, ...]:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        nwbfile = self.build_nwbfile(session, metadata, mapping_plan)

        with NWBHDF5IO(path=str(output_file), mode="w") as io:
            io.write(nwbfile)

        return (
            ProvenanceArtifact(
                artifact_type="nwb",
                location=output_file,
                description=f"NWB file assembled from {len(mapping_plan.decisions)} mapping decisions.",
            ),
        )

    @staticmethod
    def _identifier(metadata: NormalizedMetadataBundle, session: ConversionSession) -> str:
        if metadata.session.session_id is not None:
            return str(metadata.session.session_id.value)
        return session.session_id

    @staticmethod
    def _required_text(value, field_name: str) -> str:
        if value is None or value.value in (None, ""):
            raise ValueError(f"Missing required NWB field '{field_name}'.")
        return str(value.value)

    @staticmethod
    def _optional_text(value) -> str | None:
        if value is None or value.value in (None, ""):
            return None
        return str(value.value)

    @staticmethod
    def _optional_list(value) -> list[str] | None:
        text = PyNWBAssemblyService._optional_text(value)
        if text is None:
            return None
        return [text]

    @staticmethod
    def _optional_datetime(value) -> datetime | None:
        if value is None or value.value in (None, ""):
            return None
        raw = value.value
        if isinstance(raw, datetime):
            return raw if raw.tzinfo is not None else raw.replace(tzinfo=UTC)
        parsed = datetime.fromisoformat(str(raw))
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)

    @staticmethod
    def _required_datetime(value, field_name: str) -> datetime:
        if value is None or value.value in (None, ""):
            raise ValueError(f"Missing required NWB field '{field_name}'.")
        raw = value.value
        if isinstance(raw, datetime):
            return raw if raw.tzinfo is not None else raw.replace(tzinfo=UTC)
        parsed = datetime.fromisoformat(str(raw))
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)

    @staticmethod
    def _optional_keywords(metadata: NormalizedMetadataBundle) -> list[str] | None:
        if not metadata.session.keywords:
            return None
        return [str(keyword.value) for keyword in metadata.session.keywords]

    @staticmethod
    def _subject(metadata: NormalizedMetadataBundle) -> Subject | None:
        subject = metadata.subject
        values = {
            "subject_id": PyNWBAssemblyService._optional_text(subject.subject_id),
            "species": PyNWBAssemblyService._optional_text(subject.species),
            "sex": PyNWBAssemblyService._optional_text(subject.sex),
            "age": PyNWBAssemblyService._optional_text(subject.age),
            "date_of_birth": PyNWBAssemblyService._optional_datetime(subject.date_of_birth),
            "description": PyNWBAssemblyService._optional_text(subject.description),
            "genotype": PyNWBAssemblyService._optional_text(subject.genotype),
            "strain": PyNWBAssemblyService._optional_text(subject.strain),
        }
        if not any(values.values()):
            return None
        return Subject(**{key: value for key, value in values.items() if value is not None})

    @classmethod
    def _write_acquisition_streams(cls, nwbfile: NWBFile, metadata: NormalizedMetadataBundle) -> None:
        behavior_container: BehavioralTimeSeries | None = None
        position_container: Position | None = None
        for stream in metadata.acquisition_streams:
            modality = cls._stream_modality(stream)
            behavior_type = cls._stream_behavior_type(stream)
            if modality == "behavior" and behavior_type == "position":
                if position_container is None:
                    position_container = Position(name="position")
                    nwbfile.add_acquisition(position_container)
                position_container.add_spatial_series(cls._spatial_series(stream))
                continue

            if modality == "behavior":
                timeseries = cls._timeseries(stream)
                if behavior_container is None:
                    behavior_container = BehavioralTimeSeries(name="behavior")
                    nwbfile.add_acquisition(behavior_container)
                behavior_container.add_timeseries(timeseries)
                continue

            if modality in {"image", "images", "imaging", "ophys", "video"}:
                nwbfile.add_acquisition(cls._image_series(stream))
                continue

            if modality in {"ecephys", "electrical"}:
                nwbfile.add_acquisition(cls._electrical_series(nwbfile, stream))
                continue

            nwbfile.add_acquisition(cls._timeseries(stream))

    @classmethod
    def _write_time_interval_tables(cls, nwbfile: NWBFile, metadata: NormalizedMetadataBundle) -> None:
        for table in metadata.time_interval_tables:
            table_name = str(table.table_name.value).strip().lower()
            if table_name != "trials":
                raise ValueError(
                    f"Interval table '{table.table_id}' targets '{table_name}', but only trials are supported "
                    "by the current writer."
                )

            extra_columns = cls._trial_extra_columns(table.rows)
            for column_name in extra_columns:
                if nwbfile.trials is None or column_name not in nwbfile.trials.colnames:
                    nwbfile.add_trial_column(
                        name=column_name,
                        description=f"Imported interval metadata column '{column_name}'.",
                    )

            for row_index, row in enumerate(table.rows):
                kwargs = {
                    "start_time": cls._interval_time_value(row.start_time, row, "start_time"),
                    "stop_time": cls._interval_stop_time(table.rows, row_index),
                }
                for column_name in extra_columns:
                    value = row.metadata.get(column_name)
                    kwargs[column_name] = None if value is None else value.value
                nwbfile.add_trial(**kwargs)

    @classmethod
    def _timeseries(cls, stream) -> TimeSeries:
        data = cls._required_stream_metadata(stream, "data")
        unit = str(cls._required_stream_metadata(stream, "unit"))
        kwargs = {
            "name": str(stream.name.value),
            "data": data,
            "unit": unit,
            "description": cls._optional_text(stream.description) or "no description",
        }
        continuity = cls._optional_stream_metadata(stream, "continuity")
        if continuity is not None:
            kwargs["continuity"] = str(continuity)

        timestamps = cls._optional_stream_metadata(stream, "timestamps")
        rate = cls._optional_stream_metadata(stream, "rate")
        if timestamps is not None:
            kwargs["timestamps"] = timestamps
        elif rate is not None:
            kwargs["rate"] = float(rate)
            starting_time = cls._optional_stream_metadata(stream, "starting_time")
            if starting_time is not None:
                kwargs["starting_time"] = float(starting_time)
        else:
            raise ValueError(
                f"Acquisition stream '{stream.stream_id}' requires either timestamps or rate for writing."
            )

        return TimeSeries(**kwargs)

    @classmethod
    def _spatial_series(cls, stream) -> SpatialSeries:
        data = cls._required_stream_metadata(stream, "data")
        reference_frame = str(cls._required_stream_metadata(stream, "reference_frame"))
        unit = str(cls._required_stream_metadata(stream, "unit"))
        kwargs = {
            "name": str(stream.name.value),
            "data": data,
            "reference_frame": reference_frame,
            "unit": unit,
            "description": cls._optional_text(stream.description) or "no description",
        }

        timestamps = cls._optional_stream_metadata(stream, "timestamps")
        rate = cls._optional_stream_metadata(stream, "rate")
        if timestamps is not None:
            kwargs["timestamps"] = timestamps
        elif rate is not None:
            kwargs["rate"] = float(rate)
            starting_time = cls._optional_stream_metadata(stream, "starting_time")
            if starting_time is not None:
                kwargs["starting_time"] = float(starting_time)
        else:
            raise ValueError(
                f"Acquisition stream '{stream.stream_id}' requires either timestamps or rate for writing."
            )

        return SpatialSeries(**kwargs)

    @classmethod
    def _image_series(cls, stream) -> ImageSeries:
        kwargs = {
            "name": str(stream.name.value),
            "unit": str(cls._optional_stream_metadata(stream, "unit") or "n/a"),
            "description": cls._optional_text(stream.description) or "no description",
            "format": str(cls._optional_stream_metadata(stream, "format") or "raw"),
        }
        external_file = cls._optional_stream_metadata(stream, "external_file")
        if external_file is not None:
            if isinstance(external_file, (list, tuple)):
                kwargs["external_file"] = [str(item) for item in external_file]
            else:
                kwargs["external_file"] = [str(external_file)]
            starting_frame = cls._optional_stream_metadata(stream, "starting_frame")
            if starting_frame is not None:
                kwargs["starting_frame"] = starting_frame
        else:
            kwargs["data"] = cls._required_stream_metadata(stream, "data")

        timestamps = cls._optional_stream_metadata(stream, "timestamps")
        rate = cls._optional_stream_metadata(stream, "rate")
        if timestamps is not None:
            kwargs["timestamps"] = timestamps
        elif rate is not None:
            kwargs["rate"] = float(rate)
            starting_time = cls._optional_stream_metadata(stream, "starting_time")
            if starting_time is not None:
                kwargs["starting_time"] = float(starting_time)
        else:
            raise ValueError(
                f"Image stream '{stream.stream_id}' requires either timestamps or rate for writing."
            )

        return ImageSeries(**kwargs)

    @classmethod
    def _electrical_series(cls, nwbfile: NWBFile, stream) -> ElectricalSeries:
        data = np.asarray(cls._required_stream_metadata(stream, "data"))
        if data.ndim == 1:
            data = data[:, np.newaxis]
        channel_count = int(cls._optional_stream_metadata(stream, "channel_count") or data.shape[1])

        device_name = str(cls._optional_stream_metadata(stream, "device_name") or f"{stream.stream_id}-device")
        if device_name in nwbfile.devices:
            device = nwbfile.devices[device_name]
        else:
            device = nwbfile.create_device(
                name=device_name,
                description=str(cls._optional_stream_metadata(stream, "device_description") or "Auto-generated ecephys device."),
                manufacturer=str(cls._optional_stream_metadata(stream, "device_manufacturer") or "Unknown"),
            )

        group_name = str(
            cls._optional_stream_metadata(stream, "electrode_group_name") or f"{stream.stream_id}-group"
        )
        group_description = str(
            cls._optional_stream_metadata(stream, "electrode_group_description")
            or "Auto-generated electrode group for custom/hybrid ecephys stream."
        )
        group_location = str(cls._optional_stream_metadata(stream, "electrode_location") or "unknown")
        if group_name in nwbfile.electrode_groups:
            electrode_group = nwbfile.electrode_groups[group_name]
        else:
            electrode_group = nwbfile.create_electrode_group(
                name=group_name,
                description=group_description,
                location=group_location,
                device=device,
            )

        base_index = len(nwbfile.electrodes) if nwbfile.electrodes is not None else 0
        filtering = str(cls._optional_stream_metadata(stream, "filtering") or "unknown")
        for channel_index in range(channel_count):
            nwbfile.add_electrode(
                id=base_index + channel_index,
                x=float("nan"),
                y=float("nan"),
                z=float("nan"),
                imp=float("nan"),
                location=group_location,
                filtering=filtering,
                group=electrode_group,
            )
        region = nwbfile.create_electrode_table_region(
            region=list(range(base_index, base_index + channel_count)),
            description=f"Auto-generated electrodes for {stream.stream_id}.",
        )

        kwargs = {
            "name": str(stream.name.value),
            "data": data,
            "electrodes": region,
            "filtering": filtering,
            "description": cls._optional_text(stream.description) or "no description",
        }
        timestamps = cls._optional_stream_metadata(stream, "timestamps")
        rate = cls._optional_stream_metadata(stream, "rate")
        if timestamps is not None:
            kwargs["timestamps"] = timestamps
        elif rate is not None:
            kwargs["rate"] = float(rate)
            starting_time = cls._optional_stream_metadata(stream, "starting_time")
            if starting_time is not None:
                kwargs["starting_time"] = float(starting_time)
        else:
            raise ValueError(
                f"Electrical stream '{stream.stream_id}' requires either timestamps or rate for writing."
            )

        return ElectricalSeries(**kwargs)

    @staticmethod
    def _trial_extra_columns(rows) -> tuple[str, ...]:
        column_names: list[str] = []
        for row in rows:
            for column_name in row.metadata:
                if column_name not in column_names:
                    column_names.append(column_name)
        return tuple(column_names)

    @staticmethod
    def _interval_time_value(value, row, field_name: str) -> float:
        if value is None or value.value in (None, ""):
            raise ValueError(f"Time interval row '{row.row_id}' is missing required '{field_name}'.")
        return float(value.value)

    @classmethod
    def _interval_stop_time(cls, rows, row_index: int) -> float:
        row = rows[row_index]
        if row.stop_time is not None and row.stop_time.value not in (None, ""):
            return float(row.stop_time.value)
        if row_index + 1 < len(rows):
            next_row = rows[row_index + 1]
            return cls._interval_time_value(next_row.start_time, next_row, "start_time")
        return nan

    @staticmethod
    def _stream_modality(stream) -> str:
        if stream.modality is None:
            return ""
        return str(stream.modality).strip().lower()

    @classmethod
    def _stream_behavior_type(cls, stream) -> str:
        value = cls._optional_stream_metadata(stream, "behavior_type")
        if value is None:
            return ""
        return str(value).strip().lower()

    @staticmethod
    def _required_stream_metadata(stream, key: str):
        value = stream.metadata.get(key)
        if value is None or value.value in (None, ""):
            raise ValueError(
                f"Acquisition stream '{stream.stream_id}' is missing required metadata '{key}'."
            )
        return value.value

    @staticmethod
    def _optional_stream_metadata(stream, key: str):
        value = stream.metadata.get(key)
        if value is None or value.value in (None, ""):
            return None
        return value.value
