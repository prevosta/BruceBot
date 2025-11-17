from dataclasses import dataclass

from ares import AresBot
from ares.behaviors.combat.individual import CombatIndividualBehavior
from ares.managers.manager_mediator import ManagerMediator
from cython_extensions import cy_distance_to_squared
from sc2.ids.ability_id import AbilityId
from sc2.position import Point2
from sc2.unit import Unit


@dataclass
class BattleCruiserRepair(CombatIndividualBehavior):
    """Manages Yamato Cannon usage for a single BattleCruiser unit."""

    unit: Unit

    def execute(self, ai: AresBot, config: dict, mediator: ManagerMediator) -> bool:

        if self.unit.health_percentage >= 1.0 or not ai.townhalls.exists:
            return False
        
        base_location = Point2(ai.townhalls.closest_to(ai.start_location).position.towards(ai.game_info.map_center, -3))

        if cy_distance_to_squared(self.unit.position, base_location) < 10**2:
            self.unit.stop()

        # Warping out on low health
        if self.unit.health_percentage < 0.15:
            self.unit(AbilityId.EFFECT_TACTICALJUMP, base_location)

        return True
