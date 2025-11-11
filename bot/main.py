from typing import Optional

from cython_extensions import cy_distance_to_squared

from sc2.position import Point2
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId
from sc2.unit import Unit

from ares import AresBot
from ares.consts import TOWNHALL_TYPES, WORKER_TYPES
from ares.behaviors.macro.mining import Mining
from ares.behaviors.macro.auto_supply import AutoSupply

from behaviors.combat.group.BattleCruiser import BattleCruiser
from behaviors.macro.group import ControlSupplyDepot, DropMule, ProxyBuilder


class BruceBot(AresBot):
    def __init__(self, game_step_override: Optional[int] = None):
        super().__init__(game_step_override)

    async def on_start(self) -> None:
        await super(BruceBot, self).on_start()
        remove_illegal_positions(self)

    async def on_step(self, iteration: int) -> None:
        await super(BruceBot, self).on_step(iteration)

        # Greetings
        if iteration == 25:
            await self.client.chat_send(f"BruceBot v0.0.1 online. Good luck, have fun!", False)

        # Initialize defence positions
        if iteration == 10:
            self.tank_positions = [Point2((self.main_base_ramp.top_center.towards(self.start_location, 10)))]
            self.picket_positions = [Point2((self.main_base_ramp.top_center.towards(self.start_location, 4)))]
            if climber_ingress := compute_climber_ingress(self):
                self.picket_positions.extend(climber_ingress)

        self.register_behavior(Mining())
        self.register_behavior(DropMule())
        self.register_behavior(ControlSupplyDepot())
        self.register_behavior(ProxyBuilder())
        self.register_behavior(BattleCruiser(priority={UnitTypeId.VIKINGFIGHTER, UnitTypeId.MEDIVAC}))
        if self.supply_used >= 40:
            self.register_behavior(AutoSupply(self.start_location))

        # Seek and destroy
        if self.time > 6.5 * 60 and not self.enemy_structures(TOWNHALL_TYPES).exists:
            for unit in self.units.filter(lambda u: u.type_id not in WORKER_TYPES):
                if enemy_units := self.enemy_units | self.enemy_structures:
                    unit.attack(enemy_units.closest_to(unit))

                elif not unit.is_moving:
                    from random import uniform
                    unit.move(Point2((uniform(0, self.game_info.map_size.x), uniform(0, self.game_info.map_size.y))))

        # Defence positions
        else:
            for unit in self.units({UnitTypeId.MARINE, UnitTypeId.SIEGETANK, UnitTypeId.BATTLECRUISER}):
                if unit.type_id == UnitTypeId.MARINE:
                    if cy_distance_to_squared(unit.position, self.picket_positions[-1]) > 2**2:
                        unit.move(self.picket_positions[-1])

                elif unit.type_id == UnitTypeId.SIEGETANK:
                    if cy_distance_to_squared(unit.position, self.tank_positions[0]) > 2**2:
                        unit.move(self.tank_positions[0])
                    else:
                        unit(AbilityId.SIEGEMODE_SIEGEMODE)

                elif unit.type_id == UnitTypeId.BATTLECRUISER:
                    p1 = Point2(self.enemy_start_locations[0].towards(self.mediator.get_enemy_ramp.top_center, 1))
                    p2 = Point2(self.mediator.get_enemy_nat.towards(self.game_info.map_center, 1))

                    if unit.orders and isinstance(unit.orders[0].target, Point2) and cy_distance_to_squared(unit.orders[0].target, p1) < 1:
                        if cy_distance_to_squared(unit.position, p1) < 1**2:
                            unit.move(p2)
                    elif unit.orders and isinstance(unit.orders[0].target, Point2) and cy_distance_to_squared(unit.orders[0].target, p2) < 1:
                        if cy_distance_to_squared(unit.position, p2) < 1**2:
                            unit.move(p1)
                    else:
                        unit.move(p1)

        # Production
        if self.units(UnitTypeId.BATTLECRUISER).exists or self.unit_pending(UnitTypeId.BATTLECRUISER):
            # if (self.minerals - self.vespene) > 200:
            #     BuildStructure(self.start_location, UnitTypeId.BARRACKS).execute(self, self.config, self.mediator)
            for structure in self.structures(UnitTypeId.BARRACKS):
                if structure.is_idle and self.can_afford(UnitTypeId.MARINE) and self.minerals > self.vespene:
                    structure.train(UnitTypeId.MARINE)
            for structure in self.structures(UnitTypeId.STARPORT):
                if structure.is_idle and self.can_afford(UnitTypeId.BATTLECRUISER):
                    structure.train(UnitTypeId.BATTLECRUISER)
            n_workers = self.townhalls.amount * 22
            for townhall in self.townhalls:
                if townhall.is_idle and self.can_afford(UnitTypeId.SCV) and self.workers.amount < n_workers:
                    townhall.train(UnitTypeId.SCV)

    async def on_unit_created(self, unit: Unit) -> None:
        await super().on_unit_created(unit)
        if unit.type_id == UnitTypeId.SIEGETANK and self.units(UnitTypeId.SIEGETANK).amount == 1:
            await self.client.chat_send(f"{self.actual_iteration} {self.time_formatted} {unit.type_id.name}", False)
        if unit.type_id == UnitTypeId.BATTLECRUISER and self.units(UnitTypeId.BATTLECRUISER).amount == 1:
            await self.client.chat_send(f"{self.actual_iteration} {self.time_formatted} {unit.type_id.name}", False)

