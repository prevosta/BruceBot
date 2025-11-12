from dataclasses import dataclass

from cython_extensions import cy_distance_to_squared

from sc2.position import Point2
from sc2.ids.unit_typeid import UnitTypeId

from ares import AresBot
from ares.behaviors.combat.group import CombatGroupBehavior


@dataclass
class PicketDefence(CombatGroupBehavior):
    """Defend key locations using Marine units."""

    pickets: list[Point2]
    intervaled: int = 25

    def execute(self, ai: AresBot, config: dict, mediator) -> bool:

        if ai.actual_iteration % self.intervaled != 0:
            return False

        # Get all Marine units
        combat_units = ai.units(UnitTypeId.MARINE)
        
        if not combat_units.exists:
            return False
        
        # Compute next best position (least occupied, then by order defined)
        pos_cnt = {pos: sum(1 for unit in combat_units if cy_distance_to_squared(unit.position, pos) <= 1**2) for pos in self.pickets}
        pos_inx = {pos: idx for idx, pos in enumerate(self.pickets)}
        sorted_pos = sorted(self.pickets, key=lambda p: (pos_cnt[p], pos_inx[p]))

        # Only move units if they are not already near a picket position
        free_units = combat_units.filter(lambda u: all(cy_distance_to_squared(u.position, p) > 3**2 for p in self.pickets))

        # if a position as more than 1 units more than the least occupied, add one of it's units to combat_units
        n_least = min(pos_cnt.values())
        for pos in self.pickets:
            if pos_cnt[pos] > n_least + 1:
                for unit in combat_units:
                    if cy_distance_to_squared(unit.position, pos) <= 1**2:
                        free_units.append(unit)
                        break

        for unit in free_units:
            # Proceed to least occupied position
            if cy_distance_to_squared(sorted_pos[0], unit.position) >= 3**2:
                unit.move(sorted_pos[0])

        return True

    @staticmethod
    def generate(ai: AresBot) -> list[Point2]:
        """Generate picket positions around the main base ramp and climber ingress points."""

        region = ai.mediator.get_map_data_object.where(ai.start_location)

        away_locations = []  # [ai.enemy_start_locations[0], ai.mediator.get_own_expansions[0][0], ai.mediator.get_own_expansions[2][0]]
        ingress_points: list[Point2] = []  # [Point2((ai.main_base_ramp.top_center.towards(ai.start_location, 4)))]

        # Position in a circle around start location
        import math
        import numpy as np
        radius = 35
        center = ai.start_location
        for angle in range(0, 360, 10):
            rad = math.radians(angle)
            unit_pos = Point2((center.x + radius * math.cos(rad), center.y + radius * math.sin(rad)))
            if unit_pos.x < 0 or unit_pos.y < 0:
                continue
            if unit_pos.y >= ai.game_info.map_size.y or unit_pos.x >= ai.game_info.map_size.x:
                continue
            if ai.mediator.get_ground_grid[int(unit_pos.x)][int(unit_pos.y)] == np.inf:
                continue
            away_locations.append(unit_pos)

        # Find ingress points from away locations to main base
        for target in away_locations:
            if path := ai.mediator.find_raw_path(start=target, target=ai.start_location, grid=ai.mediator.get_climber_grid, sensitivity=1):
                path = [p for p in path if region.is_inside_point(p)]

                # closest 2 points between each path and perimeter points
                best_point = None
                best_dist = float('inf')
                for perimeter_point in region.perimeter_points:
                    for path_point in path:
                        dist = cy_distance_to_squared(perimeter_point, path_point)
                        if dist >= best_dist:
                            continue
                        best_dist = dist
                        best_point = path_point

                if best_point is None:
                    continue

                ingress_points.append(best_point)

        # Refine ingress points to valid positions
        for pos in ingress_points:
            valid_pos = ai.mediator.find_lowest_cost_points(from_pos=pos, radius=3, grid=ai.mediator.get_ground_grid)
            valid_pos = [p for p in valid_pos if region.is_inside_point(p)]

            if len(valid_pos) == 0:
                continue

            ingress_points.remove(pos)
            ingress_points.append(sorted(valid_pos, key=lambda p: cy_distance_to_squared(p, pos))[0])

        # Move ingress points slightly towards main base
        for i, p in enumerate(ingress_points):
            ingress_points[i] = Point2(p.towards(ai.start_location, 1))

        # Manually set ingress point at ramp
        ingress_points = [p for p in ingress_points if cy_distance_to_squared(p, ai.main_base_ramp.top_center) > 4**2]
        corner_depots = list(ai.main_base_ramp.corner_depots)
        corner_depot = sorted(corner_depots, key=lambda d: cy_distance_to_squared(d.position, ai.start_location))[0]
        ingress_points.append(Point2(corner_depot.position.towards(ai.start_location, 2)))

        # Merge close ingress points (within 2 units) averaging their positions
        merged = []
        used = set()
        for p in ingress_points:
            if id(p) in used:
                continue

            cluster = [p] + [other for other in ingress_points 
                            if id(other) not in used and other != p and p.distance_to(other) < 4.0]
            for point in cluster[1:]:
                used.add(id(point))

            avg_pos = Point2((sum(pt.x for pt in cluster) / len(cluster), sum(pt.y for pt in cluster) / len(cluster)))
            merged.append(avg_pos)
            used.add(id(p))
        ingress_points = merged

        return ingress_points
