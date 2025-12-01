from dataclasses import dataclass

from ares import AresBot
from ares.behaviors.combat.group.combat_group_behavior import CombatGroupBehavior
from ares.consts import BUILDS
from ares.managers.manager_mediator import ManagerMediator
from sc2.ids.unit_typeid import UnitTypeId


ARMY_COMPOSITION: str = "ArmyComposition"
AUTO_ARMY_AT_TIME: str = "AutoArmyAtTime"
AUTO_ARMY_AT_SUPPLY: str = "AutoArmyAtSupply"

@dataclass
class ArmyComposition(CombatGroupBehavior):
    """Defines the desired army composition at a given time (using config)."""

    def execute(self, ai: AresBot, config: dict, mediator: ManagerMediator) -> bool:
        army_composition = config.get(BUILDS, {}).get(ai.build_order_runner.chosen_opening, {}).get(ARMY_COMPOSITION)
        auto_army_at_time = config.get(BUILDS, {}).get(ai.build_order_runner.chosen_opening, {}).get(AUTO_ARMY_AT_TIME, None)
        auto_army_at_supply = config.get(BUILDS, {}).get(ai.build_order_runner.chosen_opening, {}).get(AUTO_ARMY_AT_SUPPLY, None)

        if not army_composition:
            return False
        
        if auto_army_at_time and ai.time < auto_army_at_time:
            return False
        
        if auto_army_at_supply and ai.supply_army < auto_army_at_supply:
            return False

        UNIT_STRUCT = {
            UnitTypeId.MARINE: UnitTypeId.BARRACKS,
            UnitTypeId.REAPER: UnitTypeId.BARRACKS,
            UnitTypeId.MARAUDER: UnitTypeId.BARRACKS,
            UnitTypeId.GHOST: UnitTypeId.BARRACKS,
            UnitTypeId.HELLION: UnitTypeId.FACTORY,
            UnitTypeId.SIEGETANK: UnitTypeId.FACTORY,
            UnitTypeId.THOR: UnitTypeId.FACTORY,
            UnitTypeId.WIDOWMINE: UnitTypeId.FACTORY,
            UnitTypeId.CYCLONE: UnitTypeId.FACTORY,
            UnitTypeId.VIKINGFIGHTER: UnitTypeId.STARPORT,
            UnitTypeId.BATTLECRUISER: UnitTypeId.STARPORT,
            UnitTypeId.LIBERATOR: UnitTypeId.STARPORT,
            UnitTypeId.RAVEN: UnitTypeId.STARPORT,
            UnitTypeId.BANSHEE: UnitTypeId.STARPORT,
            UnitTypeId.MEDIVAC: UnitTypeId.STARPORT,
        }
        MORPH_UNITS = {
            UnitTypeId.SIEGETANK: {UnitTypeId.SIEGETANK, UnitTypeId.SIEGETANKSIEGED},
            UnitTypeId.VIKINGFIGHTER: {UnitTypeId.VIKINGFIGHTER, UnitTypeId.VIKINGASSAULT},
            UnitTypeId.LIBERATOR: {UnitTypeId.LIBERATOR, UnitTypeId.LIBERATORAG},
        }

        for army_unit in army_composition:
            unit_type, count = army_unit.split(" ")
            unit_type = UnitTypeId[unit_type.upper()]
            target_count = int(count)

            # Count current units and pending units
            unit_count = ai.units(MORPH_UNITS.get(unit_type, unit_type)).amount
            unit_count += ai.already_pending(unit_type)

            # Only train if below target and can afford
            if unit_count < target_count and ai.can_afford(unit_type):
                for structure in ai.structures(UNIT_STRUCT[unit_type]).idle:
                    structure.train(unit_type)
                    return True

        return False
