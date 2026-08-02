from __future__ import annotations

import math
from typing import Iterable

import numpy as np

from objectforge.design.language import DesignLanguage, apply_design_language
from objectforge.geometry import cylinder_y, cylinder_z, rounded_box, torus_y, translation, tube_along
from objectforge.grammar.core import GrammarAssetBuilder
from objectforge.grammar.library import JoineryGrammar, RepetitionGrammar
from objectforge.planning.functional import benchmark_briefs, default_planner
from objectforge.functional.refined import build_functional_architecture

from .contracts import InterfaceEndpoint, InterfaceStandard, ObjectRole


CAPABILITY_ID = "objectforge.multi-object-coherent-systems.v1"


def build_role_builder(
    role: ObjectRole,
    *,
    language: DesignLanguage,
    endpoints: tuple[InterfaceEndpoint, ...],
    standards: tuple[InterfaceStandard, ...],
) -> tuple[GrammarAssetBuilder, object | None]:
    functional_brief = next((item for item in benchmark_briefs() if item.brief_id == role.builder_key), None)
    functional_plan = None
    if functional_brief is not None:
        functional_plan = default_planner().plan(functional_brief)
        builder = build_functional_architecture(functional_plan)
        if builder.variant != role.architecture_id:
            raise ValueError(f"role {role.object_id} expected {role.architecture_id}, got {builder.variant}")
    elif role.builder_key == "system_module.power":
        builder = _build_power_module(role)
    elif role.builder_key == "system_module.analysis":
        builder = _build_analysis_module(role)
    else:
        raise KeyError(f"unknown Scope 4 builder key: {role.builder_key}")

    apply_design_language(builder, language)
    role_endpoints = tuple(item for item in endpoints if item.object_id == role.object_id)
    standard_by_id = {item.standard_id: item for item in standards}
    for endpoint in role_endpoints:
        apply_interface_geometry(builder, endpoint, standard_by_id[endpoint.standard_id], language)

    builder.capability_id = CAPABILITY_ID
    builder.family = "multi_object_system_member"
    builder.functional_metadata.update(
        {
            "system_role": role.object_id,
            "system_capabilities": list(role.capabilities),
            "system_interface_endpoints": [item.to_dict() for item in role_endpoints],
            "design_language": language.language_id,
            "design_language_fingerprint": language.fingerprint,
        }
    )
    builder.interaction = {
        **builder.interaction,
        "system_role": role.object_id,
        "system_interfaces": [item.endpoint_id for item in role_endpoints],
        "compatible_standards": sorted({item.standard_id for item in role_endpoints}),
    }
    builder.op(
        "system.role_complete",
        role.object_id,
        "Bind one independently useful object into a coherent multi-object system.",
        {
            "capabilities": list(role.capabilities),
            "endpoints": [item.endpoint_id for item in role_endpoints],
            "design_language": language.language_id,
        },
    )
    return builder, functional_plan


def apply_interface_geometry(
    builder: GrammarAssetBuilder,
    endpoint: InterfaceEndpoint,
    standard: InterfaceStandard,
    language: DesignLanguage,
) -> None:
    center = np.asarray(endpoint.local_position_m, dtype=float)
    prefix = _safe(endpoint.endpoint_id)
    builder.op(
        "system.interface.instantiate",
        endpoint.endpoint_id,
        "Instantiate a standardized physical and semantic interface endpoint.",
        {
            "standard_id": standard.standard_id,
            "polarity": endpoint.polarity,
            "position_m": list(endpoint.local_position_m),
            "axis": list(endpoint.local_axis),
            "tolerance_m": standard.tolerance_m,
        },
    )
    if standard.interface_kind == "mechanical_mount":
        _add_rail_interface(builder, prefix, center, endpoint.polarity, language)
    elif standard.interface_kind == "power_data":
        _add_bus_interface(builder, prefix, center, endpoint.polarity, language)
    elif standard.interface_kind == "module_bay":
        _add_module_bay_interface(builder, prefix, center, endpoint.polarity, language)
    elif standard.interface_kind == "transport_stack":
        _add_stack_interface(builder, prefix, center, endpoint.polarity, language)
    else:
        raise KeyError(f"unsupported interface kind: {standard.interface_kind}")


