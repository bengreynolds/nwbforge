"""Declarative normalization rules for extracted metadata."""

from __future__ import annotations

from dataclasses import dataclass


DEFAULT_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "subject.subject_id": (
        "subject_id",
        "subject.subject_id",
        "subject.id",
        "animal_id",
        "animal.id",
        "animal_profile.identifier",
    ),
    "subject.species": ("species", "subject.species", "animal_profile.species_name"),
    "subject.sex": ("sex", "subject.sex", "animal_profile.sex_code"),
    "subject.age": ("age", "subject.age", "animal_profile.life_stage"),
    "subject.date_of_birth": (
        "date_of_birth",
        "subject.date_of_birth",
        "subject.dob",
        "animal_profile.birth_date",
    ),
    "subject.description": ("subject_description", "subject.description", "animal_profile.notes"),
    "subject.genotype": ("genotype", "subject.genotype"),
    "subject.strain": ("strain", "subject.strain", "animal_profile.strain_name"),
    "session.session_id": (
        "session_id",
        "session.id",
        "recording_id",
        "recording_context.recording_id",
    ),
    "session.session_description": (
        "session_description",
        "session.description",
        "description",
        "recording_context.summary",
    ),
    "session.start_time": (
        "start_time",
        "session.start_time",
        "session_start_time",
        "recording_context.started_at",
    ),
    "session.experiment_description": (
        "experiment_description",
        "session.experiment_description",
        "experiment.description",
        "recording_context.study_description",
    ),
    "session.experimenter": (
        "experimenter",
        "operator",
        "session.experimenter",
        "recording_context.operator_name",
    ),
    "session.institution": (
        "institution",
        "institution_name",
        "session.institution",
        "recording_context.institute_name",
    ),
    "session.lab": ("lab", "lab_name", "session.lab", "recording_context.group_name"),
    "session.keywords": ("keywords", "session.keywords", "annotations.keywords"),
}


@dataclass(frozen=True, slots=True)
class NormalizationRuleSet:
    field_aliases: dict[str, tuple[str, ...]]

    def canonical_key_for(self, extracted_key: str) -> str | None:
        normalized_key = extracted_key.strip().lower().replace("-", "_")
        for canonical_key, aliases in self.field_aliases.items():
            if normalized_key in aliases:
                return canonical_key
        return None
