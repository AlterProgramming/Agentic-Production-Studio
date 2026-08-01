from __future__ import annotations

from dataclasses import dataclass

from .contracts import (
    InterfaceEndpoint,
    InterfaceStandard,
    ObjectRole,
    SystemBrief,
    SystemConnection,
    SystemPlan,
    SystemWorkflow,
    TopologyCandidate,
)


@dataclass(frozen=True)
class SystemPlanner:
    """Bounded planner for the Scope 4 benchmark system."""

    def plan(self, brief: SystemBrief) -> SystemPlan:
        standards = _interface_standards()
        endpoints = _endpoints()
        objects = _object_roles()
        candidates = _topology_candidates(brief)
        selected = max(candidates, key=lambda item: item.score)
        if selected.topology_id != "shared_hub_and_carrier":
            raise ValueError("Scope 4 benchmark expected the shared hub-and-carrier topology")
        return SystemPlan(
            brief=brief,
            selected_topology=selected.topology_id,
            topology_candidates=candidates,
            objects=objects,
            standards=standards,
            endpoints=endpoints,
            connections=_connections(),
            workflows=_workflows(),
            layout_m={
                "service_hub": (0.0, 0.0, 0.0),
                "work_emitter": (-1.45, 0.0, -0.10),
                "protected_carrier": (1.70, 0.0, 0.15),
                "instrument_caddy": (0.15, 0.0, 1.35),
                "power_module": (-0.34, 1.08, -0.10),
                "analysis_module": (0.34, 1.08, -0.10),
            },
            object_yaw_degrees={
                "service_hub": 0.0,
                "work_emitter": 18.0,
                "protected_carrier": -18.0,
                "instrument_caddy": 180.0,
                "power_module": 0.0,
                "analysis_module": 0.0,
            },
        )


def benchmark_system_brief() -> SystemBrief:
    return SystemBrief(
        system_id="modular_observation_and_service_cell",
        label="Modular Observation and Service Cell",
        intent=(
            "Provide a portable, reconfigurable system for illuminating a work area, powering and hosting "
            "analysis modules, organizing instruments, protecting the equipment in transit, and restoring the "
            "system to a compact transport state."
        ),
        required_capabilities=(
            "stable_work_surface",
            "directional_illumination",
            "protected_transport",
            "visible_instrument_access",
            "portable_power",
            "analysis_and_status",
            "shared_mechanical_mounting",
            "shared_power_and_data",
            "transport_stowage",
            "reconfigurable_workflow",
        ),
        constraints={
            "maximum_deployed_footprint_m": [4.5, 3.2],
            "minimum_object_count": 6,
            "minimum_shared_interface_standards": 3,
            "minimum_active_connections": 5,
            "must_have_transport_state": True,
            "must_have_operational_state": True,
            "external_finished_model_provider": False,
        },
    )


def default_system_planner() -> SystemPlanner:
    return SystemPlanner()


