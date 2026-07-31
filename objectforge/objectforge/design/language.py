from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any

import numpy as np

from objectforge.geometry import apply_material, rounded_box, scale, translation
from objectforge.grammar.core import GrammarAssetBuilder
from objectforge.grammar.library import RepetitionGrammar


@dataclass(frozen=True)
class DesignLanguage:
    language_id: str
    label: str
    intent: str
    manufacturing_story: str
    proportion_tokens: dict[str, float]
    surface_tokens: dict[str, Any]
    interaction_tokens: dict[str, Any]
    material_roles: dict[str, str]
    material_remap: dict[str, str]
    semantic_material_overrides: dict[str, str]
    motif_id: str

    @property
    def fingerprint(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "fingerprint": self.fingerprint}


def design_languages() -> tuple[DesignLanguage, ...]:
    return (
        DesignLanguage(
            language_id="field_service",
            label="Field Service",
            intent="Rugged, repairable equipment designed for transport, gloves, impacts, and visible maintenance.",
            manufacturing_story=(
                "Powder-coated metal and molded protective parts are assembled with exposed service hardware. "
                "Orange indicates touch points and removable modules; dark rubber protects contact surfaces."
            ),
            proportion_tokens={
                "structure_scale": 1.045,
                "control_scale": 1.12,
                "protection_scale": 1.10,
                "handle_scale": 1.08,
                "detail_scale": 1.03,
                "edge_radius_class": 0.080,
                "seam_width": 0.035,
            },
            surface_tokens={
                "fastener_style": "exposed_hex",
                "seam_style": "serviceable_external",
                "edge_treatment": "large_protective_radius",
                "accent_strategy": "high_visibility_touchpoints",
                "label_strategy": "riveted_rating_plates",
                "vent_strategy": "wide_service_slots",
            },
            interaction_tokens={
                "control_size": "glove_operable",
                "handle_clearance": "large",
                "state_signaling": "orange_touchpoints",
            },
            material_roles={
                "primary": "GraphitePowderCoat",
                "secondary": "MoldedBlack",
                "accent": "SignalOrange",
                "hardware": "BrushedSteel",
                "contact": "DarkRubber",
                "interior": "CarbonInsert",
                "emitter": "WarmEmitter",
            },
            material_remap={
                "IvoryPowderCoat": "GraphitePowderCoat",
                "MoldedBlue": "GraphitePowderCoat",
                "CeramicWhite": "GraphitePowderCoat",
                "WarmAluminum": "BrushedSteel",
                "Brass": "BrushedSteel",
                "VelvetLiner": "CarbonInsert",
                "FabricLiner": "CarbonInsert",
                "OakVarnish": "CarbonInsert",
                "WalnutVarnish": "CarbonInsert",
            },
            semantic_material_overrides={
                "interface.": "SignalOrange",
                "closure.": "SignalOrange",
                "handle.": "DarkRubber",
                "protection.": "SignalOrange",
                "support.foot": "DarkRubber",
                "support.skid": "DarkRubber",
                "detail.identification": "BrushedSteel",
                "organization.socket_insert": "DarkRubber",
            },
            motif_id="rugged_service_frame",
        ),
        DesignLanguage(
            language_id="precision_lab",
            label="Precision Lab",
            intent="Quiet laboratory instrumentation with flush surfaces, fine controls, measured hierarchy, and cleanable finishes.",
            manufacturing_story=(
                "Ivory coated shells, precision metal trims, molded blue controls, and ceramic or elastomer contact surfaces "
                "are assembled with concealed hardware and narrow service seams."
            ),
            proportion_tokens={
                "structure_scale": 0.955,
                "control_scale": 0.86,
                "protection_scale": 0.82,
                "handle_scale": 0.91,
                "detail_scale": 0.88,
                "edge_radius_class": 0.035,
                "seam_width": 0.014,
            },
            surface_tokens={
                "fastener_style": "concealed_precision",
                "seam_style": "flush_narrow",
                "edge_treatment": "small_continuous_radius",
                "accent_strategy": "single_control_band",
                "label_strategy": "flush_serial_plates",
                "vent_strategy": "fine_linear_slots",
            },
            interaction_tokens={
                "control_size": "fingertip_precision",
                "handle_clearance": "compact",
                "state_signaling": "muted_blue_indicators",
            },
            material_roles={
                "primary": "IvoryPowderCoat",
                "secondary": "CeramicWhite",
                "accent": "MoldedBlue",
                "hardware": "WarmAluminum",
                "contact": "DarkRubber",
                "interior": "FabricLiner",
                "emitter": "WarmEmitter",
            },
            material_remap={
                "GraphitePowderCoat": "IvoryPowderCoat",
                "SignalOrange": "MoldedBlue",
                "MoldedBlack": "CeramicWhite",
                "BrushedSteel": "WarmAluminum",
                "Brass": "WarmAluminum",
                "CarbonInsert": "FabricLiner",
                "VelvetLiner": "FabricLiner",
                "SwitchPlastic": "MoldedBlue",
            },
            semantic_material_overrides={
                "interface.": "MoldedBlue",
                "closure.": "WarmAluminum",
                "handle.": "IvoryPowderCoat",
                "protection.": "CeramicWhite",
                "support.foot": "DarkRubber",
                "support.skid": "DarkRubber",
                "detail.identification": "WarmAluminum",
                "organization.socket_insert": "DarkRubber",
            },
            motif_id="precision_control_band",
        ),
    )


