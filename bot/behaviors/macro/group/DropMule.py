from __future__ import annotations
from dataclasses import dataclass

from sc2.unit import Unit
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId

from ares import AresBot
from ares.managers.manager_mediator import ManagerMediator
from ares.behaviors.combat.group import CombatGroupBehavior


@dataclass
class DropMule(CombatGroupBehavior):
    """Manages MULE deployment from Orbital Commands."""

    min_energy: int = 50

    def execute(self, ai: AresBot, config: dict, mediator: ManagerMediator) -> bool:
        for townhall in ai.townhalls(UnitTypeId.ORBITALCOMMAND).ready:
            # Only call down MULE if orbital has enough energy
            if townhall.energy < self.min_energy:
                continue

            # Find the best mineral field to drop MULE on
            best_mineral = self._find_best_mineral_field(ai, townhall)
            if not best_mineral:
                continue

            # Call down MULE
            townhall(AbilityId.CALLDOWNMULE_CALLDOWNMULE, best_mineral)
            return True
        
        return False

    def _find_best_mineral_field(self, ai: AresBot, townhall: Unit) -> Unit | None:
        """Find the best mineral field to drop a MULE on."""
        nearby_minerals = ai.mineral_field.closer_than(10, townhall.position)
        if not nearby_minerals:
            return None

        # First priority: minerals with no MULEs assigned
        minerals_without_mules = nearby_minerals.filter(
            lambda m: not any(unit.is_using_ability(AbilityId.HARVEST_GATHER) 
                            and unit.type_id == UnitTypeId.MULE
                            for unit in ai.units if unit.order_target == m.tag)
        )
        
        if minerals_without_mules:
            # Prefer mineral fields with more resources
            return max(minerals_without_mules, key=lambda m: m.mineral_contents)

        # If all minerals have MULEs, pick the one with the most resources
        return max(nearby_minerals, key=lambda m: m.mineral_contents)
