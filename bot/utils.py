from sc2.position import Point2

from ares import AresBot


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
