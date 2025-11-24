from dataclasses import dataclass
import json
from loguru import logger

from ares import AresBot
from ares.behaviors.combat.group import CombatGroupBehavior
from ares.consts import BUILDS, TARGET, ID, UnitRole, BuildingSize
from ares.managers.manager_mediator import ManagerMediator
from cython_extensions import cy_distance_to, cy_distance_to_squared
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2, Point3

PROXYBUILDER: str = "ProxyBuilder"
DEFAULT_PROXY = {
    "Torches AIE": [[58.5, 39.5], [53.5, 42.5], [59.5, 169.5], [54.5, 166.5]],
    "Ultralove AIE": [[145.5, 92.5], [152.5, 70.5], [36.5,  92.5], [38.5, 117.5]],
    "Persephone AIE": [[20.5, 118.5], [20.5,115.5], [20.5, 57.5], [22.5, 68.5]],
    "Pylon AIE": [[64.5, 136.5], [64.5, 133.5], [185.5, 130.5], [179.5, 134.5]],
    "Ley Lines AIE": [[84.5, 35.5], [89.5, 32.5], [111.5, 139.5], [101.5, 142.5]],
    "Magannatha AIE": [[81.5, 151.5], [146.5,  76.5], [145.5, 95.5]],
}


@dataclass
class ProxyBuilder(CombatGroupBehavior):
    """Behavior to send a worker to build a proxy structure at a specified location (via config)."""

    proxy_locations: list[Point2]

    def execute(self, ai: AresBot, config: dict, mediator: ManagerMediator) -> bool:
        if not self.proxy_locations:
            return False

        # Retrieve proxy build orders from config
        opening_name = ai.build_order_runner.chosen_opening
        proxy_actions = config[BUILDS][opening_name].get(PROXYBUILDER, [])

        # Issue proxy build orders at specified iterations
        for order in proxy_actions:
            iteration = order.split(" ")[0]
            if int(iteration) == ai.actual_iteration:
                where = self.proxy_locations[0]
                if worker := mediator.select_worker(target_position=where):
                    mediator.clear_role(tag=worker.tag)
                    mediator.assign_role(tag=worker.tag, role=UnitRole.PROXY_WORKER)
                    mediator.remove_worker_from_mineral(worker_tag=worker.tag)
                    worker.move(where)

                    return True

        # Retrieve proxy workers
        proxy_workers = mediator.get_units_from_role(role=UnitRole.PROXY_WORKER).filter(lambda u: not u.is_constructing_scv)
        if not proxy_workers:
            return False

        # Force usage of proxy workers if closer to the build location
        building_tracker: dict = mediator.get_building_tracker_dict
        for worker_tag in building_tracker:
            worker = ai.units.find_by_tag(worker_tag)
            if not worker or worker.tag in set(pw.tag for pw in proxy_workers) or worker.is_constructing_scv:
                continue

            if building_tracker[worker_tag][TARGET] is None:
                continue

            target = building_tracker[worker_tag][TARGET].position
            if not isinstance(target, Point2):
                continue

            structure_type = building_tracker[worker_tag][ID]
            actions_types = [UnitTypeId[x.split(" ")[1]] if x.split(" ")[1].upper() in UnitTypeId._member_map_ else None for x in proxy_actions ]
            if structure_type not in actions_types:
                continue

            dist = cy_distance_to_squared(worker.position, target)
            for proxy_worker in proxy_workers:
                if cy_distance_to_squared(proxy_worker.position, target) < dist:
                    task = building_tracker.pop(worker.tag)
                    task[TARGET] = self.proxy_locations[0]
                    building_tracker[proxy_worker.tag] = task
                    proxy_worker.stop()

                    mediator.clear_role(tag=worker.tag)
                    mediator.assign_role(tag=worker.tag, role=UnitRole.GATHERING)
                    proxy_worker.stop()

                    logger.info(f"ProxyBuilder: {structure_type.name if structure_type else 'Unknown'}")

                    return True

        return False
    
    class MapInfo:
        """Class to store map-related information for proxy building."""
        ground_min_x: int
        ground_max_x: int
        ground_min_y: int
        ground_max_y: int
        air_min_x: int
        air_max_x: int
        air_min_y: int
        air_max_y: int
        ground_edge_points: set[Point2] = set()
        air_edge_points: set[Point2] = set()
        proxy_locations: list[tuple[Point2, float]] = []
        buildable_locations: dict[Point2, list[Point2]] = {}

    @staticmethod
    def compute_map_info(ai: AresBot, mediator: ManagerMediator) -> MapInfo:
        """Compute and store proxy locations in the bot's memory."""

        import numpy as np
        map_info = ProxyBuilder.MapInfo()

        # Try to load from cache
        if cached_info := ProxyBuilder._load_map_info(ai):
            return cached_info

        ground_grid = mediator.get_ground_grid != np.inf
        air_grid = mediator.get_air_grid != np.inf

        # Compute map bounds
        map_info.ground_min_y, map_info.ground_max_y = np.where(ground_grid.any(axis=0))[0][[0, -1]]
        map_info.ground_min_x, map_info.ground_max_x = np.where(ground_grid.any(axis=1))[0][[0, -1]]
        map_info.air_min_y, map_info.air_max_y = np.where(air_grid.any(axis=0))[0][[0, -1]]
        map_info.air_min_x, map_info.air_max_x = np.where(air_grid.any(axis=1))[0][[0, -1]]

        # Compute ground edge points
        for y in range(map_info.ground_min_y, map_info.ground_max_y + 1):
            min_x, max_x = np.where(ground_grid[:, y])[0][[0, -1]]
            map_info.ground_edge_points.add(Point2((min_x + 0.5, y + 0.5)))
            map_info.ground_edge_points.add(Point2((max_x + 0.5, y + 0.5)))
        for x in range(map_info.ground_min_x, map_info.ground_max_x + 1):
            min_y, max_y = np.where(ground_grid[x, :])[0][[0, -1]]
            map_info.ground_edge_points.add(Point2((x + 0.5, min_y + 0.5)))
            map_info.ground_edge_points.add(Point2((x + 0.5, max_y + 0.5)))

        # Compute air edge points
        for y in range(map_info.air_min_y, map_info.air_max_y + 1):
            min_x, max_x = np.where(air_grid[:, y])[0][[0, -1]]
            map_info.air_edge_points.add(Point2((min_x + 0.5, y + 0.5)))
            map_info.air_edge_points.add(Point2((max_x + 0.5, y + 0.5)))
        for x in range(map_info.air_min_x, map_info.air_max_x + 1):
            min_y, max_y = np.where(air_grid[x, :])[0][[0, -1]]
            map_info.air_edge_points.add(Point2((x + 0.5, min_y + 0.5)))
            map_info.air_edge_points.add(Point2((x + 0.5, max_y + 0.5)))

        # Compute best proxy point
        nat_enemy_distance = cy_distance_to(mediator.get_own_nat, ai.enemy_start_locations[0])
        for location, path_distance in mediator.get_enemy_expansions:
            tm = ai.manager_hub.terrain_manager
            if location in [tm.own_nat, tm.own_third, tm.enemy_nat, tm.enemy_third]:
                continue
            air_distance = cy_distance_to(location, ai.enemy_start_locations[0])
            if air_distance > (nat_enemy_distance * 0.8):
                continue
            delta_distance = path_distance - air_distance
            map_info.proxy_locations.append((location, delta_distance))
        map_info.proxy_locations = sorted(map_info.proxy_locations, key=lambda x: x[1], reverse=True)

        # Compute proxy locations for 3x3 Starport placements
        for location, _ in map_info.proxy_locations:

            buildable_locations: set[Point2] = set()
            point_to_check = [p for p in map_info.ground_edge_points if cy_distance_to_squared(p, location) < 15**2]
            region = mediator.get_map_data_object.where(location)
            point_to_check = [p for p in point_to_check if region.is_inside_point(p)]
            min_x, max_x = map_info.ground_min_x, map_info.ground_max_x
            min_y, max_y = map_info.ground_min_y, map_info.ground_max_y
            point_to_check = [p for p in point_to_check if abs(p.x - min_x) < 10 or abs(p.x - max_x) < 10 or abs(p.y - min_y) < 10 or abs(p.y - max_y) < 10]

            for center in point_to_check:
                closest_candidate = None
                closest_distance = float('inf')

                # Check a 2x2 box around the perimeter point
                for x in range(-2, 3):
                    for y in range(-2, 3):
                        # 3x3 buildings should be centered at .5 offsets
                        candidate = Point2((center.x + x, center.y + y))

                        # Check if we can place a Starport (3x3) at this location
                        if ai.mediator.can_place_structure(position=candidate, structure_type=UnitTypeId.STARPORT):
                            addon_position = Point2((candidate.x + 2.5, candidate.y - 0.5))
                            if ai.mediator.can_place_structure(position=addon_position, structure_type=UnitTypeId.SUPPLYDEPOT):
                                distance = cy_distance_to_squared(center, candidate)
                                if distance < closest_distance:
                                    closest_distance = distance
                                    closest_candidate = candidate

                # Add the closest valid placement for this perimeter point
                if closest_candidate and cy_distance_to_squared(closest_candidate, location) >= 9.5**2:
                    buildable_locations.add(closest_candidate)

            if not buildable_locations:
                logger.warning(f"ProxyBuilder: No valid 3x3 Starport placements found near {location}")
                buildable_locations = [p for p in mediator.get_placements_dict.get(location, {}).get(BuildingSize.THREE_BY_THREE, {})]  # type: ignore

            # Sort locations by distance to enemy start location
            sorted_locations = sorted(buildable_locations, key=lambda p: cy_distance_to_squared(p, ai.enemy_start_locations[0]))

            # Remove any locations that are too close to each other (within 3 units)
            final_locations: list[Point2] = []
            for a in sorted_locations:
                if not any(cy_distance_to_squared(a, b) < 3**2 for b in final_locations):
                    addon_position = Point2((a.x + 2.5, a.y - 0.5))
                    if not any(cy_distance_to_squared(addon_position, b) < 3**2 for b in final_locations):
                        final_locations.append(a)

            map_info.buildable_locations[location] = final_locations

            # save map info in bot memory (data/map_info.json)
            ProxyBuilder._save_map_info(ai, map_info)

        return map_info
    
    @staticmethod
    def _load_map_info(ai: AresBot) -> "ProxyBuilder.MapInfo | None":
        """Load map info from file if it exists."""
        import os
        os.makedirs("data", exist_ok=True)
        
        try:
            with open("data/map_info.json", "r") as f:
                map_infos = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return None

        if not map_infos or ai.game_info.map_name not in map_infos:
            return None
        
        start_location_key = str(ai.start_location)
        if start_location_key not in map_infos[ai.game_info.map_name]:
            return None

        info = map_infos[ai.game_info.map_name][start_location_key]
        map_info = ProxyBuilder.MapInfo()
        map_info.ground_min_x = info["ground_min_x"]
        map_info.ground_max_x = info["ground_max_x"]
        map_info.ground_min_y = info["ground_min_y"]
        map_info.ground_max_y = info["ground_max_y"]
        map_info.air_min_x = info["air_min_x"]
        map_info.air_max_x = info["air_max_x"]
        map_info.air_min_y = info["air_min_y"]
        map_info.air_max_y = info["air_max_y"]
        map_info.proxy_locations = [(Point2((p[0], p[1])), p[2]) for p in info["proxy_locations"]]
        map_info.buildable_locations = {
            Point2((float(loc.split(",")[0][1:]), float(loc.split(",")[1][:-1]))): [Point2((p[0], p[1])) for p in locs]
            for loc, locs in info["buildable_locations"].items()
        }
        return map_info

    @staticmethod
    def _save_map_info(ai: AresBot, map_info: "ProxyBuilder.MapInfo") -> None:
        """Save map info to file."""
        import os
        os.makedirs("data", exist_ok=True)
        
        try:
            with open("data/map_info.json", "r") as f:
                map_infos = json.load(f)
        except FileNotFoundError:
            map_infos = {}

        if ai.game_info.map_name not in map_infos:
            map_infos[ai.game_info.map_name] = {}

        map_infos[ai.game_info.map_name][str(ai.start_location)] = {
            "ground_min_x": int(map_info.ground_min_x),
            "ground_max_x": int(map_info.ground_max_x),
            "ground_min_y": int(map_info.ground_min_y),
            "ground_max_y": int(map_info.ground_max_y),
            "air_min_x": int(map_info.air_min_x),
            "air_max_x": int(map_info.air_max_x),
            "air_min_y": int(map_info.air_min_y),
            "air_max_y": int(map_info.air_max_y),
            "proxy_locations": [(p.x, p.y, float(d)) for p, d in map_info.proxy_locations],
            "buildable_locations": {
                f"({loc.x},{loc.y})": [(p.x, p.y) for p in locs]
                for loc, locs in map_info.buildable_locations.items()
            }
        }
        
        with open("data/map_info.json", "w") as f:
            json.dump(map_infos, f, indent=4)

    @staticmethod
    def get_proxy_locations(ai: AresBot) -> list[Point2]:
        """Retrieve predefined proxy locations for the current map."""

        map_name = ai.game_info.map_name
        proxy_locations = DEFAULT_PROXY.get(map_name, [])

        if not proxy_locations:
            print("Old way of computing proxy locations...")
            map_info = ProxyBuilder.compute_map_info(ai, ai.mediator)
            return map_info.buildable_locations[map_info.proxy_locations[0][0]]

        def filter_locations(loc: Point2) -> bool:
            return cy_distance_to_squared(loc, ai.enemy_start_locations[0]) < cy_distance_to_squared(loc, ai.start_location)

        proxy_locations = [Point2((loc[0], loc[1])) for loc in proxy_locations]

        return list(filter(filter_locations, proxy_locations))

    @staticmethod
    def show_proxy_locations(ai: AresBot) -> None:
        """Visualize the 3x3 Starport placements."""

        proxy_locations = ProxyBuilder.get_proxy_locations(ai)

        for i, p in enumerate(proxy_locations):
            z = ai.get_terrain_z_height(p)
            p1 = Point3((p.x - 1.5, p.y - 1.5, z + 0.1))
            p2 = Point3((p.x + 1.5, p.y + 1.5, z + 0.1))
            ai.client.debug_box_out(p1, p2, color=(0, 255, 0) if i == 0 else (255, 255, 0))
            ai.client.debug_text_3d(f"{i} [{p.x},{p.y}]", Point3((p.x, p.y, z + 0.2)), size=12, color=(255, 255, 0))
