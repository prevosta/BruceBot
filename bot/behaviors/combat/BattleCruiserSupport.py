from dataclasses import dataclass

from ares import AresBot
from ares.behaviors.combat.individual import CombatIndividualBehavior
from ares.managers.manager_mediator import ManagerMediator
from cython_extensions import cy_distance_to_squared
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.unit import Unit


@dataclass
class BattleCruiserSupport(CombatIndividualBehavior):
    """Manages BattleCruiser support behavior to assist ramp defenses."""

    unit: Unit

    def execute(self, ai: AresBot, config: dict, mediator: ManagerMediator) -> bool:

        region = mediator.get_map_data_object.where(ai.start_location)

        enemy_nearby = ai.enemy_units.filter(lambda e: e.is_visible and e.can_attack_ground)
        enemy_nearby = enemy_nearby.filter(lambda e: region.is_inside_point(e.position))
        enemy_in_base = enemy_nearby.filter(lambda e: cy_distance_to_squared(e.position, ai.main_base_ramp.top_center) > 3**2)
        enemy_at_ramp = enemy_nearby.filter(lambda e: cy_distance_to_squared(e.position, ai.main_base_ramp.bottom_center) <= 6**2)

        if not enemy_nearby.exists and not enemy_at_ramp.exists:
            return False

        ramp_structures = ai.structures({UnitTypeId.SUPPLYDEPOT, UnitTypeId.SUPPLYDEPOTLOWERED, UnitTypeId.BARRACKS})
        ramp_structures = ramp_structures.filter(lambda d: cy_distance_to_squared(d.position, ai.main_base_ramp.top_center) < 5)
        is_ramp_falling = any(u.health_percentage < 0.1 for u in ramp_structures)
        is_ship_nearby = cy_distance_to_squared(self.unit.position, ai.main_base_ramp.top_center) < 20**2

        if (enemy_in_base.amount > 3 or is_ramp_falling) and not is_ship_nearby:
            if AbilityId.EFFECT_TACTICALJUMP in self.unit.abilities:
                self.unit(AbilityId.EFFECT_TACTICALJUMP, Point2(ai.main_base_ramp.top_center.towards(ai.start_location, 10)))
                return True

        if not is_ship_nearby:
            return False

        if enemy_in_base.exists:
            self.unit.attack(enemy_in_base.sorted(lambda x: cy_distance_to_squared(x.position, self.unit.position)).first)
            return True
        
        if enemy_at_ramp.exists:
            self.unit.attack(enemy_at_ramp.sorted(lambda x: cy_distance_to_squared(x.position, self.unit.position)).first)
            return True

        return False
