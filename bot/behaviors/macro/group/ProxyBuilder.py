from __future__ import annotations
from dataclasses import dataclass

from cython_extensions import cy_distance_to_squared

from ares import AresBot
from ares.consts import BUILDS, UnitRole
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

        for order in proxy_actions:
            iteration, where = order.split(" ")[:2]
            iteration = int(iteration)
            where = ai.build_order_runner._get_target(where.upper().strip())
            if iteration == ai.actual_iteration:
                if worker := mediator.select_worker(target_position=where):
                    mediator.clear_role(tag=worker.tag)
                    mediator.assign_role(tag=worker.tag, role=UnitRole.PROXY_WORKER)
                    mediator.remove_worker_from_mineral(worker_tag=worker.tag)
                    worker.move(where)

                    return True

        for worker in mediator.get_units_from_role(role=UnitRole.PROXY_WORKER):
            if worker.is_moving and worker.orders and cy_distance_to_squared(worker.position, worker.orders[0].target) < 25**2:
                mediator.clear_role(tag=worker.tag)
                mediator.assign_role(tag=worker.tag, role=UnitRole.PERSISTENT_BUILDER)

        for worker in mediator.get_units_from_role(role=UnitRole.PERSISTENT_BUILDER).filter(lambda w: w.is_constructing_scv):
            mediator.clear_role(tag=worker.tag)
            mediator.assign_role(tag=worker.tag, role=UnitRole.PROXY_WORKER)

        return False