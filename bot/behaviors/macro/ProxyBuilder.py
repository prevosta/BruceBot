from __future__ import annotations
from dataclasses import dataclass

from cython_extensions import cy_distance_to_squared

from sc2.position import Point2

from ares import AresBot
from ares.consts import BUILDS, TARGET, UnitRole
from ares.managers.manager_mediator import ManagerMediator
from ares.behaviors.combat.group import CombatGroupBehavior


PROXYBUILDER: str = "ProxyBuilder"

@dataclass
class ProxyBuilder(CombatGroupBehavior):
    """Behavior to send a worker to build a proxy structure at a specified location (via config)."""

    def execute(self, ai: AresBot, config: dict, mediator: ManagerMediator) -> bool:
        # Retrieve proxy build orders from config
        opening_name = ai.build_order_runner.chosen_opening
        proxy_actions = config[BUILDS][opening_name][PROXYBUILDER]
        proxy_workers = mediator.get_units_from_role(role=UnitRole.PROXY_WORKER).filter(lambda u: not u.is_constructing_scv)

        for order in proxy_actions:
            iteration, where = order.split(" ")[:2]
            iteration = int(iteration)
            where = ai.build_order_runner._get_target(where.upper().strip())
            if iteration == ai.actual_iteration:
                if worker := mediator.select_worker(target_position=where):
                    mediator.clear_role(tag=worker.tag)
                    mediator.assign_role(tag=worker.tag, role=UnitRole.IDLE)
                    mediator.remove_worker_from_mineral(worker_tag=worker.tag)
                    worker.move(where)

                    return True

        # Reassign idle workers that are close to their target to proxy worker role
        for worker in mediator.get_units_from_role(role=UnitRole.IDLE):
            if worker.is_moving and worker.orders and cy_distance_to_squared(worker.position, worker.orders[0].target) < 25**2:
                mediator.clear_role(tag=worker.tag)
                mediator.assign_role(tag=worker.tag, role=UnitRole.PROXY_WORKER)

        if not proxy_workers:
            return False

        # Force usage of proxy workers if closer to the build location
        building_tracker: dict = mediator.get_building_tracker_dict
        for worker_tag in building_tracker:
            worker = ai.units.find_by_tag(worker_tag)

            if not worker or worker.tag in set(pw.tag for pw in proxy_workers) or worker.is_constructing_scv:
                continue

            target = building_tracker[worker_tag][TARGET].position
 
            if not isinstance(target, Point2):
                continue

            dist = cy_distance_to_squared(worker.position, target)
            for proxy_worker in proxy_workers:
                if cy_distance_to_squared(proxy_worker.position, target) < dist:
                    building_tracker[proxy_worker.tag] = building_tracker.pop(worker.tag)
                    proxy_worker.stop()

                    mediator.clear_role(tag=worker.tag)
                    mediator.assign_role(tag=worker.tag, role=UnitRole.GATHERING)
                    proxy_worker.stop()

                    return True

        return False