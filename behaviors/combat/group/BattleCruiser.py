from dataclasses import dataclass

from sc2.ids.unit_typeid import UnitTypeId

from ares import AresBot
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

        return False
