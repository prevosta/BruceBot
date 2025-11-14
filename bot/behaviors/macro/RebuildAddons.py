from dataclasses import dataclass

from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId

from ares import AresBot
from ares.managers.manager_mediator import ManagerMediator


@dataclass
class ReBuildAddons:
    """Rebuilds missing tech labs on barracks."""

    def execute(self, ai: AresBot, config: dict, mediator: ManagerMediator) -> bool:
        if not ai.build_order_runner.build_completed:
            return False

        for starport in ai.structures(UnitTypeId.STARPORT).ready.idle:
            if not starport.has_add_on and ai.can_afford(UnitTypeId.STARPORTTECHLAB):
                starport(AbilityId.BUILD_TECHLAB)

                return True

        return False
