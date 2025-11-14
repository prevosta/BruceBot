from dataclasses import dataclass

from sc2.ids.unit_typeid import UnitTypeId

from ares import AresBot
from ares.behaviors.macro.build_structure import BuildStructure
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

            # Too much money, build more production
            if ai.minerals > 500 and ai.time > 6*60:
                BuildStructure(ai.start_location, UnitTypeId.BARRACKS, max_on_route=2).execute(ai, {}, mediator)

            # Count current units and pending units
            unit_count = ai.units(MORPH_UNITS.get(unit_type, unit_type)).amount
            unit_count += ai.already_pending(unit_type)

            # Only train if below target and can afford
            if unit_count < target_count and ai.can_afford(unit_type):
                for structure in ai.structures(UNIT_STRUCT[unit_type]).idle:
                    structure.train(unit_type)
                    return True

        return False