def _interface_standards() -> tuple[InterfaceStandard, ...]:
    return (
        InterfaceStandard(
            standard_id="ofx_rail_240_v1",
            label="OFX 240 mm keyed mechanical rail",
            interface_kind="mechanical_mount",
            dimensions_m={"width": 0.240, "height": 0.038, "depth": 0.052, "key_offset": 0.031},
            tolerance_m=0.0015,
            compatible_polarities=(("host", "module"),),
            payload_contract={"maximum_static_load_kg": 18.0, "locking": "dual_spring_latch"},
            geometry_contract={"profile": "keyed_trapezoid", "datum": "centerline", "insertion_axis": [0, 0, -1]},
        ),
        InterfaceStandard(
            standard_id="ofx_bus_24d_v1",
            label="OFX 24 V power and data bus",
            interface_kind="power_data",
            dimensions_m={"width": 0.084, "height": 0.046, "depth": 0.036, "key_radius": 0.011},
            tolerance_m=0.0008,
            compatible_polarities=(("source", "sink"), ("host", "device")),
            payload_contract={"voltage_v": 24.0, "maximum_current_a": 8.0, "data": "differential_pair_v1"},
            geometry_contract={"profile": "keyed_rectangular", "contact_count": 6, "insertion_axis": [0, 0, -1]},
        ),
        InterfaceStandard(
            standard_id="ofx_module_bay_360_v1",
            label="OFX 360 mm cartridge bay",
            interface_kind="module_bay",
            dimensions_m={"width": 0.360, "height": 0.220, "depth": 0.430, "guide_spacing": 0.286},
            tolerance_m=0.0020,
            compatible_polarities=(("bay", "cartridge"),),
            payload_contract={"maximum_module_mass_kg": 9.0, "retention": "front_quarter_turn"},
            geometry_contract={"profile": "dual_guide_cartridge", "datum": "lower_rear", "insertion_axis": [0, 0, -1]},
        ),
        InterfaceStandard(
            standard_id="ofx_stack_480_v1",
            label="OFX 480 mm transport stack interface",
            interface_kind="transport_stack",
            dimensions_m={"width": 0.480, "height": 0.030, "depth": 0.320, "corner_key": 0.040},
            tolerance_m=0.0025,
            compatible_polarities=(("receiver", "stacker"),),
            payload_contract={"maximum_stack_mass_kg": 16.0, "retention": "four_corner_capture"},
            geometry_contract={"profile": "four_key_stack", "datum": "base_plane", "insertion_axis": [0, -1, 0]},
        ),
    )


def _object_roles() -> tuple[ObjectRole, ...]:
    return (
        ObjectRole(
            object_id="service_hub",
            label="Service Hub",
            builder_key="elevated-service",
            architecture_id="four_leg_service_station",
            capabilities=("stable_work_surface", "shared_mechanical_mounting", "shared_power_and_data"),
            endpoint_ids=("hub_rail_left", "hub_rail_right", "hub_bus_left", "hub_bus_right", "hub_bay_left", "hub_bay_right"),
            root_object=True,
            portable=False,
        ),
        ObjectRole(
            object_id="work_emitter",
            label="Directional Work Emitter",
            builder_key="directional-energy",
            architecture_id="articulated_emitter",
            capabilities=("directional_illumination", "reconfigurable_workflow"),
            endpoint_ids=("emitter_rail", "emitter_bus"),
            root_object=False,
            portable=True,
        ),
        ObjectRole(
            object_id="protected_carrier",
            label="Protected Carrier",
            builder_key="protected-transport",
            architecture_id="hinged_protective_shell",
            capabilities=("protected_transport", "transport_stowage"),
            endpoint_ids=("carrier_bay_left", "carrier_bay_right", "carrier_stack_receiver"),
            root_object=False,
            portable=True,
        ),
        ObjectRole(
            object_id="instrument_caddy",
            label="Instrument Caddy",
            builder_key="visible-organization",
            architecture_id="portable_slot_organizer",
            capabilities=("visible_instrument_access", "transport_stowage"),
            endpoint_ids=("caddy_rail", "caddy_stack"),
            root_object=False,
            portable=True,
        ),
        ObjectRole(
            object_id="power_module",
            label="Portable Power Module",
            builder_key="system_module.power",
            architecture_id="portable_power_cartridge",
            capabilities=("portable_power", "shared_power_and_data", "transport_stowage"),
            endpoint_ids=("power_cartridge", "power_bus_out"),
            root_object=False,
            portable=True,
        ),
        ObjectRole(
            object_id="analysis_module",
            label="Analysis and Status Module",
            builder_key="system_module.analysis",
            architecture_id="analysis_status_cartridge",
            capabilities=("analysis_and_status", "shared_power_and_data", "transport_stowage"),
            endpoint_ids=("analysis_cartridge", "analysis_bus_in"),
            root_object=False,
            portable=True,
        ),
    )


