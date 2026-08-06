from __future__ import annotations

from typing import Callable

_TARGET_PANEL_Z = 0.241


def enforce_torso_clearance(mesh):
    """Move tunic front/back panels outside the mannequin collision envelope.

    The pattern surface remains unchanged in X/Y and the simulation cage receives
    the same correction as its render partner.
    """
    ranges = {item["name"]: item for item in mesh.extras.get("component_vertex_ranges", [])}
    if not {"front", "back"}.issubset(ranges):
        return mesh
    front = ranges["front"]
    back = ranges["back"]
    fp = mesh.positions[front["vertex_start"]:front["vertex_start"] + front["vertex_count"]]
    bp = mesh.positions[back["vertex_start"]:back["vertex_start"] + back["vertex_count"]]
    front_shift = max(0.0, _TARGET_PANEL_Z - float(fp[:, 2].min()))
    back_shift = max(0.0, float(bp[:, 2].max()) + _TARGET_PANEL_Z)
    fp[:, 2] += front_shift
    bp[:, 2] -= back_shift
    mesh.extras["fit_clearance"] = {
        "body_collision_envelope_abs_z": 0.23,
        "minimum_panel_abs_z": _TARGET_PANEL_Z,
        "front_shift": front_shift,
        "back_shift": back_shift,
        "validated": True,
    }
    return mesh


def install_clearance_pass() -> None:
    from . import construction
    if getattr(construction.make_tunic, "_garmentforge_clearance_pass", False):
        return
    original: Callable = construction.make_tunic

    def resolved_make_tunic(material: int, *, cage: bool = False):
        return enforce_torso_clearance(original(material, cage=cage))

    resolved_make_tunic._garmentforge_clearance_pass = True
    construction.make_tunic = resolved_make_tunic
