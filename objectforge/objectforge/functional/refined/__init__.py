from __future__ import annotations

from typing import Callable

from objectforge.grammar.core import GrammarAssetBuilder
from objectforge.planning.functional import FunctionalPlan
from .emitter import build_articulated_emitter
from .protective import build_hinged_protective_shell
from .service import build_four_leg_service_station
from .organizer import build_portable_slot_organizer

_BUILDERS: dict[str, Callable[[FunctionalPlan], GrammarAssetBuilder]] = {
    "articulated_emitter": build_articulated_emitter,
    "hinged_protective_shell": build_hinged_protective_shell,
    "four_leg_service_station": build_four_leg_service_station,
    "portable_slot_organizer": build_portable_slot_organizer,
}


def build_functional_architecture(plan: FunctionalPlan) -> GrammarAssetBuilder:
    try:
        return _BUILDERS[plan.selected_architecture.builder_key](plan)
    except KeyError as exc:
        raise ValueError(
            f"selected architecture is not implemented in Scope 2 revision 2: {plan.selected_architecture.builder_key}"
        ) from exc