def _endpoints() -> tuple[InterfaceEndpoint, ...]:
    return (
        InterfaceEndpoint("hub_rail_left", "service_hub", "ofx_rail_240_v1", "host", (-0.47, 1.13, -0.34), (0, 0, 1), {"load_kg": 12}, ("operational",)),
        InterfaceEndpoint("hub_rail_right", "service_hub", "ofx_rail_240_v1", "host", (0.47, 1.13, -0.34), (0, 0, 1), {"load_kg": 12}, ("operational",)),
        InterfaceEndpoint("hub_bus_left", "service_hub", "ofx_bus_24d_v1", "source", (-0.28, 1.03, -0.39), (0, 0, 1), {"current_a": 4}, ("operational",)),
        InterfaceEndpoint("hub_bus_right", "service_hub", "ofx_bus_24d_v1", "host", (0.28, 1.03, -0.39), (0, 0, 1), {"current_a": 4}, ("operational",)),
        InterfaceEndpoint("hub_bay_left", "service_hub", "ofx_module_bay_360_v1", "bay", (-0.36, 0.67, 0.08), (0, 0, 1), {"mass_kg": 9}, ("operational",)),
        InterfaceEndpoint("hub_bay_right", "service_hub", "ofx_module_bay_360_v1", "bay", (0.36, 0.67, 0.08), (0, 0, 1), {"mass_kg": 9}, ("operational",)),
        InterfaceEndpoint("emitter_rail", "work_emitter", "ofx_rail_240_v1", "module", (0.0, 0.05, -0.58), (0, 0, -1), {"load_kg": 4}, ("operational",)),
        InterfaceEndpoint("emitter_bus", "work_emitter", "ofx_bus_24d_v1", "sink", (0.0, 0.18, -0.62), (0, 0, -1), {"current_a": 2.5}, ("operational",)),
        InterfaceEndpoint("carrier_bay_left", "protected_carrier", "ofx_module_bay_360_v1", "bay", (-0.43, 0.16, 0.02), (0, 0, 1), {"mass_kg": 9}, ("transport",)),
        InterfaceEndpoint("carrier_bay_right", "protected_carrier", "ofx_module_bay_360_v1", "bay", (0.43, 0.16, 0.02), (0, 0, 1), {"mass_kg": 9}, ("transport",)),
        InterfaceEndpoint("carrier_stack_receiver", "protected_carrier", "ofx_stack_480_v1", "receiver", (0.0, 0.57, 0.0), (0, 1, 0), {"mass_kg": 16}, ("transport",)),
        InterfaceEndpoint("caddy_rail", "instrument_caddy", "ofx_rail_240_v1", "module", (0.0, 0.05, -0.27), (0, 0, -1), {"load_kg": 5}, ("operational",)),
        InterfaceEndpoint("caddy_stack", "instrument_caddy", "ofx_stack_480_v1", "stacker", (0.0, 0.02, 0.0), (0, -1, 0), {"mass_kg": 5}, ("transport",)),
        InterfaceEndpoint("power_cartridge", "power_module", "ofx_module_bay_360_v1", "cartridge", (0.0, 0.11, -0.22), (0, 0, -1), {"mass_kg": 6}, ("operational", "transport")),
        InterfaceEndpoint("power_bus_out", "power_module", "ofx_bus_24d_v1", "source", (0.0, 0.22, 0.23), (0, 0, 1), {"current_a": 8}, ("operational",)),
        InterfaceEndpoint("analysis_cartridge", "analysis_module", "ofx_module_bay_360_v1", "cartridge", (0.0, 0.11, -0.22), (0, 0, -1), {"mass_kg": 5}, ("operational", "transport")),
        InterfaceEndpoint("analysis_bus_in", "analysis_module", "ofx_bus_24d_v1", "device", (0.0, 0.22, 0.23), (0, 0, 1), {"current_a": 2}, ("operational",)),
    )


