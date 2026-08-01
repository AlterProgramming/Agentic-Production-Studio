from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any


@dataclass(frozen=True)
class SystemBrief:
    system_id: str
    label: str
    intent: str
    required_capabilities: tuple[str, ...]
    constraints: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class InterfaceStandard:
    standard_id: str
    label: str
    interface_kind: str
    dimensions_m: dict[str, float]
    tolerance_m: float
    compatible_polarities: tuple[tuple[str, str], ...]
    payload_contract: dict[str, Any]
    geometry_contract: dict[str, Any]

    @property
    def effective_compatible_polarities(self) -> tuple[tuple[str, str], ...]:
        pairs = list(self.compatible_polarities)
        if self.interface_kind == "power_data" and ("source", "device") not in pairs:
            pairs.append(("source", "device"))
        return tuple(pairs)

    def compatible(self, polarity_a: str, polarity_b: str) -> bool:
        pairs = self.effective_compatible_polarities
        return (polarity_a, polarity_b) in pairs or (polarity_b, polarity_a) in pairs

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["compatible_polarities"] = [list(item) for item in self.effective_compatible_polarities]
        return result


@dataclass(frozen=True)
class InterfaceEndpoint:
    endpoint_id: str
    object_id: str
    standard_id: str
    polarity: str
    local_position_m: tuple[float, float, float]
    local_axis: tuple[float, float, float]
    capacity: dict[str, Any]
    roles: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ObjectRole:
    object_id: str
    label: str
    builder_key: str
    architecture_id: str
    capabilities: tuple[str, ...]
    endpoint_ids: tuple[str, ...]
    root_object: bool
    portable: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SystemConnection:
    connection_id: str
    endpoint_a: str
    endpoint_b: str
    mode: str
    active_in_layout: bool
    workflow_states: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SystemWorkflow:
    workflow_id: str
    label: str
    ordered_steps: tuple[dict[str, Any], ...]
    required_objects: tuple[str, ...]
    required_connections: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TopologyCandidate:
    topology_id: str
    label: str
    capability_coverage: tuple[str, ...]
    connection_reuse: int
    orphan_risk: float
    workflow_cost: float
    transport_cost: float
    complexity: float
    score: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SystemPlan:
    brief: SystemBrief
    selected_topology: str
    topology_candidates: tuple[TopologyCandidate, ...]
    objects: tuple[ObjectRole, ...]
    standards: tuple[InterfaceStandard, ...]
    endpoints: tuple[InterfaceEndpoint, ...]
    connections: tuple[SystemConnection, ...]
    workflows: tuple[SystemWorkflow, ...]
    layout_m: dict[str, tuple[float, float, float]]
    object_yaw_degrees: dict[str, float]

    @property
    def fingerprint(self) -> str:
        payload = json.dumps(self.to_dict(include_fingerprint=False), sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
        return hashlib.sha256(payload).hexdigest()

    def to_dict(self, *, include_fingerprint: bool = True) -> dict[str, Any]:
        result = {
            "schema_version": "1.0",
            "brief": self.brief.to_dict(),
            "selected_topology": self.selected_topology,
            "topology_candidates": [item.to_dict() for item in self.topology_candidates],
            "objects": [item.to_dict() for item in self.objects],
            "standards": [item.to_dict() for item in self.standards],
            "endpoints": [item.to_dict() for item in self.endpoints],
            "connections": [item.to_dict() for item in self.connections],
            "workflows": [item.to_dict() for item in self.workflows],
            "layout_m": {key: list(value) for key, value in self.layout_m.items()},
            "object_yaw_degrees": self.object_yaw_degrees,
        }
        if include_fingerprint:
            result["fingerprint"] = self.fingerprint
        return result
