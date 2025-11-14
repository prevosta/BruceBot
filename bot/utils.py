from cython_extensions import cy_distance_to_squared

from sc2.position import Point2
from sc2.ids.unit_typeid import UnitTypeId

from ares import AresBot
from ares.behaviors.combat.individual.siege_tank_decision import STATIC_DEFENCE
from ares.consts import BuildingSize
from ares.dicts.structure_to_building_size import STRUCTURE_TO_BUILDING_SIZE


def remove_illegal_positions(ai: AresBot) -> None:
    resource_fields = ai.mineral_field.closer_than(15, ai.start_location) + ai.vespene_geyser.closer_than(15, ai.start_location)
    exclusion_zones = [r.position.towards(ai.start_location, 3) for r in resource_fields]

    illegal_positions = []
    for size_grp, positions in ai.mediator.get_placements_dict[ai.start_location].items():
        if size_grp == BuildingSize.FIVE_BY_FIVE:
            continue
        for position, _ in positions.items():
            if any([position.distance_to(ex) < 3 for ex in exclusion_zones]):
                illegal_positions.append((size_grp, position))

    for size_grp, positions in ai.mediator.get_placements_dict[ai.start_location].items():
        for position, attributs in positions.items():
            top_ramp = ai.main_base_ramp.top_center
            if cy_distance_to_squared(position, top_ramp) < 8**2 and not attributs.get('is_wall', False):
                illegal_positions.append((size_grp, position))

    ## Remove illegal positions from placements dict
    for size_grp, position in illegal_positions:
        del ai.mediator.get_placements_dict[ai.start_location][size_grp][position]

def add_placements(ai: AresBot, structure_type: UnitTypeId, location: Point2, near: list[Point2], radius: int = 5, is_wall: bool = False) -> bool:
    positions: list[Point2] = []

    grp_size = STRUCTURE_TO_BUILDING_SIZE[structure_type]
    at = Point2((round(near[0].x), round(near[0].y)))
    if grp_size != BuildingSize.TWO_BY_TWO:
        at += Point2((0.5, 0.5))

    # All nearby positions within region and radius
    region = ai.mediator.get_map_data_object.where(location)
    for x in range(-radius, radius + 1):
        for y in range(-radius, radius + 1):
            pos = Point2((at.x + x, at.y + y))
            if region.is_inside_point(pos):
                positions.append(pos)

    # Check placement legality
    can_places = [can_place_structure(ai, location, structure_type, p) for p in positions]
    positions = [pos for pos, can_place in zip(positions, can_places) if can_place]
  
    # Get closest position
    positions = sorted(positions, key=lambda p: [cy_distance_to_squared(p, x) for x in near])
    position = positions[0] if positions else None

    if position is None:
        return False

    # Add to placements dict
    grp_size = STRUCTURE_TO_BUILDING_SIZE[structure_type ]
    ai.mediator.get_placements_dict[location][grp_size][position] = {
        'available': True, 
        'has_addon': False, 
        'is_wall': is_wall, 
        'building_tag': 0, 
        'worker_on_route': False, 
        'time_requested': 0.0, 
        'production_pylon': False, 
        'bunker': structure_type == UnitTypeId.BUNKER, 
        'optimal_pylon': False,
        'first_pylon': False, 
        'static_defence': structure_type in STATIC_DEFENCE | {UnitTypeId.MISSILETURRET},
    }

    return True

def can_place_structure(ai: AresBot, location: Point2, structure_type: UnitTypeId, at: Point2) -> bool:
    if not ai.mediator.can_place_structure(position=at, structure_type=structure_type):
        return False

    HALF_SIZE = {BuildingSize.TWO_BY_TWO: 1, BuildingSize.THREE_BY_THREE: 1.5, BuildingSize.FIVE_BY_FIVE: 2.5}

    for size_grp, positions in ai.mediator.get_placements_dict[location].items():
        for pos, _ in positions.items():
            request_size = HALF_SIZE[STRUCTURE_TO_BUILDING_SIZE[structure_type]]
            current_size = HALF_SIZE[size_grp]
            if abs(pos.x - at.x) < (request_size + current_size) and abs(pos.y - at.y) < (request_size + current_size):
                return False
            
            if size_grp != BuildingSize.THREE_BY_THREE:
                continue

            addon_position = Point2((pos.x + 2.5, pos.y - 0.5))

            if abs(addon_position.x - at.x) < (request_size + 1) and abs(addon_position.y - at.y) < (request_size + 1):
                return False

    return True

def show_placements(ai: AresBot, location: Point2) -> None:
    from ares.consts import BuildingSize
    from sc2.position import Point3

    for size_grp, positions in ai.mediator.get_placements_dict[location].items():
        for position, attribut in positions.items():

            z = ai.get_terrain_z_height(position)
            size = {BuildingSize.TWO_BY_TWO: 2, BuildingSize.THREE_BY_THREE: 3, BuildingSize.FIVE_BY_FIVE: 5}[size_grp]
            p1 = Point3((position.x - size / 2, position.y - size / 2, z + 0.1))
            p2 = Point3((position.x + size / 2, position.y + size / 2, z + 0.1))

            color = (0, 0, 255) if attribut['bunker'] or attribut['static_defence'] else (0, 255, 0)
            color = color if attribut['available'] else (255, 0, 0)
            ai.client.debug_box_out(p1, p2, color=color)

    # Add-on placements
    for size_grp, positions in ai.mediator.get_placements_dict[location].items():
        for position, attribut in positions.items():
            if size_grp == BuildingSize.THREE_BY_THREE and not attribut.get('static_defence', False):
                addon_position = Point2((position.x + 2.5, position.y - 0.5))

                z = ai.get_terrain_z_height(position)
                p1 = Point3((addon_position.x - 1, addon_position.y - 1, z + 0.1))
                p2 = Point3((addon_position.x + 1, addon_position.y + 1, z + 0.1))

                color = (255, 0, 0) if attribut['has_addon'] or not attribut['available'] else (0, 255, 0)
                ai.client.debug_box_out(p1, p2, color=color)
