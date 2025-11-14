import math
from dataclasses import dataclass

from cython_extensions import cy_distance_to_squared

from sc2.position import Point2
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId

from ares import AresBot
from ares.consts import BuildingSize
from ares.behaviors.combat.group import CombatGroupBehavior


@dataclass
class TankDefence(CombatGroupBehavior):
    """Defend key locations using Marine units."""

    tank_positions: list[Point2]

    def execute(self, ai: AresBot, config: dict, mediator) -> bool:

        # Unsiege tanks if enemies are too close
        for tank in ai.units(UnitTypeId.SIEGETANKSIEGED):
            if ai.enemy_units.filter(lambda u: cy_distance_to_squared(u.position, tank.position) <= 3**2).exists:
                tank(AbilityId.SIEGEBREAKERSIEGE_SIEGEMODE)

        # Get all unsieged tank units
        combat_units = ai.units(UnitTypeId.SIEGETANK)
        
        if not combat_units.exists:
            return False
        
        # Compute next best position (least occupied, then by order defined)
        sieged_units = ai.units(UnitTypeId.SIEGETANKSIEGED)
        pos_cnt = {pos: sum(1 for unit in sieged_units if cy_distance_to_squared(unit.position, pos) <= 1**2) for pos in self.tank_positions}
        pos_inx = {pos: idx for idx, pos in enumerate(self.tank_positions)}
        sorted_pos = sorted(self.tank_positions, key=lambda p: (pos_cnt[p], pos_inx[p]))

        for unit in combat_units:
            # Proceed to position
            if cy_distance_to_squared(sorted_pos[0], unit.position) >= 0.1**2:
                unit.move(sorted_pos[0])

            # Siege on arival
            elif not ai.enemy_units.filter(lambda u: cy_distance_to_squared(u.position, unit.position) <= 3**2).exists:
                unit(AbilityId.SIEGEMODE_SIEGEMODE)

        return True

    @staticmethod
    def generate(ai: AresBot, safety_distance: float = 9, safety_radius: float = 1.25, unit_separation: float = 6) -> list[Point2]:
        """Generate tank positions around the main base ramp and climber ingress points."""

        tank_positions: list[Point2] = []

        # Position in a circle around top ramp (inside region)
        center = ai.main_base_ramp.top_center
        region = ai.mediator.get_map_data_object.where(ai.start_location)
        for angle in range(0, 360, 2):
            rad = math.radians(angle)
            unit_pos = Point2((center.x + safety_distance * math.cos(rad), center.y + safety_distance * math.sin(rad)))
            if region.is_inside_point(unit_pos):
                tank_positions.append(unit_pos)

        # Sort (closest to reference position)
        ref_pos = Point2((ai.main_base_ramp.top_center.towards(ai.start_location, safety_distance)))
        tank_positions = sorted(tank_positions, key=lambda p: cy_distance_to_squared(p, ref_pos))

        # Merge close positions
        merged_positions: list[Point2] = []
        for pos in tank_positions:
            if not merged_positions:
                merged_positions.append(pos)
                continue

            if all(cy_distance_to_squared(pos, merged_pos) >= unit_separation**2 for merged_pos in merged_positions):
                merged_positions.append(pos)
        tank_positions = merged_positions[:5]

        # Mark structure placements as unavailable near tank positions
        for unit_pos in tank_positions:
            for size_grp, positions in ai.mediator.get_placements_dict[ai.start_location].items():
                for struct_pos, attribut in positions.items():
                    size = {BuildingSize.TWO_BY_TWO: 2, BuildingSize.THREE_BY_THREE: 3, BuildingSize.FIVE_BY_FIVE: 5}[size_grp]
                    half_size = (size / 2) + safety_radius

                    if (abs(unit_pos.x - struct_pos.x) <= half_size and abs(unit_pos.y - struct_pos.y) <= half_size):
                        attribut['available'] = False

                    if size_grp != BuildingSize.THREE_BY_THREE:
                        continue  # Skip non-add-on buildings

                    addon_pos = Point2((struct_pos.x + 2.5, struct_pos.y - 0.5))
                    half_size = (2 / 2) + safety_radius

                    if (abs(unit_pos.x - addon_pos.x) <= half_size and abs(unit_pos.y - addon_pos.y) <= half_size):
                        attribut['available'] = False

        return tank_positions
