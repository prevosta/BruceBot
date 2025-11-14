from dataclasses import dataclass

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

    def execute(self, ai: AresBot, config: dict, mediator: ManagerMediator) -> bool:
        upgrades = config[BUILDS][ai.build_order_runner.chosen_opening].get(TECHUPGRADES)

        if not upgrades:
            return False
        
        UPGRADE_STRUCT = {
            "PUNISHERGRENADES": (UnitTypeId.BARRACKSTECHLAB, UpgradeId.PUNISHERGRENADES, AbilityId.RESEARCH_CONCUSSIVESHELLS),
            "STIMPACK": (UnitTypeId.BARRACKSTECHLAB, UpgradeId.STIMPACK, AbilityId.BARRACKSTECHLABRESEARCH_STIMPACK),
            "COMBATSHIELD": (UnitTypeId.BARRACKSTECHLAB, UpgradeId.SHIELDWALL, AbilityId.RESEARCH_COMBATSHIELD),
            "ARMORUPGRADE1": (UnitTypeId.ENGINEERINGBAY, UpgradeId.TERRANINFANTRYARMORSLEVEL1, AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL1),
            "WEAPONUPGRADE1": (UnitTypeId.ENGINEERINGBAY, UpgradeId.TERRANINFANTRYWEAPONSLEVEL1, AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL1),
            "YAMATOCANNON": (UnitTypeId.FUSIONCORE, None, AbilityId.RESEARCH_BATTLECRUISERWEAPONREFIT),
            "SHIPWEAPONS1": (UnitTypeId.ARMORY, UpgradeId.TERRANSHIPWEAPONSLEVEL1, AbilityId.ARMORYRESEARCH_TERRANSHIPWEAPONSLEVEL1),
            "SHIPARMOR1": (UnitTypeId.ARMORY, UpgradeId.TERRANSHIPARMORSLEVEL1, AbilityId.ARMORYRESEARCH_TERRANVEHICLEANDSHIPPLATINGLEVEL1),
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