def _add_rail_interface(
    builder: GrammarAssetBuilder,
    prefix: str,
    center: np.ndarray,
    polarity: str,
    language: DesignLanguage,
) -> None:
    hardware = language.material_roles["hardware"]
    accent = language.material_roles["accent"]
    contact = language.material_roles["contact"]
    if polarity == "host":
        bed = rounded_box((0.30, 0.045, 0.085), radius=0.012, segments=4)
        builder.add_part(f"{prefix}RailBed", f"{prefix.lower()}_rail_bed", builder.root_name, "system_interface.rail.host_bed", hardware, bed, translation(center))
        for index, x in enumerate((-0.092, 0.092)):
            guide = rounded_box((0.055, 0.070, 0.084), radius=0.010, segments=4)
            builder.add_part(f"{prefix}RailGuide{index+1}", f"{prefix.lower()}_rail_guide_{index+1}", builder.root_name, "system_interface.rail.host_guide", hardware, guide, translation(center + [x, 0.035, 0]))
        key = rounded_box((0.035, 0.065, 0.094), radius=0.008, segments=3)
        builder.add_part(f"{prefix}RailKey", f"{prefix.lower()}_rail_key", builder.root_name, "system_interface.rail.key", accent, key, translation(center + [0.031, 0.050, 0]))
        latch = rounded_box((0.075, 0.040, 0.105), radius=0.012, segments=4)
        builder.add_part(f"{prefix}RailLatch", f"{prefix.lower()}_rail_latch", builder.root_name, "system_interface.rail.latch", accent, latch, translation(center + [0.132, 0.055, 0]))
    else:
        tongue = rounded_box((0.235, 0.040, 0.072), radius=0.010, segments=4)
        builder.add_part(f"{prefix}RailTongue", f"{prefix.lower()}_rail_tongue", builder.root_name, "system_interface.rail.module_tongue", hardware, tongue, translation(center))
        for index, x in enumerate((-0.092, 0.092)):
            pad = rounded_box((0.050, 0.020, 0.080), radius=0.007, segments=3)
            builder.add_part(f"{prefix}RailPad{index+1}", f"{prefix.lower()}_rail_pad_{index+1}", builder.root_name, "system_interface.rail.contact_pad", contact, pad, translation(center + [x, -0.027, 0]))
        key = rounded_box((0.029, 0.052, 0.080), radius=0.006, segments=3)
        builder.add_part(f"{prefix}RailKey", f"{prefix.lower()}_rail_key", builder.root_name, "system_interface.rail.key", accent, key, translation(center + [0.031, 0.038, 0]))
        detent = cylinder_y(0.018, 0.032, sections=28)
        builder.add_part(f"{prefix}RailDetent", f"{prefix.lower()}_rail_detent", builder.root_name, "system_interface.rail.detent", accent, detent, translation(center + [0.105, 0.037, 0]))


def _add_bus_interface(
    builder: GrammarAssetBuilder,
    prefix: str,
    center: np.ndarray,
    polarity: str,
    language: DesignLanguage,
) -> None:
    primary = language.material_roles["secondary"]
    hardware = language.material_roles["hardware"]
    accent = language.material_roles["accent"]
    housing = rounded_box((0.112, 0.078, 0.052), radius=0.016, segments=5)
    builder.add_part(f"{prefix}BusHousing", f"{prefix.lower()}_bus_housing", builder.root_name, "system_interface.bus.housing", primary, housing, translation(center))
    face = rounded_box((0.088, 0.052, 0.018), radius=0.010, segments=4)
    builder.add_part(f"{prefix}BusFace", f"{prefix.lower()}_bus_face", builder.root_name, "system_interface.bus.face", hardware, face, translation(center + [0, 0, 0.034]))
    pin_material = accent if polarity in {"source", "host"} else hardware
    for index, x in enumerate((-0.030, 0.0, 0.030)):
        for row, y in enumerate((-0.014, 0.014)):
            pin = cylinder_z(0.0065, 0.016, sections=24)
            builder.add_part(f"{prefix}BusPin{index+1}{row+1}", f"{prefix.lower()}_bus_pin_{index+1}_{row+1}", builder.root_name, "system_interface.bus.contact", pin_material, pin, translation(center + [x, y, 0.047]))
    key = rounded_box((0.018, 0.014, 0.025), radius=0.004, segments=3)
    builder.add_part(f"{prefix}BusKey", f"{prefix.lower()}_bus_key", builder.root_name, "system_interface.bus.key", accent, key, translation(center + [0.034, -0.025, 0.048]))


