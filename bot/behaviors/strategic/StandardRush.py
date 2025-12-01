from dataclasses import dataclass

from ares import AresBot
from ares.consts import WORKER_TYPES, UnitRole
from ares.behaviors.combat.group import CombatGroupBehavior
from ares.managers.manager_mediator import ManagerMediator
from ares.behaviors.combat.individual.keep_unit_safe import KeepUnitSafe
from cython_extensions import cy_attack_ready, cy_distance_to_squared
from sc2.ids.unit_typeid import UnitTypeId
from sc2.unit import Unit


@dataclass
class StandardRush(CombatGroupBehavior):
    """Behavior to aggressively rush the enemy base with all available army units."""

    def execute(self, ai: AresBot, config: dict, mediator: ManagerMediator) -> bool:
        army_units = ai.units.exclude_type(WORKER_TYPES | {UnitTypeId.MULE}).ready
        if ai.build_order_runner.build_completed:
            army_units |= mediator.get_units_from_role(role=UnitRole.PROXY_WORKER).filter(lambda u: not u.is_constructing_scv)
        region = mediator.get_map_data_object.where(ai.enemy_start_locations[0])
        rally_point = ai.enemy_start_locations[0] if any(ai.units.filter(lambda u: region.is_inside_point(u.position))) else mediator.get_enemy_ramp.top_center

        for unit in army_units:
            target = self._get_attack_target(ai, unit)
            
            if target and cy_attack_ready(ai, unit, target):
                unit.attack(target)

            elif self._is_under_attack(ai, unit, 2.0):
                KeepUnitSafe(unit, grid=mediator.get_ground_grid).execute(ai, config, mediator)

            elif not unit.is_moving:
                unit.move(rally_point)

        return True

    def _get_attack_target(self, ai: AresBot, unit: Unit) -> Unit | None:
        """Get the best target for this unit to attack."""

        # Priority 1: Enemies in attack range
        structure_in_range = ai.enemy_units.visible.filter(
            lambda e: cy_distance_to_squared(e.position, unit.position) 
            < max(3, e.radius + unit.radius + unit.ground_range) ** 2 and
            e.type_id not in {UnitTypeId.LARVA, UnitTypeId.EGG}
        )
        if structure_in_range.exists:
            return structure_in_range.sorted(key=lambda u: u.health + u.shield)[0]

        # Priority 2: Enemies in sight range
        enemy_in_sight = ai.enemy_units.visible.filter(
            lambda e: cy_distance_to_squared(e.position, unit.position) 
            < max(3, e.radius + unit.radius + unit.sight_range) ** 2 and
            e.type_id not in {UnitTypeId.LARVA, UnitTypeId.EGG} and
            ai.mediator.find_raw_path(start=unit.position, target=e.position, grid=ai.mediator.get_ground_grid, sensitivity=5) is not None
        )
        if enemy_in_sight.exists:
            return enemy_in_sight.sorted(
                key=lambda u: cy_distance_to_squared(u.position, unit.position)
            )[0]
        
        # Priority 3: Enemy ramp structures
        ramp_blocked = ai.mediator.find_raw_path(start=ai.mediator.get_enemy_third, target=ai.enemy_start_locations[0], grid=ai.mediator.get_ground_grid, sensitivity=1) is None
        structure_in_range = structure_in_range | ai.enemy_structures({UnitTypeId.SUPPLYDEPOT, UnitTypeId.SUPPLYDEPOTLOWERED, UnitTypeId.PYLON}).closer_than(4, ai.mediator.get_enemy_ramp.top_center)
        if structure_in_range.exists and ramp_blocked:
            return structure_in_range.sorted(key=lambda u: u.health + u.shield)[0]

        # Priority 4: Enemy spawn townhall
        structure_in_range = ai.enemy_structures.closer_than(3, ai.enemy_start_locations[0])
        structure_in_range = structure_in_range | ai.enemy_structures({UnitTypeId.BUNKER, UnitTypeId.PHOTONCANNON, UnitTypeId.SPINECRAWLER}).closer_than(5, ai.enemy_start_locations[0])
        if structure_in_range.exists:
            return structure_in_range.sorted(key=lambda u: u.health + u.shield)[0]

        return None

    def _is_under_attack(self, ai: AresBot, unit: Unit, buffer: float = 1.0) -> bool:
        """Check if enemies are attacking this unit."""
        in_range_of = ai.enemy_units.visible.filter(
            lambda e: cy_distance_to_squared(e.position, unit.position) 
            < (e.radius + unit.radius + (e.air_range if unit.is_flying else e.ground_range) + buffer) ** 2
        )
        return in_range_of.exists
