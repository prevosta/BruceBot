from dataclasses import dataclass
from loguru import logger

from ares import AresBot
from ares.consts import TARGET, ID
from ares.behaviors.combat.group import CombatGroupBehavior
from ares.managers.manager_mediator import ManagerMediator
from cython_extensions import cy_distance_to_squared
from sc2.ids.unit_typeid import UnitTypeId

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
            if structure_type == UnitTypeId.BARRACKS:

                if target == ai.main_base_ramp.barracks_in_middle:
                    continue

                if any(cy_distance_to_squared(u.position, ai.main_base_ramp.barracks_in_middle) < 4 for u in ai.structures(UnitTypeId.BARRACKS)):
                    continue

                # Modify target to ramp barracks
                track = building_tracker.pop(worker_tag)
                track[TARGET] = ai.main_base_ramp.barracks_in_middle
                building_tracker[worker_tag] = track
                logger.info(f"RampModifier: {structure_type.name}")

                return True
            
            elif structure_type == UnitTypeId.SUPPLYDEPOT:

                if target in ai.main_base_ramp.corner_depots:
                    continue

                for corner_depot in ai.main_base_ramp.corner_depots:
                    if any(cy_distance_to_squared(u.position, corner_depot) < 1 for u in ai.structures({UnitTypeId.SUPPLYDEPOT, UnitTypeId.SUPPLYDEPOTLOWERED})):
                        continue

                    if target not in ai.main_base_ramp.corner_depots:
                        track = building_tracker.pop(worker_tag)
                        track[TARGET] = corner_depot
                        building_tracker[worker_tag] = track
                        logger.info(f"RampModifier: {structure_type.name}")

                        return True

        return False