def _add_module_bay_interface(
    builder: GrammarAssetBuilder,
    prefix: str,
    center: np.ndarray,
    polarity: str,
    language: DesignLanguage,
) -> None:
    hardware = language.material_roles["hardware"]
    accent = language.material_roles["accent"]
    contact = language.material_roles["contact"]
    if polarity == "bay":
        frame = rounded_box((0.405, 0.265, 0.060), radius=0.025, segments=5)
        builder.add_part(f"{prefix}BayFrame", f"{prefix.lower()}_bay_frame", builder.root_name, "system_interface.module_bay.frame", hardware, frame, translation(center))
        for index, x in enumerate((-0.143, 0.143)):
            guide = rounded_box((0.038, 0.215, 0.390), radius=0.010, segments=4)
            builder.add_part(f"{prefix}BayGuide{index+1}", f"{prefix.lower()}_bay_guide_{index+1}", builder.root_name, "system_interface.module_bay.guide", hardware, guide, translation(center + [x, 0, -0.205]))
        stop = rounded_box((0.315, 0.048, 0.050), radius=0.010, segments=4)
        builder.add_part(f"{prefix}BayStop", f"{prefix.lower()}_bay_stop", builder.root_name, "system_interface.module_bay.stop", contact, stop, translation(center + [0, -0.102, -0.405]))
        latch = cylinder_z(0.030, 0.060, sections=40)
        builder.add_part(f"{prefix}BayLatch", f"{prefix.lower()}_bay_latch", builder.root_name, "system_interface.module_bay.latch", accent, latch, translation(center + [0.170, 0.0, 0.034]))
    else:
        back = rounded_box((0.345, 0.215, 0.055), radius=0.020, segments=5)
        builder.add_part(f"{prefix}CartridgeBack", f"{prefix.lower()}_cartridge_back", builder.root_name, "system_interface.module_bay.cartridge_back", hardware, back, translation(center))
        for index, x in enumerate((-0.143, 0.143)):
            skid = rounded_box((0.030, 0.185, 0.405), radius=0.008, segments=4)
            builder.add_part(f"{prefix}CartridgeSkid{index+1}", f"{prefix.lower()}_cartridge_skid_{index+1}", builder.root_name, "system_interface.module_bay.cartridge_guide", hardware, skid, translation(center + [x, 0, -0.202]))
        bumper = rounded_box((0.290, 0.038, 0.045), radius=0.009, segments=4)
        builder.add_part(f"{prefix}CartridgeBumper", f"{prefix.lower()}_cartridge_bumper", builder.root_name, "system_interface.module_bay.cartridge_bumper", contact, bumper, translation(center + [0, -0.092, -0.405]))
        lock = cylinder_z(0.027, 0.052, sections=40)
        builder.add_part(f"{prefix}CartridgeLock", f"{prefix.lower()}_cartridge_lock", builder.root_name, "system_interface.module_bay.cartridge_lock", accent, lock, translation(center + [0.165, 0.0, 0.030]))


