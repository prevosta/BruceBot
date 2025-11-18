from dataclasses import dataclass

from ares import AresBot
from ares.behaviors.combat.individual import CombatIndividualBehavior
from ares.managers.manager_mediator import ManagerMediator
from cython_extensions import cy_distance_to_squared
from sc2.position import Point2
from sc2.unit import Unit


@dataclass
class BattleCruiserPatrol(CombatIndividualBehavior):
    """Manages patrol behavior for a single BattleCruiser unit."""

    unit: Unit
    staging_position: Point2

    def execute(self, ai: AresBot, config: dict, mediator: ManagerMediator) -> bool:
        waypoints = self._get_waypoints(ai, mediator)
        waypoint_index = self._get_waypoint_index(ai) % len(waypoints)

        # Skip retreat waypoint if healthy
        if (waypoint_index == len(waypoints) - 2) and (self.unit.health_percentage > 0.60):
            waypoint_index = 2

        # Retreat to last waypoint if low health
        if waypoint_index in [1, 2] and (self.unit.health_percentage < 0.40):
            waypoint_index = len(waypoints) - 1

        # Advance waypoint if close enough
        if cy_distance_to_squared(self.unit.position, waypoints[waypoint_index]) < 5**2:
            waypoint_index = (waypoint_index + 1) % len(waypoints)
            self._set_waypoint_index(ai, waypoint_index)

        # Move to waypoint
        if not self.unit.is_moving:
            self.unit.move(waypoints[waypoint_index])
            return True

        return False

    def _get_waypoint_index(self, ai: AresBot) -> int:
        patrol_indexes = getattr(ai, '_bc_patrol_indexes', {})
        return patrol_indexes.get(self.unit.tag, 0)

    def _set_waypoint_index(self, ai: AresBot, index: int) -> None:
        patrol_indexes = getattr(ai, '_bc_patrol_indexes', {})
        patrol_indexes[self.unit.tag] = index
        setattr(ai, '_bc_patrol_indexes', patrol_indexes)

    def _get_waypoints(self, ai: AresBot, mediator: ManagerMediator) -> list[Point2]:
        waypoints = getattr(ai, '_bc_waypoints', {})

        if self.unit.tag not in waypoints:
            def center_resources(loc: Point2) -> Point2:
                resources = (ai.mineral_field + ai.vespene_geyser).filter(lambda m: cy_distance_to_squared(m.position, loc) < 14**2)
                return Point2(loc.towards(resources.center, 5)) if resources.exists else loc

            p0 = self.staging_position  # staging point
            p2 = center_resources(ai.enemy_start_locations[0])  # main mineral line
            p4 = center_resources(mediator.get_enemy_nat)  # natural mineral line

            # Correct ordering
            if cy_distance_to_squared(p0, p2) > cy_distance_to_squared(p0, p4):
                p2, p4 = p4, p2

            p1 = (p0 + p2) / 2  # midpoint to main mineral line
            p3 = (p2 + p4) / 2  # midpoint to natural mineral line

            # Fix ingress from edge (p1, p3)
            import numpy as np
            air_grid = mediator.get_air_grid != np.inf
            min_y, max_y = np.where(air_grid.any(axis=0))[0][[0, -1]]
            min_x, max_x = np.where(air_grid.any(axis=1))[0][[0, -1]]

            dx, dy = min(p1.x - min_x, max_x - p1.x), min(p1.y - min_y, max_y - p1.y)
            p1 = Point2((min_x + 1 if p1.x - min_x < max_x - p1.x else max_x - 1, p1.y)) if dx <= dy else Point2((p1.x, min_y + 1 if p1.y - min_y < max_y - p1.y else max_y - 1))
            dx, dy = min(p3.x - min_x, max_x - p3.x), min(p3.y - min_y, max_y - p3.y)
            p3 = Point2((min_x + 1 if p3.x - min_x < max_x - p3.x else max_x - 1, p3.y)) if dx <= dy else Point2((p3.x, min_y + 1 if p3.y - min_y < max_y - p3.y else max_y - 1))

            # there and back patrol
            waypoints[self.unit.tag] = [p0, p1, p2, p3, p4, p3, p2, p1]
            setattr(ai, '_bc_waypoints', waypoints)

            # set index at the closest waypoint
            closest_index = min(range(len(waypoints[self.unit.tag])),
                                key=lambda i: cy_distance_to_squared(self.unit.position, waypoints[self.unit.tag][i]))
            self._set_waypoint_index(ai, closest_index)

        return waypoints[self.unit.tag]
