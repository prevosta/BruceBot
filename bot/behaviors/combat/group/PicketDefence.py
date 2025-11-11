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

    def execute(self, ai: AresBot, config: dict, mediator) -> bool:

        # Get all Marine units
        combat_units = ai.units.filter(lambda u: u.type_id == UnitTypeId.MARINE)
        
        if not combat_units.exists:
            return False
        
        # Assign closest unassigned unit to each picket to minimize switching
        # Keep similar amount of units at each picket
        
        assigned_tags = set()
        units_list = list(combat_units)
        
        # Calculate units per picket
        units_per_picket = len(units_list) // len(self.pickets)
        extra_units = len(units_list) % len(self.pickets)
        
        # Assign units to pickets
        for picket_idx, picket in enumerate(self.pickets):
            # Determine how many units this picket should get
            target_count = units_per_picket + (1 if picket_idx < extra_units else 0)
            
            for _ in range(target_count):
                # Find unassigned units
                unassigned = [u for u in units_list if u.tag not in assigned_tags]
                if not unassigned:
                    break
                
                # Get closest unassigned unit to this picket
                closest_unit = min(unassigned, key=lambda u: u.distance_to(picket))
                assigned_tags.add(closest_unit.tag)
                
                # Move if not already at the picket
                if cy_distance_to_squared(closest_unit.position, picket) > 1**2:
                    closest_unit.move(picket)

        return True


def generate_pickets(ai: AresBot) -> list[Point2]:
    """Generate picket positions around the main base ramp and climber ingress points."""

    ingress_points = [Point2((ai.main_base_ramp.top_center.towards(ai.start_location, 4)))]
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

    merged = []
    used = set()
    for p in ingress_points:
        if id(p) in used:
            continue
        
        cluster = [p] + [other for other in ingress_points 
                        if id(other) not in used and other != p and p.distance_to(other) < 2.5]
        for point in cluster[1:]:
            used.add(id(point))
        
        avg_pos = Point2((sum(pt.x for pt in cluster) / len(cluster), 
                        sum(pt.y for pt in cluster) / len(cluster)))
        merged.append(avg_pos)
        used.add(id(p))
    
    return sorted(merged, key=lambda p: p.distance_to(ai.main_base_ramp.top_center), reverse=True)