def _add_stack_interface(
    builder: GrammarAssetBuilder,
    prefix: str,
    center: np.ndarray,
    polarity: str,
    language: DesignLanguage,
) -> None:
    hardware = language.material_roles["hardware"]
    contact = language.material_roles["contact"]
    accent = language.material_roles["accent"]
    plate = rounded_box((0.520, 0.035, 0.360), radius=0.025, segments=5)
    builder.add_part(f"{prefix}StackPlate", f"{prefix.lower()}_stack_plate", builder.root_name, "system_interface.stack.plate", contact if polarity == "receiver" else hardware, plate, translation(center))
    for index, (sx, sz) in enumerate(((-1, -1), (-1, 1), (1, -1), (1, 1))):
        key = rounded_box((0.072, 0.055, 0.072), radius=0.015, segments=4)
        material = accent if polarity == "stacker" else hardware
        offset_y = 0.035 if polarity == "stacker" else -0.020
        builder.add_part(f"{prefix}StackKey{index+1}", f"{prefix.lower()}_stack_key_{index+1}", builder.root_name, "system_interface.stack.key", material, key, translation(center + [sx * 0.205, offset_y, sz * 0.125]))


def _new_module_builder(role: ObjectRole, *, label: str) -> GrammarAssetBuilder:
    builder = GrammarAssetBuilder(
        asset_id=f"scope4-{role.object_id}",
        family="system_module",
        variant=role.architecture_id,
        root_name="SystemModuleRoot",
        dimensions={"width": 0.62, "height": 0.42, "depth": 0.48},
        capability_id=CAPABILITY_ID,
        functional_metadata={
            "system_role": role.object_id,
            "system_capabilities": list(role.capabilities),
            "module_label": label,
        },
    )
    builder.op(
        "system.module.begin",
        role.object_id,
        "Construct a close-inspectable cartridge that remains independently useful outside the system.",
        {"label": label, "architecture_id": role.architecture_id},
    )
    shell = rounded_box((0.62, 0.42, 0.48), radius=0.065, segments=7)
    builder.add_part("ModuleShell", "module_shell", builder.root_name, "shell.module.body", "GraphitePowderCoat", shell, translation([0, 0.24, 0]))
    front = rounded_box((0.56, 0.34, 0.055), radius=0.045, segments=6)
    builder.add_part("ModuleFront", "module_front", builder.root_name, "shell.module.front_panel", "MoldedBlack", front, translation([0, 0.24, 0.267]))
    rear = rounded_box((0.54, 0.32, 0.045), radius=0.040, segments=6)
    builder.add_part("ModuleRear", "module_rear", builder.root_name, "shell.module.rear_panel", "MoldedBlack", rear, translation([0, 0.24, -0.265]))
    underside = rounded_box((0.52, 0.055, 0.38), radius=0.030, segments=5)
    builder.add_part("ModuleUnderside", "module_underside", builder.root_name, "support.underside", "DarkRubber", underside, translation([0, 0.045, 0]))
    for index, (sx, sz) in enumerate(((-1, -1), (-1, 1), (1, -1), (1, 1))):
        guard = rounded_box((0.105, 0.34, 0.105), radius=0.035, segments=5)
        builder.add_part(f"ModuleGuard{index+1}", f"module_guard_{index+1}", builder.root_name, "protection.corner", "SignalOrange", guard, translation([sx * 0.265, 0.235, sz * 0.195]))
        foot = rounded_box((0.095, 0.045, 0.095), radius=0.022, segments=4)
        builder.add_part(f"ModuleFoot{index+1}", f"module_foot_{index+1}", builder.root_name, "support.foot", "DarkRubber", foot, translation([sx * 0.235, 0.022, sz * 0.165]))
    JoineryGrammar.handle(builder, parent=builder.root_name, prefix="ModuleCarry", center=[0, 0.48, -0.02], width=0.32, height=0.16, material="DarkRubber")
    RepetitionGrammar.fasteners(
        builder,
        parent=builder.root_name,
        prefix="ModulePanel",
        points=[[sx * 0.235, 0.37 if sy > 0 else 0.11, 0.299] for sx in (-1, 1) for sy in (-1, 1)],
        radius=0.020,
        material="BrushedSteel",
        axis="z",
    )
    for index, x in enumerate(np.linspace(-0.19, 0.19, 7)):
        vent = rounded_box((0.035, 0.12, 0.026), radius=0.008, segments=3)
        builder.add_part(f"ModuleVent{index+1}", f"module_vent_{index+1}", builder.root_name, "detail.vent_slot", "MoldedBlack", vent, translation([x, 0.26, -0.294]))
    rating = rounded_box((0.24, 0.055, 0.018), radius=0.012, segments=4)
    builder.add_part("ModuleRatingPlate", "module_rating_plate", builder.root_name, "detail.identification_plate", "WarmAluminum", rating, translation([0, 0.13, 0.299]))
    builder.add_body(body_id=role.object_id, node=builder.root_name, body_type="dynamic", mass=4.8, collision={"shape": "rounded_box", "extents": [0.62, 0.42, 0.48]}, friction=0.72)
    return builder


