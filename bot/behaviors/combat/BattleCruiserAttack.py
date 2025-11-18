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
        def in_range(e: Unit, offset: float = 0.0) -> bool:
            return cy_distance_to_squared(e.position, self.unit.position) <= (self.unit.radius + e.radius + e.air_range + offset)**2
        
        # Check for high threat enemies nearby
        high_threats = ai.enemy_units(self.high_threats) | ai.enemy_structures(self.high_threats)
        high_threats = high_threats.filter(lambda e:  cy_distance_to_squared(e.position, self.unit.position) < 25**2)
        if high_threats.exists:
            return False

        # Check for total DPS nearby
        enemy_nearby = ai.enemy_units.filter(lambda e: e.can_attack_air and in_range(e, 1))
        total_dps = sum(e.calculate_dps_vs_target(self.unit) for e in enemy_nearby)
        if total_dps > 25:
            return False

        # Find targets to attack
        targets = ai.enemy_units(self.priorities).filter(lambda e: cy_distance_to_squared(e.position, self.unit.position) < 15**2)
        if not targets.exists:
            return False

        # Attack or move towards closest target
        target = targets.closest_to(self.unit)
        if cy_distance_to_squared(self.unit.position, target.position) <= (self.unit.ground_range - 1)**2:
            self.unit.attack(target)
        else:
            self.unit.move(target)
        return True
