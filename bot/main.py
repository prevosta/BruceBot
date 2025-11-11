from typing import Optional

from sc2.ids.unit_typeid import UnitTypeId
from sc2.unit import Unit

from ares import AresBot
from ares.consts import TOWNHALL_TYPES
from ares.behaviors.macro.mining import Mining
from ares.behaviors.macro.auto_supply import AutoSupply

from bot.behaviors.combat.group.TankDefence import TankDefence
from bot.behaviors.combat.group.PicketDefence import PicketDefence, generate_pickets
from bot.behaviors.combat.group.BattleCruiser import BattleCruiser
from bot.behaviors.combat.group.SeekAndDestroy import SeekAndDestroy
from bot.behaviors.combat.group.TankDefence import TankDefence, generate_tank_positions
from bot.behaviors.macro.group import ControlSupplyDepot, DropMule, ProxyBuilder
from bot.behaviors.macro.group.ArmyComposition import ArmyComposition
from bot.behaviors.macro.group.TrainWorker import TrainWorkers
from bot.utils import remove_illegal_positions


class BruceBot(AresBot):
    NAME: str = "BruceBot"
    VERSION: str = "0.1.0"
    CODE_NAME: str = "FightRepairRepeat"

    def __init__(self, game_step_override: Optional[int] = None):
        super().__init__(game_step_override)

    async def on_start(self) -> None:
        await super(BruceBot, self).on_start()
        remove_illegal_positions(self)
        self.picket_positions = generate_pickets(self)
        self.tank_positions = generate_tank_positions(self)

    async def on_step(self, iteration: int) -> None:
        await super(BruceBot, self).on_step(iteration)

        # Greetings
        if iteration == 25:
            await self.client.chat_send(f"{self.NAME} v{self.VERSION} {self.CODE_NAME}", False)
            await self.client.chat_send("Calling in the fleet! Good luck, have fun!", False)

        # Behaviors
        self.register_behavior(Mining())
        self.register_behavior(DropMule())
        self.register_behavior(ControlSupplyDepot())
        self.register_behavior(ProxyBuilder())
        if self.supply_used >= 40:
            self.register_behavior(AutoSupply(self.start_location))

        # Seek and destroy
        if (self.time > 6.5 * 60) and not self.enemy_structures(TOWNHALL_TYPES).exists:
            self.register_behavior(SeekAndDestroy())

        # Main actions
        else:
            self.register_behavior(PicketDefence(pickets=self.picket_positions))
            self.register_behavior(TankDefence(tank_positions=self.tank_positions))
            self.register_behavior(BattleCruiser(priority=set()))

        # Production
        if self.units(UnitTypeId.BATTLECRUISER).exists or self.unit_pending(UnitTypeId.BATTLECRUISER):
            self.register_behavior(ArmyComposition())
            self.register_behavior(TrainWorkers())

    async def on_unit_created(self, unit: Unit) -> None:
        await super().on_unit_created(unit)
        if unit.type_id == UnitTypeId.SIEGETANK and self.units(UnitTypeId.SIEGETANK).amount == 1:
            await self.client.chat_send(f"{self.actual_iteration} {self.time_formatted} {unit.type_id.name}", False)
        if unit.type_id == UnitTypeId.BATTLECRUISER and self.units(UnitTypeId.BATTLECRUISER).amount == 1:
            await self.client.chat_send(f"{self.actual_iteration} {self.time_formatted} {unit.type_id.name}", False)
