"""Canonical normalized metadata models."""

from __future__ import annotations

from dataclasses import dataclass, field

from nwbforge.domain.models.common import NormalizedValue


@dataclass(frozen=True, slots=True)
class NormalizedSubject:
    subject_id: NormalizedValue[str] | None = None
    species: NormalizedValue[str] | None = None
    sex: NormalizedValue[str] | None = None
    age: NormalizedValue[str] | None = None
    date_of_birth: NormalizedValue[str] | None = None
    description: NormalizedValue[str] | None = None
    genotype: NormalizedValue[str] | None = None
    strain: NormalizedValue[str] | None = None
    additional_fields: dict[str, NormalizedValue[object]] = field(default_factory=dict)

    def iter_values(self) -> tuple[NormalizedValue[object], ...]:
        values = [
            self.subject_id,
            self.species,
            self.sex,
            self.age,
            self.date_of_birth,
            self.description,
            self.genotype,
            self.strain,
        ]
        values.extend(self.additional_fields.values())
        return tuple(value for value in values if value is not None)


@dataclass(frozen=True, slots=True)
class NormalizedSessionMetadata:
    session_id: NormalizedValue[str] | None = None
    session_description: NormalizedValue[str] | None = None
    experiment_description: NormalizedValue[str] | None = None
    start_time: NormalizedValue[str] | None = None
    experimenter: NormalizedValue[str] | None = None
    institution: NormalizedValue[str] | None = None
    lab: NormalizedValue[str] | None = None
    keywords: tuple[NormalizedValue[str], ...] = ()
    additional_fields: dict[str, NormalizedValue[object]] = field(default_factory=dict)

    def iter_values(self) -> tuple[NormalizedValue[object], ...]:
        values = [
            self.session_id,
            self.session_description,
            self.experiment_description,
            self.start_time,
            self.experimenter,
            self.institution,
            self.lab,
            *self.keywords,
        ]
        values.extend(self.additional_fields.values())
        return tuple(value for value in values if value is not None)


@dataclass(frozen=True, slots=True)
class NormalizedDevice:
    device_id: str
    name: NormalizedValue[str]
    description: NormalizedValue[str] | None = None
    manufacturer: NormalizedValue[str] | None = None
    modality: str | None = None
    additional_fields: dict[str, NormalizedValue[object]] = field(default_factory=dict)

    def iter_values(self) -> tuple[NormalizedValue[object], ...]:
        values = [self.name, self.description, self.manufacturer]
        values.extend(self.additional_fields.values())
        return tuple(value for value in values if value is not None)


@dataclass(frozen=True, slots=True)
class AcquisitionStream:
    stream_id: str
    name: NormalizedValue[str]
    modality: str | None
    source_ids: tuple[str, ...]
    description: NormalizedValue[str] | None = None
    start_time: NormalizedValue[str] | None = None
    end_time: NormalizedValue[str] | None = None
    metadata: dict[str, NormalizedValue[object]] = field(default_factory=dict)

    def iter_values(self) -> tuple[NormalizedValue[object], ...]:
        values = [self.name, self.description, self.start_time, self.end_time]
        values.extend(self.metadata.values())
        return tuple(value for value in values if value is not None)


@dataclass(frozen=True, slots=True)
class NormalizedMetadataBundle:
    subject: NormalizedSubject = field(default_factory=NormalizedSubject)
    session: NormalizedSessionMetadata = field(default_factory=NormalizedSessionMetadata)
    devices: tuple[NormalizedDevice, ...] = ()
    acquisition_streams: tuple[AcquisitionStream, ...] = ()
    additional_metadata: dict[str, NormalizedValue[object]] = field(default_factory=dict)

    def pending_review_values(self) -> tuple[NormalizedValue[object], ...]:
        values: list[NormalizedValue[object]] = []
        values.extend(value for value in self.subject.iter_values() if value.needs_review)
        values.extend(value for value in self.session.iter_values() if value.needs_review)
        for device in self.devices:
            values.extend(value for value in device.iter_values() if value.needs_review)
        for stream in self.acquisition_streams:
            values.extend(value for value in stream.iter_values() if value.needs_review)
        values.extend(value for value in self.additional_metadata.values() if value.needs_review)
        return tuple(values)
