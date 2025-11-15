from dataclasses import dataclass
from typing import Callable

from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId
from sc2.ids.upgrade_id import UpgradeId

from ares import AresBot
from ares.consts import BUILDS
from ares.managers.manager_mediator import ManagerMediator
from ares.behaviors.combat.group.combat_group_behavior import CombatGroupBehavior

TECHUPGRADES = "TechUpgrades"
@dataclass
class UpgradeTech(CombatGroupBehavior):
    """Handles upgrading techs based on config."""

    cond: Callable = lambda: True

    def execute(self, ai: AresBot, config: dict, mediator: ManagerMediator) -> bool:
        if not self.cond():
            return False

        upgrades = config[BUILDS][ai.build_order_runner.chosen_opening].get(TECHUPGRADES)

        if not upgrades:
            return False
        
        UPGRADE_STRUCT = {
            "CONCUSSIVESHELLS": (UnitTypeId.BARRACKSTECHLAB, UpgradeId.PUNISHERGRENADES, AbilityId.RESEARCH_CONCUSSIVESHELLS),
            "STIMPACK": (UnitTypeId.BARRACKSTECHLAB, UpgradeId.STIMPACK, AbilityId.BARRACKSTECHLABRESEARCH_STIMPACK),
            "COMBATSHIELD": (UnitTypeId.BARRACKSTECHLAB, UpgradeId.SHIELDWALL, AbilityId.RESEARCH_COMBATSHIELD),
            "INFANTRYARMORS1": (UnitTypeId.ENGINEERINGBAY, UpgradeId.TERRANINFANTRYARMORSLEVEL1, AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL1),
            "INFANTRYWEAPONS1": (UnitTypeId.ENGINEERINGBAY, UpgradeId.TERRANINFANTRYWEAPONSLEVEL1, AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL1),
            "INFANTRYARMORS2": (UnitTypeId.ENGINEERINGBAY, UpgradeId.TERRANINFANTRYARMORSLEVEL2, AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL2),
            "INFANTRYWEAPONS2": (UnitTypeId.ENGINEERINGBAY, UpgradeId.TERRANINFANTRYWEAPONSLEVEL2, AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL2),
            "YAMATOCANNON": (UnitTypeId.FUSIONCORE, None, AbilityId.RESEARCH_BATTLECRUISERWEAPONREFIT),
            "SHIPWEAPONS1": (UnitTypeId.ARMORY, UpgradeId.TERRANSHIPWEAPONSLEVEL1, AbilityId.ARMORYRESEARCH_TERRANSHIPWEAPONSLEVEL1),
            "SHIPARMORS1": (UnitTypeId.ARMORY, UpgradeId.TERRANSHIPARMORSLEVEL1, AbilityId.ARMORYRESEARCH_TERRANVEHICLEANDSHIPPLATINGLEVEL1),
            "SHIPWEAPONS2": (UnitTypeId.ARMORY, UpgradeId.TERRANSHIPWEAPONSLEVEL2, AbilityId.ARMORYRESEARCH_TERRANSHIPWEAPONSLEVEL2),
            "SHIPARMORS2": (UnitTypeId.ARMORY, UpgradeId.TERRANSHIPARMORSLEVEL2, AbilityId.ARMORYRESEARCH_TERRANVEHICLEANDSHIPPLATINGLEVEL2),
        }

        for upgrade_name in upgrades:
            building_type, upgrade_id, ability_id = UPGRADE_STRUCT[upgrade_name.upper()]

            if tech_labs := ai.structures(building_type).ready.idle:
                if upgrade_id and ai.already_pending_upgrade(upgrade_id):
                    continue
                if not ai.can_afford(ability_id):
                    continue
                tech_labs.first(ability_id)
                return True

        return False