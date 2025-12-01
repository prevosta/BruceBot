
from ares import AresBot
from ares.consts import TOWNHALL_TYPES
from ares.behaviors.macro.mining import Mining
from bot.behaviors.macro import ArmyComposition, ProxyBuilder, AutoSupply, RepairController, RampWall, TechUpgrade, DropMule
from bot.behaviors.combat import ControlSupplyDepot, SeekAndDestroy, PicketDefence, TankDefence, EarlyCheeseDefense
from bot.behaviors.strategic.StandardRush import StandardRush
from bot.utils import add_placements, get_next_corner_expansion, remove_illegal_positions
from cython_extensions import cy_distance_to_squared
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2


class RedBot(AresBot):
    NAME: str = "RedBot"
    VERSION: str = "0.1.0"
    CODE_NAME: str = "Nullity"

    async def on_start(self) -> None:
        """Called once at the start of the game."""

        await super(RedBot, self).on_start()

        config = self.config.get("Builds", {}).get(self.build_order_runner.chosen_opening, {})

        self.in_attack_mode: bool = False
        self.in_seek_mode: bool = False
        self.attack_at = config.get("AttackAtSupply", 15)
        self.repair_controller = RepairController()

        self.picket_positions = PicketDefence.generate(self)
        self.tank_positions = TankDefence.generate(self)

        # Add static defense placements
        minerals = (self.mineral_field + self.vespene_geyser).closer_than(12, self.start_location)
        near = [Point2(self.start_location.towards(minerals.center, 10)), Point2(self.start_location.towards(minerals.center, 12))]
        add_placements(self, UnitTypeId.MISSILETURRET, self.start_location, near, radius=3)
        near = [self.main_base_ramp.barracks_correct_placement + Point2((2.5, -0.5)), self.start_location]
        add_placements(self, UnitTypeId.MISSILETURRET, self.start_location, near, radius=8)  #, is_wall=True)

        remove_illegal_positions(self)

    async def on_step(self, iteration: int) -> None:
        """Called every game step."""

        await super(RedBot, self).on_step(iteration)

        # Execute behaviors
        for behavior in [
            Mining(long_distance_mine=False),
            DropMule(),
            AutoSupply(),
            RampWall(),
            ProxyBuilder(),
            TechUpgrade(),
            ArmyComposition(),
            ControlSupplyDepot(),
            TankDefence(self.tank_positions),
            # PicketDefence(self.picket_positions),
            # Rebuild
            self.repair_controller,
        ]:
            behavior.execute(self, self.config, self.mediator)

        # Determine actions
        if not self.in_attack_mode and (self.supply_army >= self.attack_at):
            self.in_attack_mode = True
            await self.client.chat_send(f"{iteration} {self.time_formatted} RedBot is attacking!", False)

        is_at_enemy_townhall = any(cy_distance_to_squared(u.position, self.enemy_start_locations[0]) < 9 for u in self.units)
        missing_enemy_townhalls = not self.enemy_structures(TOWNHALL_TYPES).closer_than(3, self.enemy_start_locations[0]).exists
        if not self.in_seek_mode and is_at_enemy_townhall and missing_enemy_townhalls:
            self.in_seek_mode = True
            await self.client.chat_send(f"{iteration} {self.time_formatted} RedBot is seeking!", False)

        # Actions
        if EarlyCheeseDefense().execute(self, self.config, self.mediator):
            return

        elif self.in_seek_mode:
            SeekAndDestroy().execute(self, self.config, self.mediator)

        elif self.in_attack_mode:
            StandardRush().execute(self, self.config, self.mediator)
            # BattleCruiserRush().execute(self, self.config, self.mediator)

    async def get_next_expansion(self) -> Point2 | None:
        """Force expanding to corner bases first."""

        return await get_next_corner_expansion(self)
