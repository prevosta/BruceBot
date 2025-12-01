from dataclasses import dataclass

from ares.behaviors.combat.group import CombatGroupBehavior
from ares.consts import UnitTreeQueryType
from ares.main import AresBot
from ares.managers.manager_mediator import ManagerMediator
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.units import Units


@dataclass
class ControlSupplyDepot(CombatGroupBehavior):
    """ Controls the raising and lowering of Supply Depots based on nearby enemy ground units."""

    distance: float = 6.0

    def execute(self, ai: AresBot, config: dict, mediator: ManagerMediator) -> bool:
        order_issued: bool = False

        for depot in ai.structures({UnitTypeId.SUPPLYDEPOT, UnitTypeId.SUPPLYDEPOTLOWERED}).ready:
            near_enemy_ground_raise: Units = mediator.get_units_in_range(
                start_points=[depot.position],
                distances=self.distance,
                query_tree=UnitTreeQueryType.EnemyGround,
            )[0]

            near_enemy_ground_lower: Units = mediator.get_units_in_range(
                start_points=[depot.position],
                distances=self.distance + 1,
                query_tree=UnitTreeQueryType.EnemyGround,
            )[0]

            if depot.type_id == UnitTypeId.SUPPLYDEPOTLOWERED:
                if len(near_enemy_ground_raise) > 0:
                    depot(AbilityId.MORPH_SUPPLYDEPOT_RAISE)
                    order_issued = True

            elif depot.type_id == UnitTypeId.SUPPLYDEPOT:
                if len(near_enemy_ground_lower) == 0:
                    depot(AbilityId.MORPH_SUPPLYDEPOT_LOWER)
                    order_issued = True

        return order_issued