def get_design_language(language_id: str) -> DesignLanguage:
    for language in design_languages():
        if language.language_id == language_id:
            return language
    raise KeyError(f"unknown design language: {language_id}")


def _semantic_override(language: DesignLanguage, semantic: str) -> str | None:
    best: tuple[int, str] | None = None
    for prefix, material in language.semantic_material_overrides.items():
        if semantic.startswith(prefix) and (best is None or len(prefix) > best[0]):
            best = (len(prefix), material)
    return None if best is None else best[1]


def _scale_geometry(builder: GrammarAssetBuilder, language: DesignLanguage) -> None:
    tokens = language.proportion_tokens
    categories = (
        ("protection.", tokens["protection_scale"]),
        ("interface.", tokens["control_scale"]),
        ("closure.", tokens["control_scale"]),
        ("handle.", tokens["handle_scale"]),
        ("support.", tokens["structure_scale"]),
        ("reach.", tokens["structure_scale"]),
        ("joint.", tokens["structure_scale"]),
        ("detail.", tokens["detail_scale"]),
    )
    for part in builder.parts:
        factor = 1.0
        for prefix, value in categories:
            if part.semantic_part.startswith(prefix):
                factor = float(value)
                break
        if abs(factor - 1.0) < 1e-7:
            continue
        center = np.asarray(part.geometry.centroid, dtype=float)
        transform = translation(center) @ scale([factor, factor, factor]) @ translation(-center)
        part.geometry.apply_transform(transform)


def _remap_materials(builder: GrammarAssetBuilder, language: DesignLanguage) -> dict[str, int]:
    counts: dict[str, int] = {}
    for part in builder.parts:
        target = _semantic_override(language, part.semantic_part)
        if target is None:
            target = language.material_remap.get(part.material, part.material)
        if target not in builder.materials:
            raise KeyError(f"design language material {target} is not registered")
        part.material = target
        part.geometry = apply_material(part.geometry.copy(), builder.materials[target][1])
        part.geometry.metadata["material_name"] = target
        part.geometry.metadata["design_language"] = language.language_id
        counts[target] = counts.get(target, 0) + 1
    return counts


def _semantic_bounds(builder: GrammarAssetBuilder, prefixes: tuple[str, ...]) -> np.ndarray:
    points: list[np.ndarray] = []
    for part in builder.parts:
        if part.parent != builder.root_name or not part.semantic_part.startswith(prefixes):
            continue
        vertices = np.asarray(part.geometry.vertices, dtype=float)
        homogeneous = np.c_[vertices, np.ones(len(vertices))]
        world = (homogeneous @ np.asarray(part.local_transform, dtype=float).T)[:, :3]
        points.append(world)
    if not points:
        return builder.build_scene(False).bounds
    merged = np.vstack(points)
    return np.vstack([merged.min(axis=0), merged.max(axis=0)])


