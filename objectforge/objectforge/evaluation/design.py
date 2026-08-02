from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from objectforge.design.language import DesignLanguage
from objectforge.grammar.core import GrammarAssetBuilder


@dataclass(frozen=True)
class DesignEvaluation:
    passed: bool
    metrics: dict[str, Any]
    failures: tuple[str, ...]


def evaluate_design_language(builder: GrammarAssetBuilder, language: DesignLanguage) -> DesignEvaluation:
    failures: list[str] = []
    raw_metadata = builder.functional_metadata.get("design_language") or {}
    if isinstance(raw_metadata, str):
        metadata = {
            "language_id": raw_metadata,
            "fingerprint": builder.functional_metadata.get("design_language_fingerprint"),
        }
    else:
        metadata = raw_metadata
    motifs = [
        part
        for part in builder.parts
        if part.semantic_part.startswith("design_language.") or part.node_name.startswith("Language")
    ]
    operations = [item for item in builder.operations if item.operator == "design_language.apply"]
    verified = [item for item in builder.operations if item.operator == "design_language.verify"]
    materials = {part.material for part in builder.parts}
    role_materials = set(language.material_roles.values())
    role_coverage = sorted(materials & role_materials)

    if builder.capability_id not in {
        "objectforge.procedural-design-language.v1",
        "objectforge.multi-object-coherent-systems.v1",
    }:
        failures.append("builder does not advertise a design-language-capable ObjectForge capability")
    if metadata.get("language_id") != language.language_id:
        failures.append("retained language identity differs from requested language")
    if metadata.get("fingerprint") != language.fingerprint:
        failures.append("retained language fingerprint differs from selected profile")
    if len(motifs) < 10:
        failures.append("fewer than ten language-specific motif components")
    if len(role_coverage) < 5:
        failures.append("fewer than five design-language material roles are visible")
    if len(operations) != 1 or len(verified) != 1:
        failures.append("design-language application or verification receipt missing")
    selected_architecture = builder.functional_metadata.get("selected_architecture")
    if not selected_architecture and builder.capability_id == "objectforge.multi-object-coherent-systems.v1":
        selected_architecture = builder.variant
    if not selected_architecture:
        failures.append("functional architecture identity was lost")

    signature = {
        "language_id": language.language_id,
        "fingerprint": language.fingerprint,
        "material_roles": language.material_roles,
        "proportion_tokens": language.proportion_tokens,
        "surface_tokens": language.surface_tokens,
        "interaction_tokens": language.interaction_tokens,
    }
    return DesignEvaluation(
        passed=not failures,
        metrics={
            "language_id": language.language_id,
            "fingerprint": language.fingerprint,
            "motif_components": len(motifs),
            "role_material_coverage": role_coverage,
            "role_material_count": len(role_coverage),
            "signature": signature,
        },
        failures=tuple(failures),
    )


def evaluate_language_set(records: list[dict[str, Any]], languages: tuple[DesignLanguage, ...]) -> DesignEvaluation:
    failures: list[str] = []
    expected_languages = {item.language_id for item in languages}
    found_languages = {item["language_id"] for item in records}
    briefs = {item["brief_id"] for item in records}
    expected_count = len(languages) * len(briefs)
    if found_languages != expected_languages:
        failures.append("not all declared design languages were delivered")
    if len(records) != expected_count:
        failures.append("language-by-brief matrix is incomplete")

    within_coherence: dict[str, bool] = {}
    for language in languages:
        members = [item for item in records if item["language_id"] == language.language_id]
        fingerprints = {item["language_fingerprint"] for item in members}
        signatures = {item["style_signature_hash"] for item in members}
        coherent = fingerprints == {language.fingerprint} and signatures == {language.fingerprint}
        within_coherence[language.language_id] = coherent
        if not coherent:
            failures.append(f"{language.language_id} assets do not share one design-language signature")

    paired_architectures: dict[str, set[str]] = {}
    paired_hashes: dict[str, set[str]] = {}
    for item in records:
        paired_architectures.setdefault(item["brief_id"], set()).add(item["selected_architecture"])
        paired_hashes.setdefault(item["brief_id"], set()).add(item["canonical_sha256"])
    for brief_id, values in paired_architectures.items():
        if len(values) != 1:
            failures.append(f"design language altered functional architecture for {brief_id}")
    for brief_id, values in paired_hashes.items():
        if len(values) != len(languages):
            failures.append(f"design languages failed to produce distinct retained models for {brief_id}")

    inter_language_distinct = len({item.fingerprint for item in languages}) == len(languages)
    if not inter_language_distinct:
        failures.append("design-language profiles are not distinct")

    return DesignEvaluation(
        passed=not failures,
        metrics={
            "asset_count": len(records),
            "language_count": len(found_languages),
            "brief_count": len(briefs),
            "within_language_coherence": within_coherence,
            "paired_architecture_invariance": all(len(value) == 1 for value in paired_architectures.values()),
            "paired_model_distinction": all(len(value) == len(languages) for value in paired_hashes.values()),
            "inter_language_distinct": inter_language_distinct,
        },
        failures=tuple(failures),
    )
