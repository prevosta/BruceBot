from dataclasses import dataclass

from ares import AresBot
from ares.consts import BUILDS
from ares.behaviors.combat.group import CombatGroupBehavior
from ares.behaviors.macro.auto_supply import AutoSupply as auto_supply
from ares.managers.manager_mediator import ManagerMediator
from sc2.position import Point2
from sc2.ids.unit_typeid import UnitTypeId


AUTO_SUPPLY_AT_SUPPLY: str = "AutoSupplyAtSupply"

@dataclass
class AutoSupply(CombatGroupBehavior):
    """Behavior to automatically build supply depots when supply cap is reached or exceeded."""

    base_location: Point2 | None = None
    max_pending: int = 1

    def execute(self, ai: AresBot, config: dict, mediator: ManagerMediator) -> bool:
        opening_name = ai.build_order_runner.chosen_opening
        auto_supply_at = config.get(BUILDS, {}).get(opening_name, {}).get(AUTO_SUPPLY_AT_SUPPLY, None)

        if auto_supply_at and ai.supply_used < auto_supply_at:
            return False

        if ai.structure_pending(UnitTypeId.SUPPLYDEPOT) >= self.max_pending:
            return False

        if ai.build_order_runner.build_completed or ai.supply_used >= auto_supply_at:
            base_location = self.base_location if self.base_location is not None else ai.start_location
            return auto_supply(base_location).execute(ai, config, mediator)

        return False
