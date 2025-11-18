from dataclasses import dataclass

from ares import AresBot
from ares.behaviors.combat.individual import CombatIndividualBehavior
from ares.managers.manager_mediator import ManagerMediator
from sc2.ids.ability_id import AbilityId
from cython_extensions import cy_distance_to_squared
from sc2.position import Point2
from sc2.ids.unit_typeid import UnitTypeId
from sc2.unit import Unit


@dataclass
class BattleCruiserRepair(CombatIndividualBehavior):
    """Manages Yamato Cannon usage for a single BattleCruiser unit."""

    unit: Unit

    def execute(self, ai: AresBot, config: dict, mediator: ManagerMediator) -> bool:

        # Only repair if not at full health
        if self.unit.health_percentage >= 1.0:
            return False

        # Move towards close-by repair workers
        if repair_workers := ai.units(UnitTypeId.SCV).closer_than(10.1, self.unit).filter(lambda u: not u.is_constructing_scv):
            closest_worker = repair_workers.closest_to(self.unit)
            if cy_distance_to_squared(self.unit.position, closest_worker.position) > self.unit.radius**2:
                self.unit.move(closest_worker.position)
            else:
                self.unit.stop()
            return True

        # Retreat to safe location if very low health
        if self.unit.health_percentage >= 0.25:
            return False
        
        # Determine safe location (closest townhall or start location)
        safe_location = ai.start_location
        if ai.townhalls.exists:
            safe_location = Point2(ai.townhalls.closest_to(self.unit).position.towards(ai.game_info.map_center, -3))

        # Warp to safe location if possible
        if AbilityId.EFFECT_TACTICALJUMP in self.unit.abilities:
            self.unit(AbilityId.EFFECT_TACTICALJUMP, safe_location)
            return True
        
        # Fly to safe location
        self.unit.move(safe_location)
        return True
