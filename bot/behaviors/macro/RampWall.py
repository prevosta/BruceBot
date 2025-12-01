from dataclasses import dataclass
from loguru import logger

from ares import AresBot
from ares.consts import BuildingSize
from ares.behaviors.combat.group import CombatGroupBehavior
from ares.managers.manager_mediator import ManagerMediator
from cython_extensions import cy_distance_to_squared
from sc2.ids.unit_typeid import UnitTypeId

from sc2.position import Point2

RAMPWALL: str = "RampWall"
BARRACK_CENTER: str = "BARRACKCENTER"
THREE_DEPOT: str = "THREEDEPOT"
PLACEMENT: dict = {'available': True, 'has_addon': False, 'is_wall': True, 'building_tag': 0, 'worker_on_route': False, 'time_requested': 0.0, 'production_pylon': False, 'bunker': False, 'optimal_pylon': False, 'first_pylon': False, 'static_defence': False}

@dataclass
class RampWall(CombatGroupBehavior):
    """Behavior to set up a ramp wall at the start of the game based on the chosen build order."""

    def execute(self, ai: AresBot, config: dict, mediator: ManagerMediator) -> bool:
        wall_type: str = config.get("Builds", {}).get(ai.build_order_runner.chosen_opening, {}).get(RAMPWALL, None)

        if ai.actual_iteration == 1:
            if wall_type.upper() == BARRACK_CENTER:
                self._barrack_center_ramp_wall(ai, mediator)
                logger.info("RampWall: BarrackCenter")
                return True 

            elif wall_type.upper() == THREE_DEPOT:
                self._three_depot_ramp_wall(ai, mediator)
                logger.info("RampWall: ThreeDepot")
                return True

        return False

    def _barrack_center_ramp_wall(self, ai: AresBot, mediator: ManagerMediator) -> None:
        """Place the barracks in the center of the ramp wall."""

        base_loc = ai.start_location
        grp_size = BuildingSize.THREE_BY_THREE

        # Remove the previous placement to avoid conflicts
        previous_placement = ai.main_base_ramp.barracks_correct_placement
        placement = mediator.get_placements_dict[base_loc][grp_size][previous_placement]
        del mediator.get_placements_dict[base_loc][grp_size][previous_placement]

        # Place the barracks in the middle of the ramp
        new_placement = ai.main_base_ramp.barracks_in_middle
        mediator.get_placements_dict[base_loc][grp_size][new_placement] = placement

    def _three_depot_ramp_wall(self, ai: AresBot, mediator: ManagerMediator) -> None:
        """Place three supply depots to form a wall at the ramp."""

        base_loc = ai.start_location
    
        possible_placements = []
        around_corners = [(x, y) for x in range(-2, 3) for y in range(-2, 3) if x in (-2, 2) or y in (-2, 2)]
        for corner_depot in ai.main_base_ramp.corner_depots:
            for x, y in around_corners:
                pos = Point2((x, y)) + corner_depot
                if mediator.can_place_structure(position=pos, structure_type=UnitTypeId.SUPPLYDEPOT):
                    possible_placements.append(pos)

        if not possible_placements:
            return

        building_pos = ai.main_base_ramp.barracks_in_middle
        possible_placements = [pos for pos in possible_placements if possible_placements.count(pos) > 1]
        possible_placements = sorted(possible_placements, key=lambda p: sum(cy_distance_to_squared(p, c) for c in ai.main_base_ramp.corner_depots))
       
        # Remove the previous placement to avoid conflicts
        base_loc = ai.start_location
        grp_size = BuildingSize.THREE_BY_THREE
        building_pos = ai.main_base_ramp.barracks_correct_placement
        del mediator.get_placements_dict[base_loc][grp_size][building_pos]

        # Place the third depot at the best placement
        grp_size = BuildingSize.TWO_BY_TWO
        building_pos = possible_placements[0]
        mediator.get_placements_dict[base_loc][grp_size][building_pos] = PLACEMENT

