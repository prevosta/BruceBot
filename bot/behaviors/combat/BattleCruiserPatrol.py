from dataclasses import dataclass

from ares import AresBot
from ares.behaviors.combat.individual import CombatIndividualBehavior
from ares.managers.manager_mediator import ManagerMediator
from cython_extensions import cy_distance_to_squared
from sc2.position import Point2, Point3
from sc2.unit import Unit


@dataclass
class BattleCruiserPatrol(CombatIndividualBehavior):
    """Manages patrol behavior for a single BattleCruiser unit."""

    unit: Unit

    def execute(self, ai: AresBot, config: dict, mediator: ManagerMediator) -> bool:
        waypoint_index = self._get_waypoint_index(ai)
        waypoints = self._get_waypoints(ai, mediator)

        for i, wp in enumerate(waypoints):
            z = ai.get_terrain_z_height(wp)
            ai.client.debug_text_3d(f"WP{i}", Point3((wp.x, wp.y, z+.5)), size=12, color=(0, 255, 0) if i == waypoint_index else (255, 255, 255))

        if cy_distance_to_squared(self.unit.position, waypoints[waypoint_index]) < 3**2:
            waypoint_index = (waypoint_index + 1) % len(waypoints)
            self._set_waypoint_index(ai, waypoint_index)

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
            loc1 = ai.enemy_start_locations[0]
            minerals = ai.mineral_field.filter(lambda m: cy_distance_to_squared(m.position, loc1) < 12**2)
            dist = [(a.position, b.position, cy_distance_to_squared(a.position, b.position)) for a in minerals for b in minerals if a.tag != b.tag]
            a, b, _ = sorted(dist, key=lambda x: x[2])[-1]
            p1 = Point2(a.towards(b, -3))
            p2 = Point2(b.towards(a, -3))

            loc2 = mediator.get_enemy_nat
            minerals = ai.mineral_field.filter(lambda m: cy_distance_to_squared(m.position, loc2) < 12**2)
            dist = [(a.position, b.position, cy_distance_to_squared(a.position, b.position)) for a in minerals for b in minerals if a.tag != b.tag]
            a, b, _ = sorted(dist, key=lambda x: x[2])[-1]
            p3 = Point2(a.towards(b, -3))
            p4 = Point2(b.towards(a, -3))

            # Correct ordering
            if cy_distance_to_squared(p1, p3) < cy_distance_to_squared(p2, p3):
                p1, p2 = p2, p1
            if cy_distance_to_squared(p3, p1) > cy_distance_to_squared(p4, p1):
                p3, p4 = p4, p3

            # there and back patrol
            waypoints[self.unit.tag] = [p1, p2, p3, p4, p3, p2]
            setattr(ai, '_bc_waypoints', waypoints)

            # set index at the closest waypoint
            closest_index = min(range(len(waypoints[self.unit.tag])),
                                key=lambda i: cy_distance_to_squared(self.unit.position, waypoints[self.unit.tag][i]))
            self._set_waypoint_index(ai, closest_index)

        return waypoints[self.unit.tag]
