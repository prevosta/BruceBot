from dataclasses import dataclass

from ares import AresBot
from ares.behaviors.combat.individual import CombatIndividualBehavior
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

        # Find targets to attack
        real_range = self.unit.ground_range + self.unit.radius
        targets = ai.enemy_units(self.priorities).filter(lambda e: cy_distance_to_squared(e.position, self.unit.position) < real_range**2)
        if not targets.exists:
            return False

        # Attack or move towards closest target
        target = targets.closest_to(self.unit)
        if cy_distance_to_squared(self.unit.position, target.position) <= (self.unit.ground_range - 1)**2:
            self.unit.attack(target)
    
        else:
            self.unit.move(target)

        return True
