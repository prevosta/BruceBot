from dataclasses import dataclass

from cython_extensions import cy_distance_to_squared

from sc2.position import Point2
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId

from ares import AresBot
from ares.consts import UnitRole
from ares.managers.manager_mediator import ManagerMediator
from ares.behaviors.combat.group import CombatGroupBehavior
from ares.behaviors.combat.individual.path_unit_to_target import PathUnitToTarget

@dataclass
class BattleCruiser(CombatGroupBehavior):
    """Manages BattleCruisers in combat."""

    priority: set[UnitTypeId]

    def execute(self, ai: AresBot, config: dict, mediator: ManagerMediator) -> bool:
        # Yamato Cannon (Static Air Defense, Air2Air unit)
        # Priority: AntiAir(if can win), Worker, TechBuilding
        # Assign to mineral line
        # Tatical Emergency Recall for defense

        for unit in ai.units(UnitTypeId.BATTLECRUISER):
            # Repair logic
            if ai.townhalls.exists:
                base_location = Point2(ai.townhalls.closest_to(ai.start_location).position.towards(ai.game_info.map_center, -3))

                if cy_distance_to_squared(unit.position, base_location) < 10**2 and unit.health_percentage < 1.0:
                    repair_crew = mediator.get_units_from_role(role=UnitRole.REPAIRING)
                    my_repair_crew = repair_crew.filter(lambda u: u.orders and isinstance(u.orders[0].target, Point2) and cy_distance_to_squared(u.orders[0].target, unit.position) < 1)

                    if my_repair_crew.amount < 2:
                        if worker := mediator.select_worker(target_position=unit.position):
                            mediator.clear_role(tag=worker.tag)
                            mediator.assign_role(tag=worker.tag, role=UnitRole.REPAIRING)
                            mediator.remove_worker_from_mineral(worker_tag=worker.tag)

                    for worker in repair_crew.filter(lambda u: not u.is_repairing):
                        worker.repair(unit)

                    unit.stop()

                    return True

                # Warping out if low health
                if unit.health_percentage < 0.2:
                    unit(AbilityId.EFFECT_TACTICALJUMP, base_location)
                    return True

            # Patrol logic
            if not unit.is_moving:
                p1 = Point2(ai.enemy_start_locations[0].towards(mediator.get_enemy_ramp.top_center, -2))
                p2 = Point2(mediator.get_enemy_nat.towards(ai.game_info.map_center, -2))

                if int(ai.time / 60) % 2 == 0:
                    PathUnitToTarget(unit, mediator.get_air_grid, p1).execute(ai, config, mediator)
                else:
                    PathUnitToTarget(unit, mediator.get_air_grid, p2).execute(ai, config, mediator)

        # Repair crew management
        damaged = ai.units.filter(lambda u: u.health_percentage < 1.0)
        for worker in mediator.get_units_from_role(role=UnitRole.REPAIRING):
            if (worker.is_idle and not damaged.exists) or (ai.minerals < 10 or ai.vespene < 10):
                mediator.clear_role(tag=worker.tag)
                mediator.assign_role(tag=worker.tag, role=UnitRole.GATHERING)

        return False