def compute_climber_ingress(ai: AresBot) -> list[Point2]:
    ingress_points = []
    targets = [ai.enemy_start_locations[0], ai.mediator.get_own_expansions[0][0], ai.mediator.get_own_expansions[2][0]]
    
    for target in targets:
        if path := ai.mediator.find_raw_path(start=ai.start_location, target=target, grid=ai.mediator.get_climber_grid, sensitivity=1):
            region = ai.mediator.get_map_data_object.where(ai.start_location)
            best_point = min(
                ((p, min(p.distance_to(path_point) for path_point in path)) for p in region.perimeter_points),
                key=lambda x: x[1],
                default=(None, float('inf'))
            )[0]
            
            if best_point:
                ingress_points.append(best_point)
    
    # Filter and merge nearby points
    filtered = [p for p in ingress_points if cy_distance_to_squared(p, ai.main_base_ramp.top_center) > 5**2]
    
    merged = []
    used = set()
    for p in filtered:
        if id(p) in used:
            continue
        
        cluster = [p] + [other for other in filtered 
                         if id(other) not in used and other != p and p.distance_to(other) < 2.5]
        for point in cluster[1:]:
            used.add(id(point))
        
        avg_pos = Point2((sum(pt.x for pt in cluster) / len(cluster), 
                          sum(pt.y for pt in cluster) / len(cluster)))
        merged.append(avg_pos)
        used.add(id(p))
    
    return sorted(merged, key=lambda p: p.distance_to(ai.main_base_ramp.top_center), reverse=True)

def remove_illegal_positions(ai: AresBot) -> None:
    from ares.consts import BuildingSize

    resource_fields = ai.mineral_field.closer_than(15, ai.start_location) + ai.vespene_geyser.closer_than(15, ai.start_location)
    exclusion_zones = [r.position.towards(ai.start_location, 3) for r in resource_fields]

    illegal_positions = []
    for size_grp, positions in ai.mediator.get_placements_dict[ai.start_location].items():
        if size_grp == BuildingSize.FIVE_BY_FIVE:
            continue
        for position, attribut in positions.items():
            if any([position.distance_to(ex) < 3 for ex in exclusion_zones]):
                illegal_positions.append(position)

    ## Remove illegal positions from placements dict
    for pos in illegal_positions:
        for size_grp, positions in ai.mediator.get_placements_dict[ai.start_location].items():
            if pos in positions:
                del positions[pos]

def convert_3X3_to_5X5(ai: AresBot) -> None:
    from ares.consts import BuildingSize

    positions_3x3 = ai.mediator.get_placements_dict[ai.start_location][BuildingSize.THREE_BY_THREE]
    positions_5x5 = ai.mediator.get_placements_dict[ai.start_location].get(BuildingSize.FIVE_BY_FIVE, {})
    
    resource_fields = ai.mineral_field.closer_than(15, ai.start_location) + ai.vespene_geyser.closer_than(15, ai.start_location)
    
    def is_vertically_stacked(pos_a: Point2, pos_b: Point2) -> bool:
        return abs(pos_a.x - pos_b.x) < 0.1 and abs(abs(pos_a.y - pos_b.y) - 3) < 0.1
    
    def min_distance_to_resources(pos: Point2) -> float:
        if not resource_fields:
            return float('inf')
        return min(pos.distance_to(r.position) for r in resource_fields)
    
    # Find stacked 3x3 pair farthest from resources
    positions_list = list(positions_3x3.items())
    best_pair = max(
        ((pos1, pos2, attr) for i, (pos1, attr) in enumerate(positions_list)
         for pos2, _ in positions_list[i+1:] if is_vertically_stacked(pos1, pos2)),
        key=lambda x: min_distance_to_resources(Point2((x[0].x + 1, x[0].y + 1))),
        default=None
    )
    
    if best_pair:
        # Convert the best pair to a 5x5 position
        pos1, pos2, attr = best_pair
        new_pos = Point2((pos1.x + 1, pos1.y + 1))
        positions_5x5[new_pos] = attr
        del positions_3x3[pos1]
        del positions_3x3[pos2]
    
    ai.mediator.get_placements_dict[ai.start_location][BuildingSize.FIVE_BY_FIVE] = positions_5x5

def show_placements(ai: AresBot, location: Point2) -> None:
    from ares.consts import BuildingSize
    from sc2.position import Point3

    for size_grp, positions in ai.mediator.get_placements_dict[location].items():
        for position, attribut in positions.items():

            z = ai.get_terrain_z_height(position)
            size = {BuildingSize.TWO_BY_TWO: 2, BuildingSize.THREE_BY_THREE: 3, BuildingSize.FIVE_BY_FIVE: 5}[size_grp]
            p1 = Point3((position.x - size / 2, position.y - size / 2, z + 0.1))
            p2 = Point3((position.x + size / 2, position.y + size / 2, z + 0.1))

            color = (0, 255, 0) if attribut['available'] else (255, 0, 0)
            ai.client.debug_box_out(p1, p2, color=color)
