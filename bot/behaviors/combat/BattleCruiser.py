from dataclasses import dataclass

from ares import AresBot
from ares.behaviors.combat.group import CombatGroupBehavior
from ares.managers.manager_mediator import ManagerMediator
from sc2.ids.unit_typeid import UnitTypeId

from bot.behaviors.combat.BattleCruiserAttack import BattleCruiserAttack
from bot.behaviors.combat.BattleCruiserPatrol import BattleCruiserPatrol
from bot.behaviors.combat.BattleCruiserSupport import BattleCruiserSupport
from bot.behaviors.combat.BattleCruiserRepair import BattleCruiserRepair
from bot.behaviors.combat.BattleCruiserYamato import BattleCruiserYamato

@dataclass
class BattleCruiser(CombatGroupBehavior):
    """Manages BattleCruisers in combat."""

    priorities: set[UnitTypeId] | None = None # Battery Cannon priority
    high_threats: set[UnitTypeId] | None = None # Yamato Cannon priority

    def execute(self, ai: AresBot, config: dict, mediator: ManagerMediator) -> bool:
        fleet = ai.units(UnitTypeId.BATTLECRUISER)
        order_issue = False

        for unit in fleet:
            if BattleCruiserYamato(unit, self.high_threats).execute(ai, config, mediator):
                order_issue = True
                continue

            if BattleCruiserRepair(unit).execute(ai, config, mediator):
                order_issue = True
                continue

            if BattleCruiserSupport(unit).execute(ai, config, mediator):
                order_issue = True
                continue

            if BattleCruiserAttack(unit, self.priorities, self.high_threats).execute(ai, config, mediator):
                order_issue = True
                continue

            if BattleCruiserPatrol(unit).execute(ai, config, mediator):
                order_issue = True
                continue

        return order_issue
