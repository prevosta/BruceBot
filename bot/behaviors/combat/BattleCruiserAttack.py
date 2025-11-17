from dataclasses import dataclass

from ares import AresBot
from ares.behaviors.combat.individual import CombatIndividualBehavior
from ares.behaviors.combat.individual.keep_unit_safe import KeepUnitSafe
from ares.managers.manager_mediator import ManagerMediator
from cython_extensions import cy_distance_to_squared
from sc2.ids.unit_typeid import UnitTypeId
from sc2.unit import Unit


@dataclass
class BattleCruiserAttack(CombatIndividualBehavior):
    """Manages Yamato Cannon usage for a single BattleCruiser unit."""

    unit: Unit
    priorities: set[UnitTypeId] | None = None
    high_threats: set[UnitTypeId] | None = None

    def execute(self, ai: AresBot, config: dict, mediator: ManagerMediator) -> bool:
        # targets = ai.enemy_units.filter(lambda e: e.can_attack_air)
        # targets = targets.filter(lambda e: cy_distance_to_squared(e.position, self.unit.position) < (e.air_range + 2)**2)
        # if self.high_threats:
        #     targets |= ai.enemy_units(self.high_threats) | ai.enemy_structures(self.high_threats)
        # targets = targets.filter(lambda e: e.is_visible)

        # if not targets.exists and self.priorities:
        if self.priorities:
            targets = ai.enemy_structures(self.priorities) | ai.enemy_units(self.priorities)
            targets = targets.filter(lambda e: cy_distance_to_squared(e.position, self.unit.position) < 15**2)

        if not targets.exists:
            return False

        closest_enemy = targets.sorted(lambda x: (x.health, cy_distance_to_squared(x.position, self.unit.position))).first
        other_enemy = targets.filter(lambda e: e.tag != closest_enemy.tag and e.can_attack_air)
        other_enemy = other_enemy.sorted(lambda e: cy_distance_to_squared(e.position, self.unit.position) < e.air_range**2)

        if other_enemy.amount > 4:
            return False

        if other_enemy.exists:
            KeepUnitSafe(self.unit, mediator.get_air_grid).execute(ai, config, mediator)

        if cy_distance_to_squared(self.unit.position, closest_enemy.position) > (self.unit.ground_range -2) ** 2:
            self.unit.attack(closest_enemy)

        return True
