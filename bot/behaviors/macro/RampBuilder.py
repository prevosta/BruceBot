from dataclasses import dataclass
from loguru import logger

from ares import AresBot
from ares.consts import TARGET, ID
from ares.behaviors.combat.group import CombatGroupBehavior
from ares.managers.manager_mediator import ManagerMediator
from cython_extensions import cy_distance_to_squared
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2

PROXYBUILDER: str = "ProxyBuilder"

@dataclass
class RampBuilder(CombatGroupBehavior):
    """Behavior to modify building placement targets to be on the main base ramp barracks position."""

    def execute(self, ai: AresBot, config: dict, mediator: ManagerMediator) -> bool:

        # Force usage of proxy workers if closer to the build location
        building_tracker: dict = mediator.get_building_tracker_dict
        for worker_tag in building_tracker:
            structure_type = building_tracker[worker_tag][ID]
            target = building_tracker[worker_tag][TARGET].position

            # Only modify barracks placements
            if structure_type != UnitTypeId.BARRACKS:
                continue

            # Skip if already targeting ramp barracks or out of range
            distance_square = cy_distance_to_squared(target, ai.main_base_ramp.barracks_in_middle)
            if not isinstance(target, Point2) or not (0.1 < distance_square < 5**2):
                continue

            # Modify target to ramp barracks
            track = building_tracker.pop(worker_tag)
            track[TARGET] = ai.main_base_ramp.barracks_in_middle
            building_tracker[worker_tag] = track
            logger.info(f"RampModifier: {structure_type.name} {distance_square:.2f} {ai.main_base_ramp.barracks_in_middle} -> {track[TARGET]}")

            return True

        return False
    