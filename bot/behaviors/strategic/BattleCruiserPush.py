from dataclasses import dataclass

from ares import AresBot
from ares.behaviors.combat.group import CombatGroupBehavior
from ares.managers.manager_mediator import ManagerMediator
from bot.behaviors.combat import ArmyAttack, BattleCruiser, PicketDefence, SeekAndDestroy, TankDefence
from bot.behaviors.macro import EarlyCheeseDefense
from ares.consts import WORKER_TYPES
from sc2.ids.unit_typeid import UnitTypeId
from sc2.unit import Unit

@dataclass
class BattleCruiserPush(CombatGroupBehavior):
    """"""

    def execute(self, ai: AresBot, config: dict, mediator: ManagerMediator) -> bool:
        # Reactions
        if EarlyCheeseDefense().execute(ai, ai.config, ai.mediator):
            if not ai.cheese_in_progress:
                await ai.client.chat_send(f"{iteration} {ai.time_formatted} Early cheese defense activated.", False)
                ai.cheese_in_progress = True
        else:
            ai.cheese_in_progress = False

        if ai.cheese_in_progress:
            pass
        
        # Main actions
        elif ArmyAttack({UnitTypeId.BATTLECRUISER}).execute(ai, ai.config, ai.mediator):
            high_threats = {
                UnitTypeId.MISSILETURRET,
                UnitTypeId.BUNKER,
                UnitTypeId.PHOTONCANNON,
                UnitTypeId.SPORECRAWLER,
                UnitTypeId.VIKINGFIGHTER,
                UnitTypeId.QUEEN,
                UnitTypeId.CORRUPTOR,
                UnitTypeId.VOIDRAY,
                UnitTypeId.BATTLECRUISER,
                UnitTypeId.CARRIER,
            }

            PicketDefence(pickets=ai.picket_positions).execute(ai, ai.config, ai.mediator)
            TankDefence(tank_positions=ai.tank_positions).execute(ai, ai.config, ai.mediator)
            BattleCruiser(ai.proxy_placements[0], priorities=WORKER_TYPES, high_threats=high_threats).execute(ai, ai.config, ai.mediator)

            # Scouting
            for scout in ai.units(UnitTypeId.REAPER):
                waypoints = [x[0] for x in ai.mediator.get_enemy_expansions[1:-2]]
                ReaperScout(scout, waypoints).execute(ai, ai.config, ai.mediator)

            ai.seek_and_destroy = False

        # Searching, seek and destroy
        else:
            SeekAndDestroy().execute(ai, ai.config, ai.mediator)
            for unit in ai.units(UnitTypeId.BATTLECRUISER):
                BattleCruiserYamato(unit).execute(ai, ai.config, ai.mediator)

            if not ai.seek_and_destroy:
                ai.seek_and_destroy = True
                await ai.client.chat_send(f"{iteration} {ai.time_formatted} Searching, seek and destroy.", False)

        return True
