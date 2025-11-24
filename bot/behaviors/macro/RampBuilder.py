from dataclasses import dataclass
from loguru import logger

from ares import AresBot
from ares.consts import TARGET, ID, BuildingSize
from ares.dicts.structure_to_building_size import STRUCTURE_TO_BUILDING_SIZE
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

        # Inspect building tracker...
        building_tracker: dict = mediator.get_building_tracker_dict
        for worker_tag in building_tracker:

            if building_tracker[worker_tag][TARGET] is None:
                continue

            structure_type = building_tracker[worker_tag][ID]
            target: Point2 = building_tracker[worker_tag][TARGET].position

            # 1- Prioritize barracks on the ramp.
            if structure_type == UnitTypeId.BARRACKS:

                if target == ai.main_base_ramp.barracks_in_middle:
                    continue

                if any(cy_distance_to_squared(u.position, ai.main_base_ramp.barracks_in_middle) < 4 for u in ai.structures(UnitTypeId.BARRACKS)):
                    continue

                track = building_tracker.pop(worker_tag)
                track[TARGET] = ai.main_base_ramp.barracks_in_middle
                building_tracker[worker_tag] = track
                logger.info(f"RampBuilder: {structure_type.name}")

                return True

            # 2- Prioritize depots on the ramp corners.
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
                        logger.info(f"RampBuilder: {structure_type.name}")

                        return True

                # 3- Switch other depots on non static defense positions.
                group_size : BuildingSize = STRUCTURE_TO_BUILDING_SIZE[structure_type]
                pos_locations = {building_pos: base_loc for base_loc in mediator.get_placements_dict for building_pos in mediator.get_placements_dict[base_loc][group_size]}
                base_loc = pos_locations.get(target, ai.start_location)

                static_defence = mediator.get_placements_dict[base_loc][group_size][target].get('static_defence', False)
                track_target = self.request_building_placement(ai, base_location=base_loc, structure_type=structure_type)

                if static_defence and (track_target is not None):
                    track = building_tracker.pop(worker_tag)
                    track[TARGET] = track_target
                    building_tracker[worker_tag] = track
                    logger.info(f"RampBuilder: {structure_type.name}")

                    return True
                
            # 4- Prioritize turrets at static defense positions.
            elif structure_type == UnitTypeId.MISSILETURRET:

                group_size : BuildingSize = STRUCTURE_TO_BUILDING_SIZE[structure_type]
                pos_locations = {building_pos: base_loc for base_loc in mediator.get_placements_dict for building_pos in mediator.get_placements_dict[base_loc][group_size]}
                base_loc = pos_locations.get(target, ai.start_location)

                static_defence = mediator.get_placements_dict[base_loc][group_size][target].get('static_defence', False)
                if static_defence:
                    continue

                track_target = self.request_building_placement(ai, base_location=base_loc, structure_type=structure_type, static_defence=True)

                if track_target is None:
                    continue

                track = building_tracker.pop(worker_tag)
                track[TARGET] = track_target
                building_tracker[worker_tag] = track
                logger.info(f"RampBuilder: {structure_type.name}")

                return True

        return False

    def request_building_placement(self, ai: AresBot, base_location: Point2, structure_type: UnitTypeId, near: Point2 | None = None, static_defence: bool = False, is_wall: bool = False) -> Point2 | None:
        """Request a building placement from the mediator."""

        group_size : BuildingSize = STRUCTURE_TO_BUILDING_SIZE[structure_type]
        placements = ai.mediator.get_placements_dict[base_location][group_size]

        if is_wall:
            wall_positions = [pos for pos, attribs in placements.items() if attribs.get('is_wall', False) and attribs.get('available', True)]

            if near is not None:
                wall_positions = sorted(wall_positions, key=lambda p: cy_distance_to_squared(p, near))

            return wall_positions[0] if wall_positions else None

        if static_defence:
            static_defences = [pos for pos, attribs in placements.items() if attribs.get('static_defence', False) and attribs.get('available', True)]

            if near is not None:
                static_defences = sorted(static_defences, key=lambda p: cy_distance_to_squared(p, near))

            return static_defences[0] if static_defences else None

        return next((pos for pos, attribs in placements.items() if attribs.get('available', True)), None)
