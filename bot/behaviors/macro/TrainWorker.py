from dataclasses import dataclass

from sc2.ids.unit_typeid import UnitTypeId

from ares import AresBot
from ares.managers.manager_mediator import ManagerMediator
from ares.behaviors.combat.group import CombatGroupBehavior


@dataclass
class TrainWorker(CombatGroupBehavior):
    """Manages worker training at all townhalls."""

    n_per_townhall: int = 22

    def execute(self, ai: AresBot, config: dict, mediator: ManagerMediator) -> bool:
        n_workers = ai.townhalls.amount * self.n_per_townhall

        for townhall in ai.townhalls:
            if townhall.is_idle and ai.can_afford(UnitTypeId.SCV) and ai.workers.amount < n_workers:
                townhall.train(UnitTypeId.SCV)

        return True
