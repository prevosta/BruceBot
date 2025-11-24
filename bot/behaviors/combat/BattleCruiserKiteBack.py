from dataclasses import dataclass

from ares import AresBot
from sc2.ids.unit_typeid import UnitTypeId
from ares.managers.manager_mediator import ManagerMediator

from sc2.unit import Unit
from sc2.position import Point2
from cython_extensions import cy_distance_to_squared
from ares.behaviors.combat.individual import CombatIndividualBehavior

@dataclass
class BattleCruiserKiteBack(CombatIndividualBehavior):
    """Manages Yamato Cannon usage for a single BattleCruiser unit."""

    unit: Unit
    safe_pos: Point2
    dps_threshold: float = 25.0

    def execute(self, ai: AresBot, config: dict, mediator: ManagerMediator) -> bool:
        """Kite back BattleCruisers when (strong) enemies are too close."""

        # Census nearby enemies that can attack air
        enemy_nearby = ai.enemy_units({UnitTypeId.MARINE, UnitTypeId.STALKER, UnitTypeId.QUEEN})
        enemy_nearby = enemy_nearby.filter(lambda e: cy_distance_to_squared(self.unit.position, e.position) < 15**2)
        enemy_nearby = enemy_nearby.filter(lambda e: e.can_attack_air)
        if not enemy_nearby.exists:
            return False

        # Check if resistance is strong
        total_dps = sum(e.calculate_dps_vs_target(self.unit) for e in enemy_nearby)
        if total_dps <= self.dps_threshold:
            return False
        print(f"BC kiting from {total_dps} DPS nearby.")

        def in_range(e: Unit, range: float) -> bool:
            real_range = self.unit.radius + e.radius + range
            return cy_distance_to_squared(e.position, self.unit.position) <= (real_range)**2
        
        # go to safe position if health is low
        if self.unit.health_percentage < 0.50:
            self.unit.move(self.safe_pos)
            return True

        # Kite back to safe position
        in_range_of = enemy_nearby.filter(lambda e: in_range(e, e.air_range + 0.5))
        if in_range_of.amount > 2:
            self.unit.move(self.safe_pos)
            return True

        # Kite foward to reduce enemy strength
        closest_enemy = enemy_nearby.closest_to(self.unit)
        range = self.unit.air_range if closest_enemy.is_flying else self.unit.ground_range
        if in_range(closest_enemy, range - 0.5):
            self.unit.move(Point2(self.unit.position.towards(closest_enemy.position, 1)))
            return True
        
        return False
