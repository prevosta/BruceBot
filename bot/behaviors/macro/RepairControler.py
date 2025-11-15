from typing import Dict, List

from cython_extensions import cy_distance_to_squared

from sc2.units import Units
from sc2.ids.unit_typeid import UnitTypeId

from ares import AresBot
from ares.consts import WORKER_TYPES, UnitRole
from ares.managers.manager_mediator import ManagerMediator
from ares.behaviors.combat.group import CombatGroupBehavior


class RepairController(CombatGroupBehavior):
    def __init__(self, crew_size: int = 2, repair_unit: bool = True, repair_worker: bool = False):
        self.crew_size = crew_size
        self.repair_unit = repair_unit
        self.repair_worker = repair_worker

        self.damaged_units: Dict[int, List[int]] = {}

    def execute(self, ai: AresBot, config: dict, mediator: ManagerMediator) -> bool:

        # roles = {tag: role for role, tags in mediator.get_unit_role_dict.items() for tag in tags}
        # print([roles.get(tag) for tag in ai.workers.tags if roles.get(tag) != UnitRole.GATHERING])

        # Find damaged units
        damaged_units: Units = ai.structures.filter(lambda u: u.health_percentage < 1.0 and u.build_progress >= 1.0)

        if self.repair_unit:
            damaged_units |= ai.units.filter(lambda u: u.health_percentage < 1.0 and u.type_id not in WORKER_TYPES | {UnitTypeId.MULE})

        if self.repair_worker:
            damaged_units |= ai.units.filter(lambda u: u.health_percentage < 1.0 and u.type_id in WORKER_TYPES)

        damaged_units = damaged_units.filter(lambda u: cy_distance_to_squared(u.position, ai.start_location) < 30**2)

        # Assign repair crew
        for unit in damaged_units:
            if unit.tag not in self.damaged_units:
                self.damaged_units[unit.tag] = []

            # Survey - keep only workers that are still alive
            self.damaged_units[unit.tag] = [w for w in self.damaged_units[unit.tag] if w in ai.workers.tags]
            crew_size = self.crew_size if unit.is_structure else self.crew_size * 2
            needed_crew = max(0, crew_size - len(self.damaged_units[unit.tag]))

            # Assign - one at a time
            if needed_crew > 0:
                worker = mediator.select_worker(target_position=unit.position)

                if worker is None:
                    break

                mediator.clear_role(tag=worker.tag)
                mediator.assign_role(tag=worker.tag, role=UnitRole.REPAIRING)
                mediator.remove_worker_from_mineral(worker_tag=worker.tag)

                self.damaged_units[unit.tag].append(worker.tag)

        # Remove - clean up units no longer damaged
        units_to_remove = [tag for tag in self.damaged_units if tag not in damaged_units.tags]
        for damaged_unit in units_to_remove:
            for worker_tag in self.damaged_units[damaged_unit]:
                mediator.clear_role(tag=worker_tag)
                mediator.assign_role(tag=worker_tag, role=UnitRole.GATHERING)

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