def _motif_bounds(builder: GrammarAssetBuilder) -> tuple[np.ndarray, np.ndarray]:
    variant = builder.variant
    if variant == "articulated_emitter":
        anchor = _semantic_bounds(builder, ("support.base", "support.edge_detail", "interface.base_bezel"))
        return anchor, _semantic_bounds(builder, ("support.foot", "support.underside"))
    if variant == "hinged_protective_shell":
        anchor = _semantic_bounds(builder, ("shell.lower.", "closure.", "protection.corner"))
        return anchor, _semantic_bounds(builder, ("support.foot", "support.skid"))
    if variant == "four_leg_service_station":
        anchor = _semantic_bounds(builder, ("joinery.apron", "storage.drawer_front", "surface.load"))
        return anchor, _semantic_bounds(builder, ("support.leg", "support.foot"))
    if variant == "portable_slot_organizer":
        anchor = _semantic_bounds(builder, ("shell.retention.", "support.ballast", "protection.bumper"))
        return anchor, _semantic_bounds(builder, ("support.foot", "support.ballast"))
    bounds = builder.build_scene(False).bounds
    return bounds, bounds


def _add_field_service_motifs(builder: GrammarAssetBuilder, language: DesignLanguage) -> list[str]:
    anchor_bounds, _ = _motif_bounds(builder)
    minimum, maximum = anchor_bounds
    extents = np.maximum(maximum - minimum, 0.1)
    center = (minimum + maximum) / 2.0
    width, height, depth = (float(value) for value in extents)
    y_low = float(minimum[1] + max(0.055, height * 0.055))
    front = float(maximum[2] - max(0.012, depth * 0.010))
    names: list[str] = []

    rail = rounded_box((max(0.45, width * 0.62), max(0.045, height * 0.035), max(0.045, depth * 0.035)), radius=max(0.018, min(width, depth) * 0.015), segments=5)
    builder.add_part("LanguageServiceRail", "language_service_rail", builder.root_name, "design_language.service_rail", language.material_roles["accent"], rail, translation([center[0], y_low + height * 0.10, front]))
    names.append("LanguageServiceRail")

    for index, sx in enumerate((-1.0, 1.0)):
        guard = rounded_box((max(0.10, width * 0.075), max(0.10, height * 0.13), max(0.10, depth * 0.10)), radius=max(0.025, min(width, depth) * 0.025), segments=6)
        builder.add_part(f"LanguageFrontGuard{index + 1}", f"language_front_guard_{index + 1}", builder.root_name, "design_language.protective_guard", language.material_roles["accent"], guard, translation([center[0] + sx * width * 0.40, y_low + height * 0.08, front - depth * 0.025]))
        names.append(f"LanguageFrontGuard{index + 1}")

    bolt_points = [[center[0] + x * width * 0.24, y_low + height * 0.10, front + depth * 0.018] for x in (-1.0, -0.33, 0.33, 1.0)]
    RepetitionGrammar.fasteners(builder, parent=builder.root_name, prefix="LanguageServiceBolt", points=bolt_points, radius=max(0.017, min(width, depth) * 0.018), material=language.material_roles["hardware"], axis="z")
    names.extend([f"LanguageServiceBolt{i + 1}" for i in range(len(bolt_points))])

    for index, x in enumerate((-0.27, 0.0, 0.27)):
        slot = rounded_box((max(0.045, width * 0.075), max(0.035, height * 0.025), max(0.022, depth * 0.020)), radius=max(0.008, min(width, depth) * 0.007), segments=3)
        builder.add_part(f"LanguageServiceVent{index + 1}", f"language_service_vent_{index + 1}", builder.root_name, "design_language.service_vent", language.material_roles["secondary"], slot, translation([center[0] + x * width, y_low + height * 0.19, front + depth * 0.010]))
        names.append(f"LanguageServiceVent{index + 1}")
    return names


