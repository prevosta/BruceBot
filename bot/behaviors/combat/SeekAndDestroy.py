from dataclasses import dataclass
from random import uniform

from sc2.position import Point2

from ares import AresBot
from ares.consts import WORKER_TYPES
from ares.behaviors.combat.group import CombatGroupBehavior


@dataclass
class SeekAndDestroy(CombatGroupBehavior):
    """Attack enemy units/structures when all enemy townhalls are destroyed."""

    def execute(self, ai: AresBot, config: dict, mediator) -> bool:

        # Get all non-worker units
        combat_units = ai.units.filter(lambda u: u.type_id not in WORKER_TYPES)
        
        if not combat_units.exists:
            return False
        
        enemy_targets = ai.enemy_units | ai.enemy_structures
        
        for unit in combat_units:
            if enemy_targets.exists:
                # Attack closest enemy
                unit.attack(enemy_targets.closest_to(unit))

            elif not unit.is_moving:
                # Hunt randomly across the map
                random_pos = Point2((
                    uniform(0, ai.game_info.map_size.x),
                    uniform(0, ai.game_info.map_size.y)
                ))
                unit.move(random_pos)

        return True
