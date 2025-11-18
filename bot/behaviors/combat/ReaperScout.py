from dataclasses import dataclass

from ares import AresBot
from ares.behaviors.combat.individual import CombatIndividualBehavior
from ares.managers.manager_mediator import ManagerMediator
from cython_extensions import cy_distance_to_squared
from sc2.position import Point2
from sc2.unit import Unit


@dataclass
class ReaperScout(CombatIndividualBehavior):
    """Manages patrol behavior for a single Reaper unit."""

    unit: Unit
    waypoints: list[Point2]

    def execute(self, ai: AresBot, config: dict, mediator: ManagerMediator) -> bool:
        waypoints = self._get_waypoints(ai, mediator)
        waypoint_index = self._get_waypoint_index(ai) % len(waypoints)

        # Advance waypoint if close enough
        if cy_distance_to_squared(self.unit.position, waypoints[waypoint_index]) < 2**2:
            waypoint_index = (waypoint_index + 1) % len(waypoints)
            self._set_waypoint_index(ai, waypoint_index)

        # Move to waypoint
        if not self.unit.is_moving:
            self.unit.move(waypoints[waypoint_index])
            return True

        return False

    def _get_waypoint_index(self, ai: AresBot) -> int:
        patrol_indexes = getattr(ai, '_reaper_patrol_indexes', {})
        return patrol_indexes.get(self.unit.tag, 0)

    def _set_waypoint_index(self, ai: AresBot, index: int) -> None:
        patrol_indexes = getattr(ai, '_reaper_patrol_indexes', {})
        patrol_indexes[self.unit.tag] = index
        setattr(ai, '_reaper_patrol_indexes', patrol_indexes)

    def _get_waypoints(self, ai: AresBot, mediator: ManagerMediator) -> list[Point2]:
        waypoints: dict[int, list[Point2]] = getattr(ai, '_reaper_waypoints', {})

        if self.unit.tag not in waypoints:
            waypoints[self.unit.tag] = self.waypoints
            setattr(ai, '_reaper_waypoints', waypoints)

        return waypoints[self.unit.tag]
