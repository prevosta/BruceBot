from typing import Optional

from ares import AresBot
from ares.behaviors.macro.mining import Mining
from ares.consts import WORKER_TYPES
from cython_extensions import cy_distance_to_squared
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.unit import Unit

from bot.behaviors.combat import (
    ArmyAttack,
    BattleCruiser,
    PicketDefence,
    SeekAndDestroy,
    TankDefence,
)
from bot.behaviors.combat.BattleCruiserYamato import BattleCruiserYamato
from bot.behaviors.macro import (
    ArmyComposition,
    AutoSupply,
    ControlSupplyDepot,
    DropMule,
    EarlyCheeseDefense,
    ProxyBuilder,
    RampBuilder,
    ReBuildAddons,
    RebuildDestroyStructure,
    RepairController,
    TrainWorker,
    UpgradeTech,
)
from bot.utils import add_placements, remove_illegal_positions


class BruceBot(AresBot):
    NAME: str = "BruceBot"
    VERSION: str = "2.2.0"
    CODE_NAME: str = "Fearless"

    def __init__(self, game_step_override: Optional[int] = None):
        super().__init__(game_step_override)

    async def on_start(self) -> None:
        await super(BruceBot, self).on_start()

        self.cheese_in_progress = False
        self.seek_and_destroy = False
        self.battlecruiser_production_started = False

        self.picket_positions = PicketDefence.generate(self)
        self.tank_positions = TankDefence.generate(self)
        self.rebuildDestroyStructure = RebuildDestroyStructure()
        self.repair_controller = RepairController()

        remove_illegal_positions(self)
        self.map_info = ProxyBuilder.compute_map_info(self, self.mediator)
        self.proxy_placements = self.map_info.buildable_locations[self.map_info.proxy_locations[0][0]]

    async def on_step(self, iteration: int) -> None:
        await super(BruceBot, self).on_step(iteration)

        # Greetings
        if iteration == 15:
            await self.client.chat_send(f"{self.NAME} v{self.VERSION} {self.CODE_NAME}", False)
            await self.client.chat_send("Calling in the fleet! Good luck, have fun!", False)
            if self.main_base_ramp.barracks_correct_placement:
                near = [self.main_base_ramp.barracks_correct_placement + Point2((2.5, -0.5)), self.start_location]
                add_placements(self, UnitTypeId.MISSILETURRET, self.start_location, near, radius=8)
                minerals = self.mineral_field.closer_than(12, self.start_location)
                near = [Point2(self.start_location.towards(minerals.center, 10)), Point2(self.start_location.towards(minerals.center, 12))]
                add_placements(self, UnitTypeId.MISSILETURRET, self.start_location, near, radius=3)

        # Behaviors
        Mining(workers_per_gas=0 if self.cheese_in_progress else 3).execute(self, self.config, self.mediator)
        DropMule().execute(self, self.config, self.mediator)
        ControlSupplyDepot().execute(self, self.config, self.mediator)
        ProxyBuilder(self.proxy_placements).execute(self, self.config, self.mediator)
        RampBuilder().execute(self, self.config, self.mediator)
        UpgradeTech(self.ready_to_upgrade).execute(self, self.config, self.mediator)
        self.repair_controller.execute(self, self.config, self.mediator)
        self.rebuildDestroyStructure.execute(self, self.config, self.mediator)
        ReBuildAddons().execute(self, self.config, self.mediator)
        AutoSupply(self.start_location).execute(self, self.config, self.mediator)

        # Reactions
        if EarlyCheeseDefense().execute(self, self.config, self.mediator):
            if not self.cheese_in_progress:
                await self.client.chat_send(f"{iteration} {self.time_formatted} Early cheese defense activated.", False)
                self.cheese_in_progress = True
        else:
            self.cheese_in_progress = False

        if self.cheese_in_progress:
            pass
        
        # Main actions
        elif ArmyAttack({UnitTypeId.BATTLECRUISER}).execute(self, self.config, self.mediator):
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

            PicketDefence(pickets=self.picket_positions).execute(self, self.config, self.mediator)
            TankDefence(tank_positions=self.tank_positions).execute(self, self.config, self.mediator)
            BattleCruiser(self.proxy_placements[0], priorities=WORKER_TYPES, high_threats=high_threats).execute(self, self.config, self.mediator)
            self.seek_and_destroy = False

        # Searching, seek and destroy
        else:
            SeekAndDestroy().execute(self, self.config, self.mediator)
            for unit in self.units(UnitTypeId.BATTLECRUISER):
                BattleCruiserYamato(unit).execute(self, self.config, self.mediator)

            if not self.seek_and_destroy:
                self.seek_and_destroy = True
                await self.client.chat_send(f"{iteration} {self.time_formatted} Searching, seek and destroy.", False)

        # Production
        if self.units(UnitTypeId.BATTLECRUISER).exists or self.unit_pending(UnitTypeId.BATTLECRUISER):
            ArmyComposition().execute(self, self.config, self.mediator)
            TrainWorker(n_extra=4).execute(self, self.config, self.mediator)

    async def on_unit_created(self, unit: Unit) -> None:
        """Called when a unit is created."""

        await super().on_unit_created(unit)
        if unit.type_id == UnitTypeId.MARINE and self.units(UnitTypeId.MARINE).amount == 1 and self.time < 180:
            await self.client.chat_send(f"{self.actual_iteration} {self.time_formatted} {unit.type_id.name}", False)
        if unit.type_id == UnitTypeId.SIEGETANK and self.units(UnitTypeId.SIEGETANK).amount == 1 and self.time < 240:
            await self.client.chat_send(f"{self.actual_iteration} {self.time_formatted} {unit.type_id.name}", False)
        if unit.type_id == UnitTypeId.BATTLECRUISER and self.units(UnitTypeId.BATTLECRUISER).amount == 1 and self.time < 360:
            await self.client.chat_send(f"{self.actual_iteration} {self.time_formatted} {unit.type_id.name}", False)

    async def on_building_construction_started(self, unit: Unit) -> None:
        """Called when a building construction is started."""

        await super().on_building_construction_started(unit)
        if unit.type_id == UnitTypeId.SUPPLYDEPOT and self.structures({UnitTypeId.SUPPLYDEPOT, UnitTypeId.SUPPLYDEPOTLOWERED}).ready.amount + self.structure_pending(UnitTypeId.SUPPLYDEPOT) == 2 and self.time < 180:
            await self.client.chat_send(f"{self.actual_iteration} {self.time_formatted} RAMP_WALL", False)

    async def on_building_construction_complete(self, unit: Unit) -> None:
        """Called when a building construction is complete."""

        await super().on_building_construction_complete(unit)
        if unit.type_id == UnitTypeId.MISSILETURRET and self.structures(UnitTypeId.MISSILETURRET).amount == 1 and self.time < 300:
            await self.client.chat_send(f"{self.actual_iteration} {self.time_formatted} AIR_DEFENSE", False)
        self.rebuildDestroyStructure.register_structure(unit)

    async def on_unit_destroyed(self, unit_tag: int) -> None:
        """Called when a unit is destroyed."""

        await super().on_unit_destroyed(unit_tag)
        self.rebuildDestroyStructure.register_destroyed_structure(unit_tag)

    def ready_to_upgrade(self) -> bool:
        """Toggles when to start upgrading"""

        if not self.battlecruiser_production_started:
            if self.units(UnitTypeId.BATTLECRUISER).amount + self.unit_pending(UnitTypeId.BATTLECRUISER) >= 2:
                self.battlecruiser_production_started = True
        return self.battlecruiser_production_started

    async def get_next_expansion(self) -> Point2 | None:
        """Find next expansion location."""

        enemy_start: Point2 = self.enemy_start_locations[0]
        own_start: Point2 = self.start_location

        closest_location: Point2 | None = None
        closest_distance: float = self.EXPANSION_GAP_THRESHOLD

        for location in self.expansion_locations_list:
            distance: float = 0

            def is_close_to_expansion(townhall: Unit) -> bool:
                return cy_distance_to_squared(townhall.position, location.position) < self.EXPANSION_GAP_THRESHOLD

            if any(is_close_to_expansion(t) for t in self.townhalls):
                continue  # already taken

            if enemy_path := await self.client.query_pathing(enemy_start, location):
                distance += float(enemy_path)

            if own_path := await self.client.query_pathing(own_start, location):
                distance += float(own_path)

            if (self.EXPANSION_GAP_THRESHOLD < distance) and (distance > closest_distance):
                closest_distance = distance
                closest_location = location

        return closest_location