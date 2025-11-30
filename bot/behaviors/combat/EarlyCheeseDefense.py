from dataclasses import dataclass

from ares import AresBot
from ares.behaviors.combat.group import CombatGroupBehavior
from ares.behaviors.macro.build_structure import BuildStructure
from ares.consts import UnitRole, WORKER_TYPES
from ares.managers.manager_mediator import ManagerMediator
from cython_extensions import cy_distance_to_squared
from sc2.ids.unit_typeid import UnitTypeId
from sc2.unit import Unit


@dataclass
class EarlyCheeseDefense(CombatGroupBehavior):
    """Behavior to defend against early cheese attacks."""

    timeout: int = int(2.25 * 60)  # 2.25 minutes
    crew_size: int = 3
    cap_size: int = 9

    def execute(self, ai: AresBot, config: dict, mediator: ManagerMediator) -> bool:
        # Check timeout and existing defending workers
        worker_army = mediator.get_units_from_role(role=UnitRole.DEFENDING, unit_type=UnitTypeId.SCV)
        if ai.time > self.timeout and not worker_army.exists:
            return False

        # Return unneeded units to mining
        for worker in mediator.get_units_from_role(role=UnitRole.DEFENDING, unit_type=UnitTypeId.SCV):
            if not worker.is_attacking:
                mediator.clear_role(tag=worker.tag)
                mediator.assign_role(tag=worker.tag, role=UnitRole.GATHERING)
                worker.stop()

        # Identify enemy proxy structures
        region = mediator.get_map_data_object.where(ai.start_location)
        proxy_structures = ai.enemy_structures.filter(lambda u: region.is_inside_point(u.position) and cy_distance_to_squared(u.position, ai.main_base_ramp.bottom_center) > 6**2)
        if not proxy_structures.exists:
            return False

        # Construct ramp wall defenses if not already present
        for loc in ai.main_base_ramp.corner_depots:
            if not ai.structures({UnitTypeId.SUPPLYDEPOT, UnitTypeId.SUPPLYDEPOTLOWERED}).filter(lambda s: cy_distance_to_squared(s.position, loc) < 1**2).exists:
                BuildStructure(loc, UnitTypeId.SUPPLYDEPOT).execute(ai, config, mediator)
        loc = ai.main_base_ramp.barracks_in_middle
        if loc and not ai.structures(UnitTypeId.BARRACKS).filter(lambda s: cy_distance_to_squared(s.position, loc) < 3**2).exists:
            BuildStructure(loc, UnitTypeId.BARRACKS).execute(ai, config, mediator)

        # Build marines
        for barracks in ai.structures(UnitTypeId.BARRACKS).ready.idle:
            if ai.can_afford(UnitTypeId.MARINE) and ai.supply_left > 0 and ai.workers.exists:
                barracks.train(UnitTypeId.MARINE)
        for townhall in ai.townhalls.ready.idle:
            if ai.can_afford(UnitTypeId.SCV) and ai.supply_left > 0:
                townhall.train(UnitTypeId.SCV)

        # Marine attack worker
        for unit in ai.units(UnitTypeId.MARINE).idle:
            if ai.enemy_units(WORKER_TYPES).exists:
                target = ai.enemy_units(WORKER_TYPES).closest_to(unit)
                unit.attack(target)
            else:
                target = proxy_structures.closest_to(unit)
                unit.attack(target)

        # Get defending workers and unassigned workers
        worker_army = mediator.get_units_from_role(role=UnitRole.DEFENDING, unit_type=UnitTypeId.SCV)
        unassigned_units = [unit for unit in worker_army if self.target_tag(unit) is None]

        # Retreive Proxy assignments
        proxy_units = []
        for proxy in proxy_structures:
            workers = [unit for unit in worker_army if self.target_tag(unit) == proxy.tag]
            proxy_units.append((proxy, workers))

        # Create new assignments
        for proxy, workers in sorted(proxy_units, key=lambda p: (p[0].type_id == UnitTypeId.PHOTONCANNON, p[0].build_progress), reverse=True):
            needed_crew = max(0, self.crew_size - len(workers))

            for _ in range(needed_crew):
                if len(worker_army) >= self.cap_size:
                    break

                if unassigned_units:
                    worker = sorted(unassigned_units, key=lambda u: cy_distance_to_squared(u.position, proxy.position))[0]
                    worker_army.append(worker)
                    unassigned_units.remove(worker)
                    worker.attack(proxy)

                elif worker := mediator.select_worker(target_position=proxy.position):
                    worker_army.append(worker)
                    mediator.clear_role(tag=worker.tag)
                    mediator.assign_role(tag=worker.tag, role=UnitRole.DEFENDING)
                    mediator.remove_worker_from_mineral(worker_tag=worker.tag)
                    worker.attack(proxy)

        return True


    @staticmethod
    def target_tag(unit: Unit) -> int | None:
        """Get the target tag of a unit's current order, if any."""

        if unit.orders and len(unit.orders) > 0 and isinstance(unit.orders[0].target, int):
            return unit.orders[0].target

        return None