def _build_power_module(role: ObjectRole) -> GrammarAssetBuilder:
    builder = _new_module_builder(role, label="Portable Power Module")
    for index, x in enumerate((-0.18, -0.06, 0.06, 0.18)):
        for row, z in enumerate((-0.09, 0.09)):
            cell = cylinder_y(0.048, 0.24, sections=48)
            builder.add_part(f"EnergyCell{index+1}{row+1}", f"energy_cell_{index+1}_{row+1}", builder.root_name, "energy.cell", "MoldedBlue", cell, translation([x, 0.24, z]))
    for index, z in enumerate((-0.125, 0.125)):
        cradle = rounded_box((0.50, 0.045, 0.070), radius=0.015, segments=4)
        builder.add_part(
            f"ThermalIsolationCradle{index+1}",
            f"thermal_isolation_cradle_{index+1}",
            builder.root_name,
            "energy.thermal_isolation_cradle",
            "CarbonInsert",
            cradle,
            translation([0, 0.105, z]),
        )
    busbar = rounded_box((0.46, 0.035, 0.12), radius=0.012, segments=4)
    builder.add_part("PowerBusbar", "power_busbar", builder.root_name, "energy.busbar", "BrushedSteel", busbar, translation([0, 0.37, 0]))
    for index, x in enumerate((-0.15, -0.05, 0.05, 0.15)):
        indicator = cylinder_z(0.018, 0.024, sections=32)
        builder.add_part(f"ChargeIndicator{index+1}", f"charge_indicator_{index+1}", builder.root_name, "interface.status_indicator", "WarmEmitter", indicator, translation([x, 0.31, 0.304]))
    breaker = cylinder_z(0.050, 0.048, sections=48)
    builder.add_part("PowerBreaker", "power_breaker", builder.root_name, "interface.breaker", "SignalOrange", breaker, translation([0.22, 0.23, 0.305]))
    fuse = rounded_box((0.12, 0.07, 0.025), radius=0.012, segments=4)
    builder.add_part("FuseServiceDoor", "fuse_service_door", builder.root_name, "interface.service_door", "WarmAluminum", fuse, translation([-0.21, 0.22, 0.306]))
    builder.recovery = {
        "status": "recovered",
        "forced_failure": {"finding": "unkeyed power cartridge orientation"},
        "alternative_comparison": [
            {"repair": "add_color_only_marker", "accepted": False},
            {"repair": "add_physical_key_and_bus polarity", "accepted": True},
        ],
        "rollback": {"preserved_prior_state": True},
        "source_overwritten": False,
    }
    builder.op("planner.try_alternative", "power_module_key", "Reject a visually marked but physically reversible power module.", {"alternative": "color_only_orientation"}, status="rejected")
    builder.op("planner.compare_repairs", "power_module_key", "Select physical keying over a color-only instruction.", {"selected": "add_physical_key_and_bus polarity"})
    builder.op("rollback", "checkpoint.power_module_shell", "Preserve the completed module shell while adding the keyed interface.", {"preserved_prior_state": True})
    builder.op("functional.verify", role.object_id, "Verify portable power, service access, status signaling, thermal isolation, and docking readiness.", {"covered_capabilities": list(role.capabilities)})
    builder.op("refinement.verify_close_inspection", role.object_id, "Verify cells, thermal isolation cradles, busbar, breaker, service door, vents, guards, handle, and underside.", {"detail_groups": ["cells", "thermal_isolation", "busbar", "breaker", "service_door", "vents", "guards"]})
    return builder