def _add_precision_lab_motifs(builder: GrammarAssetBuilder, language: DesignLanguage) -> list[str]:
    anchor_bounds, foot_bounds = _motif_bounds(builder)
    minimum, maximum = anchor_bounds
    extents = np.maximum(maximum - minimum, 0.1)
    center = (minimum + maximum) / 2.0
    width, height, depth = (float(value) for value in extents)
    front = float(maximum[2] - max(0.010, depth * 0.007))
    y_low = float(minimum[1] + max(0.040, height * 0.040))
    names: list[str] = []

    band = rounded_box((max(0.42, width * 0.70), max(0.028, height * 0.020), max(0.024, depth * 0.018)), radius=max(0.008, min(width, depth) * 0.006), segments=4)
    builder.add_part("LanguageControlBand", "language_control_band", builder.root_name, "design_language.control_band", language.material_roles["accent"], band, translation([center[0], y_low + height * 0.19, front]))
    names.append("LanguageControlBand")

    trim = rounded_box((max(0.44, width * 0.76), max(0.024, height * 0.016), max(0.018, depth * 0.014)), radius=max(0.006, min(width, depth) * 0.005), segments=4)
    builder.add_part("LanguagePrecisionTrim", "language_precision_trim", builder.root_name, "design_language.precision_trim", language.material_roles["hardware"], trim, translation([center[0], y_low + height * 0.25, front - depth * 0.008]))
    names.append("LanguagePrecisionTrim")

    for index, x in enumerate(np.linspace(-0.28, 0.28, 7)):
        slot = rounded_box((max(0.018, width * 0.028), max(0.025, height * 0.018), max(0.012, depth * 0.010)), radius=max(0.004, min(width, depth) * 0.0035), segments=3)
        builder.add_part(f"LanguageFineVent{index + 1}", f"language_fine_vent_{index + 1}", builder.root_name, "design_language.fine_vent", language.material_roles["secondary"], slot, translation([center[0] + x * width, y_low + height * 0.115, front + depth * 0.005]))
        names.append(f"LanguageFineVent{index + 1}")

    foot_minimum, foot_maximum = foot_bounds
    foot_center = (foot_minimum + foot_maximum) / 2.0
    foot_extents = np.maximum(foot_maximum - foot_minimum, 0.1)
    for index, sx in enumerate((-1.0, 1.0)):
        foot = rounded_box((max(0.075, float(foot_extents[0]) * 0.055), max(0.035, float(foot_extents[1]) * 0.025), max(0.075, float(foot_extents[2]) * 0.060)), radius=max(0.012, min(float(foot_extents[0]), float(foot_extents[2])) * 0.010), segments=5)
        builder.add_part(f"LanguagePrecisionFoot{index + 1}", f"language_precision_foot_{index + 1}", builder.root_name, "design_language.precision_foot", language.material_roles["contact"], foot, translation([foot_center[0] + sx * float(foot_extents[0]) * 0.33, float(foot_minimum[1]) + max(0.015, float(foot_extents[1]) * 0.02), foot_center[2] + float(foot_extents[2]) * 0.24]))
        names.append(f"LanguagePrecisionFoot{index + 1}")
    return names


def apply_design_language(builder: GrammarAssetBuilder, language: DesignLanguage) -> GrammarAssetBuilder:
    """Apply a persistent product-language grammar to an already functional builder."""
    before = {"parts": len(builder.parts), "materials": sorted({part.material for part in builder.parts}), "design_language": builder.functional_metadata.get("design_language")}
    _scale_geometry(builder, language)
    remapped = _remap_materials(builder, language)
    if language.motif_id == "rugged_service_frame":
        motifs = _add_field_service_motifs(builder, language)
    elif language.motif_id == "precision_control_band":
        motifs = _add_precision_lab_motifs(builder, language)
    else:
        raise ValueError(f"unimplemented design-language motif: {language.motif_id}")

    builder.capability_id = "objectforge.procedural-design-language.v1"
    builder.functional_metadata["design_language"] = language.to_dict()
    builder.functional_metadata["design_language_id"] = language.language_id
    builder.functional_metadata["design_language_fingerprint"] = language.fingerprint
    builder.interaction = {**builder.interaction, "design_language": language.language_id, "interaction_tokens": language.interaction_tokens}
    builder.op(
        "design_language.apply",
        language.language_id,
        "Apply coherent product DNA across proportions, materials, controls, seams, fasteners, labels, and signature motifs.",
        {"fingerprint": language.fingerprint, "material_roles": language.material_roles, "proportion_tokens": language.proportion_tokens, "surface_tokens": language.surface_tokens, "interaction_tokens": language.interaction_tokens, "motif_nodes": motifs, "material_usage": remapped},
        before=before,
        after={"parts": len(builder.parts), "materials": sorted({part.material for part in builder.parts}), "design_language": language.language_id},
    )
    builder.op(
        "design_language.verify",
        language.language_id,
        "Verify that the functional architecture retains its requirements while visibly inheriting the selected design language.",
        {"motif_count": len(motifs), "fingerprint": language.fingerprint, "selected_architecture": builder.functional_metadata.get("selected_architecture")},
    )
    return builder
