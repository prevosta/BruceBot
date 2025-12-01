from typing import Dict, List

from ares import AresBot
from ares.behaviors.combat.group import CombatGroupBehavior
from ares.consts import WORKER_TYPES, UnitRole
from ares.managers.manager_mediator import ManagerMediator
from cython_extensions import cy_distance_to_squared
from sc2.ids.unit_typeid import UnitTypeId
from sc2.units import Units
from sc2.position import Point2


class RepairController(CombatGroupBehavior):
    """Behavior to manage repairing of damaged units and structures."""

    def __init__(self, crew_size: int = 2, cap_crew: int = 8, lithering: int = 25, repair_unit: bool = True, repair_worker: bool = False):
        self.crew_size = crew_size
        self.cap_crew = cap_crew
        self.lithering = lithering
        self.repair_unit = repair_unit
        self.repair_worker = repair_worker

        self.damaged_units: Dict[int, List[int]] = {}
        self.repair_units: Dict[int, int] = {}

    def execute(self, ai: AresBot, config: dict, mediator: ManagerMediator) -> bool:

        if not ai.townhalls.exists:
            return False

        # Find damaged units
        damaged_units: Units = ai.structures.filter(lambda u: u.health_percentage < 1.0 and u.build_progress >= 1.0)

        if self.repair_unit:
            damaged_units |= ai.units.filter(lambda u: u.health_percentage < 1.0 and u.type_id not in WORKER_TYPES | {UnitTypeId.MULE})

        if self.repair_worker:
            damaged_units |= ai.units.filter(lambda u: u.health_percentage < 1.0 and u.type_id in WORKER_TYPES)

        near_townhalls = damaged_units.filter(lambda u: any(cy_distance_to_squared(u.position, townhall.position) < 35**2 for townhall in ai.townhalls))
        near_workers = damaged_units.filter(lambda u: any(cy_distance_to_squared(u.position, unit.position) < 10**2 for unit in ai.workers))
        damaged_units = near_townhalls | near_workers 

        # Assign repair crew
        for unit in damaged_units.sorted(lambda u: u.health + u.shield):
            if unit.tag not in self.damaged_units:
                self.damaged_units[unit.tag] = []

            # Survey - keep only workers that are still alive
            self.damaged_units[unit.tag] = [w for w in self.damaged_units[unit.tag] if w in ai.workers.tags]
            crew_size = self.crew_size if unit.is_structure else self.crew_size * 2  # More crew for units
            crew_size = crew_size if unit.health_percentage <= 0.9 else 1  # Less crew for minor repairs
            needed_crew = max(0, crew_size - len(self.damaged_units[unit.tag]))
            total_crew = sum(len(self.damaged_units[uid]) for uid in self.damaged_units)
            cap_crew = min(self.cap_crew, (ai.minerals + ai.vespene) // (2 * 15))

            # Assign - one at a time
            if needed_crew > 0 and total_crew < cap_crew:
                worker = None
                role=UnitRole.PROXY_WORKER

                crew_tags = [tag for crew in self.damaged_units.values() for tag in crew]

                proxy_workers = mediator.get_units_from_role(role=UnitRole.PROXY_WORKER, unit_type=WORKER_TYPES)
                proxy_workers = proxy_workers.filter(lambda u: not u.is_constructing_scv and not u.is_repairing)
                proxy_workers = proxy_workers.filter(lambda u: cy_distance_to_squared(u.position, unit.position) < 12**2)  # type: ignore
                proxy_workers = proxy_workers.filter(lambda u: u.tag not in crew_tags)  # type: ignore

                repair_workers = Units(mediator.get_units_from_tags(tags=list(self.repair_units.keys())), ai)
                repair_workers = repair_workers.filter(lambda u: not u.is_constructing_scv and not u.is_repairing)
                repair_workers = repair_workers.filter(lambda u: cy_distance_to_squared(u.position, unit.position) < 12**2)  # type: ignore
                repair_workers = repair_workers.filter(lambda u: u.tag not in crew_tags)  # type: ignore

                # Reuse nearby waiting worker
                if repair_workers.exists:
                    role=UnitRole.REPAIRING
                    worker = repair_workers.closest_to(unit.position)

                # Nearest proxy worker
                elif proxy_workers.exists:
                    role=UnitRole.PROXY_WORKER
                    worker = proxy_workers.closest_to(unit.position)

                # New worker
                else:
                    role=UnitRole.REPAIRING
                    worker = mediator.select_worker(target_position=unit.position, force_close=True)

                if (worker is None) or (cy_distance_to_squared(worker.position, unit.position) > 25**2):
                    break

                mediator.clear_role(tag=worker.tag)
                mediator.assign_role(tag=worker.tag, role=role)
                mediator.remove_worker_from_mineral(worker_tag=worker.tag)

                self.damaged_units[unit.tag].append(worker.tag)
                self.repair_units[worker.tag] = ai.actual_iteration

            # ai.client.debug_text_3d(f"Crew:{len(self.damaged_units[unit.tag])}", unit, size=12, color=(255, 255, 255))

        # Remove - clean up units no longer damaged
        to_remove_tags = [tag for tag in self.damaged_units if tag not in damaged_units.tags]
        for unit_tag in to_remove_tags:
            for worker_tag in self.damaged_units[unit_tag]:
                self.repair_units[worker_tag] = ai.actual_iteration

                if worker := ai.units.find_by_tag(worker_tag):
                    if unit := ai.units.find_by_tag(unit_tag):
                        worker.move(Point2(worker.position.towards(unit.position, -1)))

            del self.damaged_units[unit_tag]

        # Release waiting units
        proxy_workers = mediator.get_units_from_role(role=UnitRole.PROXY_WORKER, unit_type=WORKER_TYPES)
        for worker_tag in list(self.repair_units.keys()):
            if worker_tag in proxy_workers.tags:
                continue
    
            # Wait a few frames before releasing
            if self.repair_units.get(worker_tag, 0) + self.lithering > ai.actual_iteration:
                # if worker := ai.units.find_by_tag(worker_tag):
                #     remaining = (self.repair_units.get(worker_tag, 0) + self.lithering) - ai.actual_iteration
                #     ai.client.debug_text_3d(f"{remaining}", worker, size=12, color=(255, 255, 255))
                continue

            # Release after X frames
            mediator.clear_role(tag=worker_tag)
            mediator.assign_role(tag=worker_tag, role=UnitRole.GATHERING)
            if worker := ai.units.find_by_tag(worker_tag):
                worker.move(ai.townhalls.closest_to(worker.position))
            del self.repair_units[worker_tag]

        # Issue repair commands
        for unit_tag, worker_tags in self.damaged_units.items():
            unit = ai.units.find_by_tag(unit_tag) or ai.structures.find_by_tag(unit_tag)

            if unit is None:
                continue

            for worker_tag in worker_tags:
                worker = ai.workers.find_by_tag(worker_tag)
                self.repair_units[worker_tag] = ai.actual_iteration

                if worker is None:
                    continue

                # ai.client.debug_text_3d(f"R", worker, size=12, color=(255, 255, 255))

                if worker.is_repairing:
                    continue

                worker.repair(unit)

        return True
