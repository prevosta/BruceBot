from dataclasses import dataclass

from sc2.ids.unit_typeid import UnitTypeId

from ares import AresBot
from ares.consts import BUILDS
from ares.managers.manager_mediator import ManagerMediator
from ares.behaviors.combat.group.combat_group_behavior import CombatGroupBehavior


@dataclass
class ArmyComposition(CombatGroupBehavior):
    """Defines the desired army composition at a given time (using config)."""

    def execute(self, ai: AresBot, config: dict, mediator: ManagerMediator) -> bool:
        army_composition = config[BUILDS][ai.build_order_runner.chosen_opening].get("ArmyComposition")

        if not army_composition:
            return False

        UNIT_STRUCT = {
            UnitTypeId.MARINE: UnitTypeId.BARRACKS,
            UnitTypeId.REAPER: UnitTypeId.BARRACKS,
            UnitTypeId.MARAUDER: UnitTypeId.BARRACKS,
            UnitTypeId.HELLION: UnitTypeId.FACTORY,
            UnitTypeId.SIEGETANK: UnitTypeId.FACTORY,
            UnitTypeId.THOR: UnitTypeId.FACTORY,
            UnitTypeId.VIKINGFIGHTER: UnitTypeId.STARPORT,
            UnitTypeId.BATTLECRUISER: UnitTypeId.STARPORT,
        }
        MORPH_UNITS = {
            UnitTypeId.SIEGETANK: UnitTypeId.SIEGETANKSIEGED,
        }

        for army_unit in army_composition:
            unit_type, count = army_unit.split(" ")
            unit_type = UnitTypeId[unit_type.upper()]
            target_count = int(count)
            
            # Count current units and pending units
            unit_count = ai.units(MORPH_UNITS.get(unit_type, unit_type)).amount
            unit_count += ai.already_pending(MORPH_UNITS.get(unit_type, unit_type))

            # Only train if below target and can afford
            if unit_count < target_count and ai.can_afford(unit_type):
                units_needed = target_count - unit_count
                
                for structure in ai.structures(UNIT_STRUCT[unit_type]).idle:
                    if units_needed <= 0:
                        break
                    structure.train(unit_type)
                    units_needed -= 1

        return True
