from typing import Dict, List

from ares import AresBot
from ares.behaviors.combat.group import CombatGroupBehavior
from ares.consts import WORKER_TYPES, UnitRole
from ares.managers.manager_mediator import ManagerMediator
from cython_extensions import cy_distance_to_squared
from sc2.ids.unit_typeid import UnitTypeId
from sc2.units import Units


class RepairController(CombatGroupBehavior):
    """Behavior to manage repairing of damaged units and structures."""

    def __init__(self, crew_size: int = 2, cap_crew: int = 8, repair_unit: bool = True, repair_worker: bool = False):
        self.crew_size = crew_size
        self.cap_crew = cap_crew
        self.repair_unit = repair_unit
        self.repair_worker = repair_worker

        self.damaged_units: Dict[int, List[int]] = {}

    def execute(self, ai: AresBot, config: dict, mediator: ManagerMediator) -> bool:

        if not ai.townhalls.exists:
            return False

        # Find damaged units
        damaged_units: Units = ai.structures.filter(lambda u: u.health_percentage < 1.0 and u.build_progress >= 1.0)

        if self.repair_unit:
            damaged_units |= ai.units.filter(lambda u: u.health_percentage < 1.0 and u.type_id not in WORKER_TYPES | {UnitTypeId.MULE})

        if self.repair_worker:
            damaged_units |= ai.units.filter(lambda u: u.health_percentage < 1.0 and u.type_id in WORKER_TYPES)

        near_townhalls = damaged_units.filter(lambda u: any(cy_distance_to_squared(u.position, townhall.position) < 30**2 for townhall in ai.townhalls))
        near_workers = damaged_units.filter(lambda u: any(cy_distance_to_squared(u.position, unit.position) < 10**2 for unit in ai.workers))
        damaged_units = near_townhalls | near_workers 

        # Assign repair crew
        for unit in damaged_units:
            if unit.tag not in self.damaged_units:
                self.damaged_units[unit.tag] = []

            # Survey - keep only workers that are still alive
            self.damaged_units[unit.tag] = [w for w in self.damaged_units[unit.tag] if w in ai.workers.tags]
            crew_size = self.crew_size if unit.is_structure else self.crew_size * 2
            needed_crew = max(0, crew_size - len(self.damaged_units[unit.tag]))
            total_crew = sum(len(self.damaged_units[uid]) for uid in self.damaged_units)
            cap_crew = min(self.cap_crew, (ai.minerals + ai.vespene) // (2 * 15))

            # Assign - one at a time
            if needed_crew > 0 and total_crew < cap_crew:
                worker = None
                role=UnitRole.PROXY_WORKER

                proxy_workers = mediator.get_units_from_role(role=UnitRole.PROXY_WORKER, unit_type=WORKER_TYPES)
                proxy_workers = proxy_workers.filter(lambda u: not u.is_constructing_scv)
                proxy_workers = proxy_workers.filter(lambda u: cy_distance_to_squared(u.position, unit.position) < 12**2)  # type: ignore
                proxy_workers = proxy_workers.filter(lambda u: u.tag not in self.damaged_units[unit.tag])  # type: ignore

                if proxy_workers.exists:
                    worker = proxy_workers.closest_to(unit.position)
                else:
                    role=UnitRole.REPAIRING
                    worker = mediator.select_worker(target_position=unit.position, force_close=True)

                if (worker is None) or (cy_distance_to_squared(worker.position, unit.position) > 25**2):
                    break

                mediator.clear_role(tag=worker.tag)
                mediator.assign_role(tag=worker.tag, role=role)
                mediator.remove_worker_from_mineral(worker_tag=worker.tag)

                self.damaged_units[unit.tag].append(worker.tag)

        # Remove - clean up units no longer damaged
        proxy_workers = mediator.get_units_from_role(role=UnitRole.PROXY_WORKER, unit_type=WORKER_TYPES)
        units_to_remove = [tag for tag in self.damaged_units if tag not in damaged_units.tags]
        for damaged_unit in units_to_remove:
            for worker_tag in self.damaged_units[damaged_unit]:
                if worker_tag in proxy_workers.tags:
                    continue
                mediator.clear_role(tag=worker_tag)
                mediator.assign_role(tag=worker_tag, role=UnitRole.GATHERING)
                if worker := ai.units.find_by_tag(worker_tag):
                    worker.move(ai.townhalls.closest_to(worker.position))

            del self.damaged_units[damaged_unit]

        # Issue repair commands
        for unit_tag, worker_tags in self.damaged_units.items():
            unit = ai.units.find_by_tag(unit_tag) or ai.structures.find_by_tag(unit_tag)

            if unit is None:
                continue

            for worker_tag in worker_tags:
                worker = ai.workers.find_by_tag(worker_tag)

                if worker is None:
                    continue
                if worker.is_repairing:
                    continue

                worker.repair(unit)

        return True
