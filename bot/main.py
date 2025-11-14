from typing import Optional

from sc2.unit import Unit
from sc2.position import Point2
from sc2.ids.unit_typeid import UnitTypeId

from ares import AresBot
from ares.consts import TOWNHALL_TYPES, WORKER_TYPES
from ares.behaviors.macro.mining import Mining

from bot.behaviors.macro.RebuildAddons import ReBuildAddons
from bot.behaviors.macro.RebuildDestroyStructure import RebuildDestroyStructure
from bot.behaviors.macro.RepairControler import RepairController
from bot.utils import add_placements, remove_illegal_positions, show_placements
from bot.behaviors.combat.TankDefence import TankDefence
from bot.behaviors.combat.PicketDefence import PicketDefence
from bot.behaviors.combat.BattleCruiser import BattleCruiser
from bot.behaviors.combat.SeekAndDestroy import SeekAndDestroy
from bot.behaviors.combat.TankDefence import TankDefence
from bot.behaviors.macro import AutoSupply, ControlSupplyDepot, DropMule, ProxyBuilder, UpgradeTech
from bot.behaviors.macro.ArmyComposition import ArmyComposition
from bot.behaviors.macro.TrainWorker import TrainWorker


class BruceBot(AresBot):
    NAME: str = "BruceBot"
    VERSION: str = "1.0.0"
    CODE_NAME: str = "FootLoose"

    def __init__(self, game_step_override: Optional[int] = None):
        super().__init__(game_step_override)

    async def on_start(self) -> None:
        await super(BruceBot, self).on_start()
        
        self.picket_positions = PicketDefence.generate(self)
        self.tank_positions = TankDefence.generate(self)
        self.rebuildDestroyStructure = RebuildDestroyStructure()
        self.repair_controller = RepairController()

        remove_illegal_positions(self)

    async def on_step(self, iteration: int) -> None:
        await super(BruceBot, self).on_step(iteration)

        # Greetings
        if iteration == 5:
            await self.client.chat_send(f"{self.NAME} v{self.VERSION} {self.CODE_NAME}", False)
            await self.client.chat_send("Calling in the fleet! Good luck, have fun!", False)
            # near = [self.main_base_ramp.top_center, self.main_base_ramp.bottom_center]
            # add_placements(self, UnitTypeId.BUNKER, self.start_location, near, radius=8)
            if self.main_base_ramp.barracks_correct_placement:
                near = [self.main_base_ramp.barracks_correct_placement + Point2((2.5, -0.5)), self.start_location]
                add_placements(self, UnitTypeId.MISSILETURRET, self.start_location, near, radius=8)

        # Behaviors
        self.register_behavior(Mining())
        self.register_behavior(DropMule())
        self.register_behavior(ControlSupplyDepot())
        self.register_behavior(ProxyBuilder())
        if self.unit_pending(UnitTypeId.BATTLECRUISER) or hasattr(self, 'battlecruiser_started'):
            setattr(self, 'battlecruiser_started', True)
            self.register_behavior(UpgradeTech())
        self.register_behavior(self.repair_controller)
        self.register_behavior(self.rebuildDestroyStructure)
        self.register_behavior(ReBuildAddons())
        self.register_behavior(AutoSupply(base_location=self.start_location))

        # Seek and destroy
        if (self.time > 6.5 * 60) and not self.enemy_structures(TOWNHALL_TYPES).exists:
            if getattr(self, 'seek_and_destroy_activated', False):
                setattr(self, 'seek_and_destroy_activated', True)
                await self.client.chat_send(f"{self.time_formatted} {iteration} Searching, seek and destroy.", False)

            self.register_behavior(SeekAndDestroy())

        # Main actions
        else:
            self.register_behavior(PicketDefence(pickets=self.picket_positions))
            self.register_behavior(TankDefence(tank_positions=self.tank_positions))
            self.register_behavior(BattleCruiser(priority=WORKER_TYPES))

        # Production
        if self.units(UnitTypeId.BATTLECRUISER).exists or self.unit_pending(UnitTypeId.BATTLECRUISER):
            self.register_behavior(ArmyComposition())
            self.register_behavior(TrainWorker())

    async def on_unit_created(self, unit: Unit) -> None:
        await super().on_unit_created(unit)
        if unit.type_id == UnitTypeId.SIEGETANK and self.units(UnitTypeId.SIEGETANK).amount == 1:
            await self.client.chat_send(f"{self.actual_iteration} {self.time_formatted} {unit.type_id.name}", False)
        if unit.type_id == UnitTypeId.BATTLECRUISER and self.units(UnitTypeId.BATTLECRUISER).amount == 1:
            await self.client.chat_send(f"{self.actual_iteration} {self.time_formatted} {unit.type_id.name}", False)

    async def on_building_construction_complete(self, unit: Unit) -> None:
        await super().on_building_construction_complete(unit)
        self.rebuildDestroyStructure.register_structure(unit)

    async def on_unit_destroyed(self, unit_tag: int) -> None:
        await super().on_unit_destroyed(unit_tag)
        self.rebuildDestroyStructure.register_destroyed_structure(unit_tag)
