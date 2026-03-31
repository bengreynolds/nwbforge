"""Concrete NWB assembly services."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pynwb import NWBHDF5IO, NWBFile
from pynwb.file import Subject

from nwbforge.domain.contracts import AssemblyService
from nwbforge.domain.models import MappingPlan, NormalizedMetadataBundle, ProvenanceArtifact, ConversionSession


class PyNWBAssemblyService(AssemblyService):
    """Write a minimal NWB file from normalized metadata and the current mapping plan."""

    def write(
        self,
        session: ConversionSession,
        metadata: NormalizedMetadataBundle,
        mapping_plan: MappingPlan,
        output_path: str,
    ) -> tuple[ProvenanceArtifact, ...]:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

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
