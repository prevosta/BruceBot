from dataclasses import dataclass

from cython_extensions import cy_distance_to_squared

from sc2.position import Point2
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId

from ares import AresBot
from ares.behaviors.combat.group import CombatGroupBehavior


@dataclass
class TankDefence(CombatGroupBehavior):
    """Defend key locations using Marine units."""

    tank_positions: list[Point2]

    def execute(self, ai: AresBot, config: dict, mediator) -> bool:

        # Get all Marine units
        combat_units = ai.units.filter(lambda u: u.type_id == UnitTypeId.SIEGETANK)
        
        if not combat_units.exists:
            return False
        
        for unit in combat_units:
            if cy_distance_to_squared(unit.position, self.tank_positions[0]) > 2**2:
                unit.move(self.tank_positions[0])
            else:
                unit(AbilityId.SIEGEMODE_SIEGEMODE)

        return True


def generate_tank_positions(ai: AresBot) -> list[Point2]:
    """Generate tank positions around the main base ramp and climber ingress points."""

    return [Point2((ai.main_base_ramp.top_center.towards(ai.start_location, 10)))]
