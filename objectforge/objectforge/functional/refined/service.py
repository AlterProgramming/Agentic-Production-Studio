from __future__ import annotations

import numpy as np

from objectforge.geometry import cylinder_between, rounded_box, torus_y, translation, tube_along
from objectforge.grammar.core import GrammarAssetBuilder
from objectforge.grammar.library import DetailGrammar, JoineryGrammar, SupportGrammar
from objectforge.planning.functional import FunctionalPlan
from .common import _add_knob, _add_label_plate, _add_vent_bank, _new_builder


def _support_metrics(width: float, depth: float, load_kg: float, top_height: float) -> dict[str, float | bool]:
    half = min(width, depth) / 2.0
    overturn = load_kg * 9.81 * top_height * 0.08
    resisting = (6.2 + load_kg) * 9.81 * half
    margin = resisting - overturn
    return {
        "support_half_span": round(half, 4),
        "design_load_kg": load_kg,
        "top_height_m": top_height,
        "moment_margin_nm": round(margin, 4),
        "stable": bool(half >= 0.28 and margin > 10.0),
    }


def build_four_leg_service_station(plan: FunctionalPlan) -> GrammarAssetBuilder:
    builder = _new_builder(plan, "FunctionalRoot")
    width, depth, height = 1.34, 0.80, 1.04
    positions = SupportGrammar.four_leg_frame(
        builder,
        top_size=(width, depth),
        height=height,
        leg_section=0.105,
        material="GraphitePowderCoat",
        inset=0.15,
    )

    top = rounded_box((width, 0.11, depth), radius=0.075, segments=8)
    builder.add_part(
        "ServiceSurface",
        "service_surface",
        builder.root_name,
        "surface.load",
        "WalnutVarnish",
        top,
        translation([0, height + 0.055, 0]),
        {"shape": "box", "extents": [width, 0.11, depth]},
    )
    DetailGrammar.edge_band(
        builder,
        parent=builder.root_name,
        prefix="SurfaceBand",
        size=(width, depth),
        y=height + 0.070,
        thickness=0.055,
        material="WarmAluminum",
    )
    mat = rounded_box((width - 0.25, 0.018, depth - 0.20), radius=0.055, segments=6)
    builder.add_part(
        "ReplaceableWorkMat",
        "replaceable_work_mat",
        builder.root_name,
        "surface.work_mat",
        "DarkRubber",
        mat,
        translation([0, height + 0.119, 0]),
    )
    rail = rounded_box((width - 0.16, 0.065, 0.075), radius=0.025, segments=4)
    builder.add_part(
        "AccessoryRail",
        "accessory_rail",
        builder.root_name,
        "interface.accessory_rail",
        "BrushedSteel",
        rail,
        translation([0, height + 0.18, -depth / 2 + 0.07]),
    )
    for index, x in enumerate((-0.48, -0.16, 0.16, 0.48)):
        hook_points = np.array(
            [[x, height + 0.16, -depth / 2 + 0.07], [x, height + 0.05, -depth / 2 - 0.05], [x, height - 0.03, -depth / 2 - 0.05]]
        )
        builder.add_part(
            f"AccessoryHook{index + 1}",
            f"accessory_hook_{index + 1}",
            builder.root_name,
            "interface.accessory_hook",
            "SignalOrange",
            tube_along(hook_points, radius=0.020, sections=12),
        )

    drawer_body = rounded_box((width - 0.27, 0.22, depth * 0.64), radius=0.045, segments=6)
    builder.add_part(
        "ServiceDrawerBody",
        "service_drawer_body",
        builder.root_name,
        "storage.drawer_body",
        "MoldedBlack",
        drawer_body,
        translation([0, height - 0.20, 0.03]),
    )
    drawer_front = rounded_box((width - 0.19, 0.20, 0.09), radius=0.035, segments=5)
    builder.add_part(
        "ServiceDrawerFront",
        "service_drawer_front",
        builder.root_name,
        "storage.drawer_front",
        "GraphitePowderCoat",
        drawer_front,
        translation([0, height - 0.19, depth / 2 - 0.02]),
    )
    JoineryGrammar.handle(
        builder,
        parent=builder.root_name,
        prefix="Drawer",
        center=[0, height - 0.19, depth / 2 + 0.055],
        width=0.38,
        height=0.075,
        material="DarkRubber",
    )
    for index, x in enumerate((-0.50, 0.50)):
        runner = rounded_box((0.05, 0.055, depth * 0.60), radius=0.018, segments=3)
        builder.add_part(
            f"DrawerRunner{index + 1}",
            f"drawer_runner_{index + 1}",
            builder.root_name,
            "storage.drawer_runner",
            "BrushedSteel",
            runner,
            translation([x, height - 0.23, 0]),
        )

    shelf_y = 0.38
    shelf = rounded_box((width - 0.18, 0.08, depth - 0.15), radius=0.050, segments=7)
    builder.add_part(
        "OpenStorageShelf",
        "open_storage_shelf",
        builder.root_name,
        "storage.open_shelf",
        "OakVarnish",
        shelf,
        translation([0, shelf_y, 0]),
    )
    DetailGrammar.edge_band(
        builder,
        parent=builder.root_name,
        prefix="ShelfBand",
        size=(width - 0.18, depth - 0.15),
        y=shelf_y + 0.015,
        thickness=0.042,
        material="BrushedSteel",
    )
    for index, z in enumerate((-depth * 0.31, depth * 0.31)):
        lip = rounded_box((width - 0.26, 0.13, 0.055), radius=0.020, segments=4)
        builder.add_part(
            f"ShelfRetainingLip{index + 1}",
            f"shelf_retaining_lip_{index + 1}",
            builder.root_name,
            "storage.shelf_lip",
            "GraphitePowderCoat",
            lip,
            translation([0, shelf_y + 0.085, z]),
        )

    for index, pos in enumerate(positions):
        JoineryGrammar.bracket(
            builder,
            parent=builder.root_name,
            prefix=f"LoadJoin{index + 1}",
            center=[pos[0], height - 0.14, pos[2]],
            size=(0.25, 0.13, 0.085),
            material="SignalOrange",
        )
        _add_knob(
            builder,
            parent=builder.root_name,
            prefix=f"Leveler{index + 1}",
            center=[pos[0], 0.07, pos[2]],
            radius=0.050,
            material="MoldedBlack",
        )
    brace_specs = [
        ([-width * 0.36, 0.18, -depth * 0.36], [width * 0.36, 0.65, -depth * 0.36]),
        ([width * 0.36, 0.18, -depth * 0.34], [-width * 0.36, 0.65, -depth * 0.34]),
        ([-width * 0.36, 0.18, depth * 0.36], [width * 0.36, 0.65, depth * 0.36]),
        ([width * 0.36, 0.18, depth * 0.34], [-width * 0.36, 0.65, depth * 0.34]),
    ]
    for index, (start, end) in enumerate(brace_specs):
        builder.add_part(
            f"CrossBrace{index + 1}",
            f"cross_brace_{index + 1}",
            builder.root_name,
            "support.cross_brace",
            "BrushedSteel",
            cylinder_between(start, end, 0.027, sections=22),
        )
    for index, x in enumerate((-0.32, 0.32)):
        grommet = torus_y(0.075, 0.025, 48, 10)
        builder.add_part(
            f"CableGrommet{index + 1}",
            f"cable_grommet_{index + 1}",
            builder.root_name,
            "interface.cable_grommet",
            "DarkRubber",
            grommet,
            translation([x, height + 0.12, 0.20]),
        )
    cable_tray = rounded_box((0.78, 0.10, 0.22), radius=0.035, segments=4)
    builder.add_part(
        "CableTray",
        "cable_tray",
        builder.root_name,
        "interface.cable_tray",
        "MoldedBlack",
        cable_tray,
        translation([0, height - 0.38, -depth / 2 + 0.08]),
    )
    _add_vent_bank(
        builder,
        parent=builder.root_name,
        prefix="CableTrayVent",
        center=[0, height - 0.38, -depth / 2 - 0.04],
        count=7,
        spacing=0.09,
        size=(0.045, 0.055, 0.025),
    )
    _add_label_plate(
        builder,
        parent=builder.root_name,
        prefix="StationRating",
        center=[0, height - 0.10, depth / 2 + 0.055],
        size=(0.36, 0.030, 0.12),
    )

    bad = _support_metrics(0.42, 0.36, 12, height)
    wider = _support_metrics(width, depth, 12, height)
    pedestal_alt = _support_metrics(0.68, 0.68, 12, height)
    rejected = builder.op(
        "planner.try_alternative",
        "load_path",
        "Test a minimum-footprint support layout against the declared working load.",
        {"alternative": "narrow_four_contact", "width": 0.42, "depth": 0.36},
        status="rejected",
        before=wider,
        after=bad,
    )
    builder.op(
        "planner.compare_repairs",
        "load_path",
        "Compare widening the four-contact frame with switching to a pedestal load path.",
        {
            "alternatives": [
                {"repair": "widen_four_contact_frame", "metrics": wider, "open_storage_preserved": True},
                {"repair": "switch_to_pedestal", "metrics": pedestal_alt, "open_storage_preserved": False},
            ],
            "selected": "widen_four_contact_frame",
        },
        recovery_of=rejected,
    )
    builder.op(
        "rollback",
        "checkpoint.load_path",
        "Restore the open-storage frame and accepted support footprint.",
        {"preserved_prior_state": True},
        recovery_of=rejected,
    )
    builder.recovery = {
        "status": "recovered",
        "forced_failure": {"operation": rejected, "finding": "insufficient support footprint", "metrics": bad},
        "alternative_comparison": [
            {"repair": "widen_four_contact_frame", "metrics": wider, "accepted": True},
            {"repair": "switch_to_pedestal", "metrics": pedestal_alt, "accepted": False},
        ],
        "rollback": {"preserved_prior_state": True, "replacement_metrics": wider},
        "source_overwritten": False,
    }
    builder.interaction = {
        "drag_targets": [],
        "contact_surface": "surface.load",
        "open_storage": "storage.open_shelf",
        "drawer": "ServiceDrawerFront",
        "accessory_rail": "AccessoryRail",
        "design_load_kg": 12,
    }
    builder.op(
        "refinement.verify_close_inspection",
        "four_leg_service_station",
        "Verify drawer construction, accessory rail, cross-bracing, leveling controls, cable tray, shelf retention, joinery and underside completion.",
        {"detail_groups": ["drawer", "accessory_rail", "cross_braces", "levelers", "cable_tray", "shelf_lips"]},
    )
    builder.op(
        "functional.verify",
        "elevated_service",
        "Verify load support, standing-height surface, open storage, footprint, and cable routing.",
        {"covered_requirements": [item.requirement_id for item in plan.brief.requirements], "support": wider},
    )
    return builder
