from dataclasses import dataclass

from sc2.units import Units
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId

from ares.consts import UnitTreeQueryType
from ares.main import AresBot
from ares.behaviors.combat.group import CombatGroupBehavior
from ares.managers.manager_mediator import ManagerMediator


@dataclass
class ControlSupplyDepot(CombatGroupBehavior):
    """ Controls the raising and lowering of Supply Depots based on nearby enemy ground units."""

    distance: float = 6.0

    def execute(self, ai: AresBot, config: dict, mediator: ManagerMediator) -> bool:
        order_issued: bool = False

        for depot in ai.structures({UnitTypeId.SUPPLYDEPOT, UnitTypeId.SUPPLYDEPOTLOWERED}).ready:
            near_enemy_ground: Units = mediator.get_units_in_range(
                start_points=[depot.position],
                distances=self.distance,
                query_tree=UnitTreeQueryType.EnemyGround,
            )[0]

            if depot.type_id == UnitTypeId.SUPPLYDEPOTLOWERED:
                if len(near_enemy_ground) > 0:
                    depot(AbilityId.MORPH_SUPPLYDEPOT_RAISE)
                    order_issued = True

            elif depot.type_id == UnitTypeId.SUPPLYDEPOT:
                if len(near_enemy_ground) == 0:
                    depot(AbilityId.MORPH_SUPPLYDEPOT_LOWER)
                    order_issued = True

        return order_issued