def _build_analysis_module(role: ObjectRole) -> GrammarAssetBuilder:
    builder = _new_module_builder(role, label="Analysis and Status Module")
    screen_frame = rounded_box((0.38, 0.20, 0.034), radius=0.030, segments=6)
    builder.add_part("AnalysisScreenFrame", "analysis_screen_frame", builder.root_name, "interface.display_frame", "WarmAluminum", screen_frame, translation([0, 0.27, 0.306]))
    screen = rounded_box((0.33, 0.15, 0.020), radius=0.020, segments=5)
    builder.add_part("AnalysisScreen", "analysis_screen", builder.root_name, "interface.display", "MoldedBlue", screen, translation([0, 0.27, 0.330]))
    for index, x in enumerate((-0.18, -0.06, 0.06, 0.18)):
        knob = cylinder_z(0.026, 0.035, sections=40)
        builder.add_part(f"AnalysisControl{index+1}", f"analysis_control_{index+1}", builder.root_name, "interface.control_knob", "SignalOrange", knob, translation([x, 0.13, 0.315]))
    for index, x in enumerate((-0.18, -0.09, 0.0, 0.09, 0.18)):
        port = torus_y(0.024, 0.008, 40, 10)
        port.apply_transform(np.array([[1,0,0,0],[0,0,-1,0],[0,1,0,0],[0,0,0,1]], dtype=float))
        builder.add_part(f"SensorPort{index+1}", f"sensor_port_{index+1}", builder.root_name, "interface.sensor_port", "BrushedSteel", port, translation([x, 0.12, -0.295]))
    processor = rounded_box((0.34, 0.045, 0.22), radius=0.018, segments=4)
    builder.add_part("AnalysisProcessor", "analysis_processor", builder.root_name, "analysis.processor", "CarbonInsert", processor, translation([0, 0.22, 0]))
    for index, x in enumerate(np.linspace(-0.16, 0.16, 5)):
        fin = rounded_box((0.018, 0.17, 0.20), radius=0.006, segments=3)
        builder.add_part(f"ProcessorFin{index+1}", f"processor_fin_{index+1}", builder.root_name, "detail.cooling_fin", "BrushedSteel", fin, translation([x, 0.22, -0.13]))
    builder.recovery = {
        "status": "recovered",
        "forced_failure": {"finding": "analysis module accepted power without data identity"},
        "alternative_comparison": [
            {"repair": "add_label_only", "accepted": False},
            {"repair": "use keyed power-data endpoint", "accepted": True},
        ],
        "rollback": {"preserved_prior_state": True},
        "source_overwritten": False,
    }
    builder.op("planner.try_alternative", "analysis_bus", "Reject a power-only connection that cannot identify the analysis device.", {"alternative": "power_only"}, status="rejected")
    builder.op("planner.compare_repairs", "analysis_bus", "Select the shared keyed power-data interface.", {"selected": "use keyed power-data endpoint"})
    builder.op("rollback", "checkpoint.analysis_module_shell", "Preserve the completed module shell while adding the shared data identity.", {"preserved_prior_state": True})
    builder.op("functional.verify", role.object_id, "Verify analysis, status display, sensor access, and docking readiness.", {"covered_capabilities": list(role.capabilities)})
    builder.op("refinement.verify_close_inspection", role.object_id, "Verify display, controls, sensor ports, processor, cooling fins, vents, guards, handle, and underside.", {"detail_groups": ["display", "controls", "ports", "processor", "cooling", "guards"]})
    return builder


def _safe(value: str) -> str:
    return "".join(part.capitalize() for part in value.replace("-", "_").split("_") if part)
