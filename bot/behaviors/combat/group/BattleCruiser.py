from dataclasses import dataclass

from cython_extensions import cy_distance_to_squared

from sc2.position import Point2
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId

from ares import AresBot
from ares.consts import UnitRole
from ares.managers.manager_mediator import ManagerMediator
from ares.behaviors.combat.group import CombatGroupBehavior


@dataclass
class BattleCruiser(CombatGroupBehavior):
    """Manages BattleCruisers in combat."""

    priority: set[UnitTypeId]

    def execute(self, ai: AresBot, config: dict, mediator: ManagerMediator) -> bool:
        # WarpBack repair
        # Yamato Cannon (Static Air Defense, Air2Air unit)
        # Priority: AntiAir(if can win), Worker, TechBuilding
        # Assign to mineral line
        # Tatical Emergency Recall for defense

        for unit in ai.units(UnitTypeId.BATTLECRUISER):
            if ai.townhalls.exists:
                base_location = Point2(ai.townhalls.closest_to(ai.start_location).position.towards(ai.game_info.map_center, -3))

                if cy_distance_to_squared(unit.position, base_location) < 10**2 and unit.health_percentage < 1.0:
                    repair_crew = mediator.get_units_from_role(role=UnitRole.REPAIRING)
                    my_repair_crew = repair_crew.filter(lambda u: u.orders and u.orders[0].target == unit.tag)

                    if my_repair_crew.amount < 2:
                        if worker := mediator.select_worker(target_position=unit.position):
                            mediator.clear_role(tag=worker.tag)
                            mediator.assign_role(tag=worker.tag, role=UnitRole.REPAIRING)
                            mediator.remove_worker_from_mineral(worker_tag=worker.tag)

                    for worker in repair_crew.filter(lambda u: not u.is_repairing):
                        worker.repair(unit)

                    return True

                # If health is low, recall to base
                if unit.health_percentage < 0.2:
                    unit(AbilityId.EFFECT_TACTICALJUMP, base_location)
                    return True

            # Patrol between enemy start location and natural
            p1 = Point2(ai.enemy_start_locations[0].towards(mediator.get_enemy_ramp.top_center, 1))
            p2 = Point2(mediator.get_enemy_nat.towards(ai.game_info.map_center, 1))

            if unit.orders and isinstance(unit.orders[0].target, Point2) and cy_distance_to_squared(unit.orders[0].target, p1) < 1:
                if cy_distance_to_squared(unit.position, p1) < 1**2:
                    unit.move(p2)
            elif unit.orders and isinstance(unit.orders[0].target, Point2) and cy_distance_to_squared(unit.orders[0].target, p2) < 1:
                if cy_distance_to_squared(unit.position, p2) < 1**2:
                    unit.move(p1)
            else:
                unit.move(p1)

            damaged = ai.units.filter(lambda u: u.health_percentage < 1.0)
            for worker in mediator.get_units_from_role(role=UnitRole.REPAIRING):
                if worker.is_idle and not damaged.exists:
                    mediator.clear_role(tag=worker.tag)
                    mediator.assign_role(tag=worker.tag, role=UnitRole.GATHERING)

        return False
