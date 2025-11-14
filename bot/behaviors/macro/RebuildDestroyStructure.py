from __future__ import annotations
from dataclasses import dataclass

from sc2.unit import Unit
from sc2.position import Point2
from sc2.ids.unit_typeid import UnitTypeId

from ares import AresBot
from ares.consts import BuildingSize
from ares.behaviors.macro.build_structure import BuildStructure
from ares.dicts.structure_to_building_size import STRUCTURE_TO_BUILDING_SIZE
from ares.managers.manager_mediator import ManagerMediator
from ares.behaviors.combat.group import CombatGroupBehavior


@dataclass
class RebuildDestroyStructure(CombatGroupBehavior):
    """Behavior to rebuild destroyed structures."""

    def __init__(self):
        super().__init__()
        self.structures: dict[int, tuple[UnitTypeId, Point2]] = {}
        self.destroyed_structures: list[int] = []
        self.requested_rebuilds: dict[int, float] = {}

    def execute(self, ai: AresBot, config: dict, mediator: ManagerMediator) -> bool:
        for unit_tag in self.destroyed_structures:
            structure_id, closest_to = self.structures[unit_tag]

            if unit_tag in self.requested_rebuilds:
                if ai.time - self.requested_rebuilds[unit_tag] > 30:
                    del self.requested_rebuilds[unit_tag]
                    print(f"Rebuild {unit_tag}, timed out.")
                continue

            if ai.can_afford(structure_id):
                region = mediator.get_map_data_object.where(ai.start_location)
                if not region.is_inside_point(closest_to):
                    closest_to = ai.start_location

                if BuildStructure(base_location=closest_to, structure_id=structure_id, closest_to=closest_to).execute(ai, config, mediator):
                    print(f"Rebuild {unit_tag} {structure_id.name} {closest_to}.")
                    self.requested_rebuilds[unit_tag] = ai.time
                    return True

        return False

    def register_structure(self, unit: Unit) -> None:
        if not unit.is_structure:
            return  # only structures

        if unit.type_id not in STRUCTURE_TO_BUILDING_SIZE:
            return  # only care about buildable structures

        if STRUCTURE_TO_BUILDING_SIZE == BuildingSize.FIVE_BY_FIVE:
            return  # no townhalls

        self.structures[unit.tag] = (unit.type_id, unit.position)

    def register_destroyed_structure(self, unit_tag: int) -> None:
        if (unit_tag in self.structures) and (unit_tag not in self.destroyed_structures):
            self.destroyed_structures.append(unit_tag)
            print(f"Registered: {unit_tag}")