def _connections() -> tuple[SystemConnection, ...]:
    return (
        SystemConnection("mount_emitter", "hub_rail_left", "emitter_rail", "mechanical", True, ("deploy", "operate")),
        SystemConnection("power_emitter", "hub_bus_left", "emitter_bus", "power", True, ("operate",)),
        SystemConnection("mount_caddy", "hub_rail_right", "caddy_rail", "mechanical", True, ("deploy", "operate")),
        SystemConnection("dock_power", "hub_bay_left", "power_cartridge", "module", True, ("deploy", "operate", "charge")),
        SystemConnection("dock_analysis", "hub_bay_right", "analysis_cartridge", "module", True, ("deploy", "operate")),
        SystemConnection("power_analysis", "power_bus_out", "analysis_bus_in", "power_data", True, ("operate",)),
        SystemConnection("stack_caddy", "carrier_stack_receiver", "caddy_stack", "transport", False, ("stow", "transport")),
        SystemConnection("stow_power", "carrier_bay_left", "power_cartridge", "transport", False, ("stow", "transport")),
        SystemConnection("stow_analysis", "carrier_bay_right", "analysis_cartridge", "transport", False, ("stow", "transport")),
    )


def _workflows() -> tuple[SystemWorkflow, ...]:
    return (
        SystemWorkflow(
            workflow_id="deploy_and_operate",
            label="Deploy, illuminate, analyze, and service",
            ordered_steps=(
                {"step": 1, "action": "position", "object": "service_hub"},
                {"step": 2, "action": "dock", "connection": "dock_power"},
                {"step": 3, "action": "dock", "connection": "dock_analysis"},
                {"step": 4, "action": "mount", "connection": "mount_emitter"},
                {"step": 5, "action": "mount", "connection": "mount_caddy"},
                {"step": 6, "action": "connect", "connection": "power_analysis"},
                {"step": 7, "action": "connect", "connection": "power_emitter"},
                {"step": 8, "action": "operate", "objects": ["work_emitter", "analysis_module", "instrument_caddy"]},
            ),
            required_objects=("service_hub", "work_emitter", "instrument_caddy", "power_module", "analysis_module"),
            required_connections=("dock_power", "dock_analysis", "mount_emitter", "mount_caddy", "power_analysis", "power_emitter"),
        ),
        SystemWorkflow(
            workflow_id="stow_and_transport",
            label="Collapse the system into protected transport",
            ordered_steps=(
                {"step": 1, "action": "disconnect", "connections": ["power_analysis", "power_emitter"]},
                {"step": 2, "action": "undock", "connections": ["dock_power", "dock_analysis"]},
                {"step": 3, "action": "stow", "connection": "stow_power"},
                {"step": 4, "action": "stow", "connection": "stow_analysis"},
                {"step": 5, "action": "stack", "connection": "stack_caddy"},
                {"step": 6, "action": "close", "object": "protected_carrier"},
            ),
            required_objects=("protected_carrier", "instrument_caddy", "power_module", "analysis_module"),
            required_connections=("stow_power", "stow_analysis", "stack_caddy"),
        ),
    )


def _topology_candidates(brief: SystemBrief) -> tuple[TopologyCandidate, ...]:
    required = tuple(brief.required_capabilities)
    return (
        TopologyCandidate(
            topology_id="shared_hub_and_carrier",
            label="Shared operational hub plus protected transport carrier",
            capability_coverage=required,
            connection_reuse=9,
            orphan_risk=0.0,
            workflow_cost=0.18,
            transport_cost=0.22,
            complexity=0.42,
            score=0.91,
        ),
        TopologyCandidate(
            topology_id="carrier_centric",
            label="Carrier acts as both transport shell and operational surface",
            capability_coverage=tuple(item for item in required if item != "stable_work_surface"),
            connection_reuse=7,
            orphan_risk=0.08,
            workflow_cost=0.30,
            transport_cost=0.12,
            complexity=0.37,
            score=0.74,
        ),
        TopologyCandidate(
            topology_id="distributed_pairwise",
            label="Independent objects connect directly without a shared hub",
            capability_coverage=tuple(item for item in required if item != "shared_mechanical_mounting"),
            connection_reuse=4,
            orphan_risk=0.24,
            workflow_cost=0.48,
            transport_cost=0.31,
            complexity=0.58,
            score=0.55,
        ),
        TopologyCandidate(
            topology_id="single_monolith",
            label="One integrated enclosure contains every capability",
            capability_coverage=required,
            connection_reuse=1,
            orphan_risk=0.0,
            workflow_cost=0.12,
            transport_cost=0.45,
            complexity=0.82,
            score=0.49,
        ),
    )
