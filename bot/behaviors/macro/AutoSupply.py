from dataclasses import dataclass

from sc2.position import Point2

from ares import AresBot
from ares.consts import BUILDS
from ares.managers.manager_mediator import ManagerMediator
from ares.behaviors.combat.group import CombatGroupBehavior
from ares.behaviors.macro.auto_supply import AutoSupply as auto_supply

@dataclass
class AutoSupply(CombatGroupBehavior):
    """Behavior to automatically build supply depots when supply is low."""

    base_location: Point2

    def execute(self, ai: AresBot, config: dict, mediator: ManagerMediator) -> bool:
        opening_name = ai.build_order_runner.chosen_opening
        auto_supply_at = config[BUILDS][opening_name]["AutoSupplyAtSupply"]

        if ai.build_order_runner.build_completed or ai.supply_used >= auto_supply_at:
            return auto_supply(ai.start_location).execute(ai, config, mediator)

        return False
