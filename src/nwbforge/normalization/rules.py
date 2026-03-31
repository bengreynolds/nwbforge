"""Declarative normalization rules for extracted metadata."""

from __future__ import annotations

from dataclasses import dataclass


DEFAULT_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "subject.subject_id": ("subject_id", "subject.id", "animal_id", "animal.id"),
    "subject.species": ("species", "subject.species"),
    "subject.sex": ("sex", "subject.sex"),
    "subject.age": ("age", "subject.age"),
    "subject.genotype": ("genotype", "subject.genotype"),
    "subject.strain": ("strain", "subject.strain"),
    "session.session_id": ("session_id", "session.id", "recording_id"),
    "session.session_description": (
        "session_description",
        "session.description",
        "description",
    ),
    "session.start_time": ("start_time", "session.start_time", "session_start_time"),
    "session.experimenter": ("experimenter", "operator", "session.experimenter"),
    "session.institution": ("institution", "institution_name", "session.institution"),
    "session.lab": ("lab", "lab_name", "session.lab"),
    "session.keywords": ("keywords", "session.keywords"),
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
