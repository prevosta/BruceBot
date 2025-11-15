from dataclasses import dataclass

from cython_extensions import cy_distance_to_squared

from sc2.position import Point2
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId

from ares import AresBot
from ares.consts import TOWNHALL_TYPES
from ares.managers.manager_mediator import ManagerMediator
from ares.behaviors.combat.group import CombatGroupBehavior
from ares.behaviors.combat.individual.keep_unit_safe import KeepUnitSafe
from ares.behaviors.combat.individual.path_unit_to_target import PathUnitToTarget

@dataclass
class BattleCruiser(CombatGroupBehavior):
    """Manages BattleCruisers in combat."""

    high_threats: set[UnitTypeId] | None = None # Yamato Cannon priority
    priorities: set[UnitTypeId] | None = None # Battery Cannon priority

    def execute(self, ai: AresBot, config: dict, mediator: ManagerMediator) -> bool:
        # Yamato Cannon (Static Air Defense, Air2Air unit)
        # Priority: AntiAir(if can win), Worker, TechBuilding
        # Tatical Emergency Recall for defense

        order_issue = False

        for unit in ai.units(UnitTypeId.BATTLECRUISER):
            # Support logic
            region = mediator.get_map_data_object.where(ai.start_location)
            enemy_at_the_gate = ai.enemy_units.filter(lambda e: e.is_visible and cy_distance_to_squared(e.position, ai.main_base_ramp.bottom_center) < 10**2)
            enemy_at_the_gate |= ai.enemy_units.filter(lambda e: region.is_inside_point(e.position))
            if enemy_at_the_gate.amount > 8 and cy_distance_to_squared(unit.position, ai.main_base_ramp.top_center) > 30**2:
                unit(AbilityId.EFFECT_TACTICALJUMP, Point2(ai.main_base_ramp.top_center.towards(ai.start_location, 10)))
                order_issue = True
                continue

            # Repair logic
            if unit.health_percentage < 1.0 and ai.townhalls.exists:
                base_location = Point2(ai.townhalls.closest_to(ai.start_location).position.towards(ai.game_info.map_center, -3))

                if cy_distance_to_squared(unit.position, base_location) < 10**2:
                    unit.stop()
                    order_issue = True
                    continue

                # Warping out on low health                
                if unit.health_percentage < 0.25:
                    unit(AbilityId.EFFECT_TACTICALJUMP, base_location)
                    order_issue = True
                    continue

            # Attack logic
            targets = ai.enemy_units.filter(lambda e: e.can_attack_air and cy_distance_to_squared(e.position, unit.position) < (e.air_range + 2)**2)
            if self.high_threats:
                targets |= ai.enemy_units(self.high_threats) | ai.enemy_structures(self.high_threats)

            if not targets.exists and self.priorities:
                targets = ai.enemy_structures(self.priorities) | ai.enemy_units(self.priorities)
                targets = targets.filter(lambda e: cy_distance_to_squared(e.position, unit.position) < 15**2 and e.is_visible)

            if targets.exists:
                closest_enemy = targets.sorted(lambda x: cy_distance_to_squared(x.position, unit.position)).first
                other_enemy = targets.filter(lambda e: e.tag != closest_enemy.tag and e.can_attack_air)

                if other_enemy.exists:
                    KeepUnitSafe(unit, mediator.get_air_grid).execute(ai, config, mediator)
                    order_issue = True
                    continue

                elif cy_distance_to_squared(unit.position, closest_enemy.position) > (unit.ground_range -2) ** 2:
                    PathUnitToTarget(unit, mediator.get_air_grid, closest_enemy.position).execute(ai, config, mediator)

            # Defense logic
            elif enemy_at_the_gate.amount > 2 and cy_distance_to_squared(unit.position, ai.main_base_ramp.top_center) <= 30**2:
                target = Point2(ai.main_base_ramp.top_center.towards(ai.start_location, 2))
                PathUnitToTarget(unit, mediator.get_air_grid, target).execute(ai, config, mediator)

        return order_issue
