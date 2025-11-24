from dataclasses import dataclass

from ares import AresBot
from ares.behaviors.combat.group import CombatGroupBehavior
from ares.consts import TOWNHALL_TYPES
from ares.managers.manager_mediator import ManagerMediator
from cython_extensions import cy_distance_to_squared
from sc2.ids.unit_typeid import UnitTypeId


@dataclass
class ArmyAttack(CombatGroupBehavior):
    """Manages BattleCruisers in combat."""

    army_types: set[UnitTypeId] | UnitTypeId | None = None

    def execute(self, ai: AresBot, config: dict, mediator: ManagerMediator) -> bool:
        army = ai.units(self.army_types)

        # Wait until army is available
        if not army.exists:
            return True  

        # Attack until main townhall is destroyed
        if army.filter(lambda u: cy_distance_to_squared(u.position, ai.enemy_start_locations[0]) < 10**2).exists:
            if ai.enemy_structures(TOWNHALL_TYPES).filter(lambda u: cy_distance_to_squared(u.position, ai.enemy_start_locations[0]) < 3**2).exists:
                setattr(ai, '_enemy_main_destroy', False)
                return True
            setattr(ai, '_enemy_main_destroy', True)

        # Attack until natural townhall is destroyed
        if army.filter(lambda u: cy_distance_to_squared(u.position, mediator.get_enemy_nat) < 10**2).exists:
            if ai.enemy_structures(TOWNHALL_TYPES).filter(lambda u: cy_distance_to_squared(u.position, mediator.get_enemy_nat) < 3**2).exists:
                setattr(ai, '_enemy_nat_destroy', False)
                return True 
            setattr(ai, '_enemy_nat_destroy', True)

        # Attack until main and natural are seen and destroyed
        if getattr(ai, '_enemy_main_destroy', False) and getattr(ai, '_enemy_nat_destroy', False):
            return False

        return True
