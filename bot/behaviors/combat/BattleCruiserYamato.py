from dataclasses import dataclass

from ares import AresBot
from ares.behaviors.combat.individual import CombatIndividualBehavior
from ares.behaviors.combat.individual.keep_unit_safe import KeepUnitSafe
from ares.behaviors.combat.individual.path_unit_to_target import PathUnitToTarget
from ares.managers.manager_mediator import ManagerMediator
from cython_extensions import cy_distance_to_squared
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.unit import Unit


@dataclass
class BattleCruiserYamato(CombatIndividualBehavior):
    """Manages Yamato Cannon usage for a single BattleCruiser unit."""

    unit: Unit
    priorities: set[UnitTypeId] | None = None

    def execute(self, ai: AresBot, config: dict, mediator: ManagerMediator) -> bool:
        if AbilityId.YAMATO_YAMATOGUN not in self.unit.abilities:
            return False

        postion = self.unit.position
        sight_range = self.unit.sight_range + 2

        targets = ai.enemy_units(self.priorities) | ai.enemy_structures(self.priorities)
        targets = targets.filter(lambda e: e.is_visible and cy_distance_to_squared(e.position, postion) < sight_range**2)

        if not targets.exists:
            return False
        
        def yamato_priority(e):
            # Prioritize targets (Structure > CanAttackAir > Health+Shield)
            return e.is_structure, e.can_attack_air, e.health + e.shield

        target = targets.sorted(key=yamato_priority).first
        self.unit(AbilityId.YAMATO_YAMATOGUN, target)

        return True
