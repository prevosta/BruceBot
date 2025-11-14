from dataclasses import dataclass

from cython_extensions import cy_distance_to_squared

from sc2.position import Point2
from sc2.ids.unit_typeid import UnitTypeId

from ares import AresBot
from ares.consts import TOWNHALL_TYPES
from ares.managers.manager_mediator import ManagerMediator
from ares.behaviors.combat.group import CombatGroupBehavior
from ares.behaviors.combat.individual.path_unit_to_target import PathUnitToTarget


@dataclass
class ArmyAttack(CombatGroupBehavior):
    """Manages BattleCruisers in combat."""

    army_types: set[UnitTypeId] | UnitTypeId | None = None

    def execute(self, ai: AresBot, config: dict, mediator: ManagerMediator) -> bool:
        army = ai.units(self.army_types)

        if not army.exists:
            return False

        targets: list[Point2] = [s.position for s in ai.enemy_structures(TOWNHALL_TYPES)]

        if not getattr(ai, 'main_townhall_destroyed', False):
            targets.append(ai.enemy_start_locations[0])

            if army.filter(lambda u: cy_distance_to_squared(u.position, ai.enemy_start_locations[0]) < 10**2).exists:
                if not ai.enemy_structures(TOWNHALL_TYPES).filter(lambda u: cy_distance_to_squared(u.position, ai.enemy_start_locations[0]) < 10**2).exists:
                    setattr(ai, 'main_townhall_destroyed', True)

        if not targets:
            return False

        # Move to location
        for unit in army.idle:
            inx_target = int(ai.time) % len(targets)
            PathUnitToTarget(unit, mediator.get_air_grid, targets[inx_target]).execute(ai, config, mediator)

        return True
