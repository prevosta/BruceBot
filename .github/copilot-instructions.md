# BruceBot - StarCraft II AI Agent

## Project Overview

This is a **Terran bot for StarCraft II** built using the **ares-sc2 framework** (git submodule at `ares-sc2/`). The ares-sc2 framework extends python-sc2 with optimized pathing, production management, combat behaviors, and build order systems.

**Key Architecture Pattern**: This bot uses a **behavior registration system** where discrete behaviors are registered each frame via `self.register_behavior()`. Behaviors execute in priority order through the `BehaviorExecutioner`.

## Critical Framework Understanding

### Bot Inheritance Hierarchy
```
BotAI (python-sc2)
  └── CustomBotAI (ares-sc2)
       └── AresBot (ares-sc2) 
            └── BruceBot (bot/main.py)
```

Your bot class in `bot/main.py` inherits from `AresBot` which provides:
- `self.mediator`: ManagerMediator instance - the single source of truth for game state
- `self.register_behavior()`: Register behaviors to execute this frame
- `self.config`: Parsed configuration from `config.yml` + `terran_builds.yml`
- `self.build_order_runner`: Executes build orders from YAML configs

### The Mediator Pattern

**CRITICAL**: Access game state and services through `self.mediator`, not by calling managers directly.

Common mediator methods:
- `self.mediator.get_ground_grid` - Pathing grid with enemy influence
- `self.mediator.select_worker(target_position)` - Optimal worker selection
- `self.mediator.assign_role(tag, role)` - Assign UnitRole to units
- `self.mediator.get_units_from_role(role, unit_type)` - Query units by role
- `self.mediator.get_enemy_ramp` / `get_enemy_nat` - Map analysis data
- `self.mediator.get_own_units_dict` / `get_own_structures_dict` - Fast unit lookups by type
- `self.mediator.can_win_fight()` - Combat simulation
- `self.mediator.find_path_next_point(start, target, grid)` - A* pathing

See `ares-sc2/src/ares/managers/manager_mediator.py` for the full API.

## Behavior System

### Creating Custom Behaviors

Behaviors go in `behaviors/` and inherit from protocol classes:
- `CombatIndividualBehavior` - Single unit combat logic
- `CombatGroupBehavior` - Multi-unit combat coordination  
- `MacroBehavior` - Economy/production logic

Example structure:
```python
from dataclasses import dataclass
from ares.behaviors.combat.group import CombatGroupBehavior

@dataclass
class MyBehavior(CombatGroupBehavior):
    """Brief description."""
    
    # Optional dataclass fields for configuration
    min_units: int = 5
    
    def execute(self, ai: AresBot, config: dict, mediator: ManagerMediator) -> bool:
        # Your logic here
        # Return True if behavior did something, False otherwise
        return False
```

### Registering Behaviors

In `on_step()`, register behaviors each frame:
```python
self.register_behavior(Mining())  # Built-in ares behavior
self.register_behavior(MyCustomBehavior())  # Your custom behavior
```

Behaviors execute in registration order. Return `True` from `execute()` to indicate the behavior performed an action.

## Build Order System

Build orders are defined in `terran_builds.yml` using a declarative syntax:

```yaml
Builds:
  MyBuild:
    OpeningBuildOrder:
      - 0 SUPPLYDEPOT @ RAMP
      - 0 SCV
      - 0 BARRACKS
      - 0 REFINERY
      # ... continue build
    ProxyBuilder:  # Custom extension for this bot
      - 1100 ENEMY_FOURTH STARPORT
    ArmyComposition:
      - BATTLECRUISER 14
      - MARINE 50
```

- First column: iteration delay (usually 0 for exact ordering)
- `@ RAMP` places structures at main ramp
- `@ NATURAL` / `@ THIRD` / `@ ENEMY_FOURTH` are location targets
- `x2` multiplier for training multiple units

The BuildOrderRunner automatically handles worker assignment, structure placement, and production. Access via `self.build_order_runner`.

## Project Structure

```
bot/main.py              # BruceBot implementation (your main bot logic)
behaviors/               # Custom behaviors organized by combat/macro
  ├── combat/group/      # Multi-unit combat behaviors (BattleCruiser.py)
  └── macro/group/       # Production behaviors (ProxyBuilder.py, DropMule.py)
config.yml               # Main configuration (race, debug, features)
terran_builds.yml        # Build order definitions
run.py                   # Local testing entry point
ladder.py                # Ladder server integration
scripts/                 # Utility scripts for zip creation, uploads
ares-sc2/                # Framework submodule (DO NOT EDIT)
  └── src/ares/
      ├── behaviors/     # Built-in behaviors (Mining, AutoSupply, etc.)
      ├── managers/      # Game state management
      └── main.py        # AresBot base class
```

## Development Workflow

### Running Locally
```powershell
poetry run python run.py
```
This runs against a random opponent on a random map. Modify `run.py` to test specific matchups.

### Building for Ladder (AI Arena)
The GitHub Action workflow `.github/workflows/ladder_zip.yml` automatically:
1. Compiles Cython extensions on Linux
2. Creates `bot.zip` via `scripts/create_ladder_zip.py`
3. Uploads to AI Arena (if `AutoUploadToAiarena: True` and secrets configured)

Push to `main` branch to trigger the build.

### Testing
Use `poetry run python run.py` for quick iteration. The bot logs to console and can use chat commands if `ChatDebug: True` in `config.yml`.

## Common Patterns in This Codebase

### Worker Role Management
```python
if worker := self.mediator.select_worker(target_position=location):
    self.mediator.clear_role(tag=worker.tag)
    self.mediator.assign_role(tag=worker.tag, role=UnitRole.PROXY_WORKER)
    self.mediator.remove_worker_from_mineral(worker_tag=worker.tag)
    worker.move(location)
```

### Distance Checks (Optimized)
Use cython distance functions:
```python
from cython_extensions import cy_distance_to_squared
if cy_distance_to_squared(unit.position, target) < radius**2:
    # Do something
```

### Unit Queries
```python
# Fast lookups by type
marines = self.mediator.get_own_units_dict[UnitTypeId.MARINE]

# Query by role
defenders = self.mediator.get_units_from_role(
    role=UnitRole.DEFENDING, 
    unit_type=UnitTypeId.SCV
)
```

### Placement System
The framework pre-calculates building formations. Access via:
```python
self.mediator.get_placements_dict[base_location]
```

Custom placement functions in `bot/main.py`:
- `remove_illegal_positions(ai)` - Filter placements near resources
- `convert_3X3_to_5X5(ai)` - Convert stacked 3x3 spots to 5x5 for special buildings

## Configuration

`config.yml` key settings:
- `MyBotName` / `MyBotRace` - Bot identity
- `GameStep` - Frames per bot iteration (default: 2)
- `Debug` - Enables debug logging and visualization
- `UseData` - Track build performance across games

`terran_builds.yml`:
- `BuildSelection` - Algorithm for choosing builds (WinrateBased, Random)
- `BuildChoices` - Maps opponent races to builds
- `Builds` - Actual build order definitions

## Coding Guidelines

### Code Quality Principles
- **Keep it simple** - Write short, concise, clean and readable code
- **Minimize changes** - Always try to achieve your goal with the minimum number of changes
- **Be selective** - Only create new files when they add real value to the project
- **Avoid over-engineering** - Prefer straightforward solutions over complex abstractions

### Development Tracking
- **copilot-devlog.md** - Maintain a log of changes you make. Document what changed, why, and any important decisions
- **copilot-task.md** - Use this to plan, track, and remember your current work. Update it as you progress through tasks

Example devlog entry:
```markdown
## 2024-01-15 - Added BattleCruiser Yamato Cannon behavior
- Modified: behaviors/combat/group/BattleCruiser.py
- Added logic to prioritize anti-air units with Yamato Cannon
- Changed target selection to prefer high-value units (Vikings, Medivacs)
```

Example task file:
```markdown
# Current Task: Improve BattleCruiser Combat

## Goals
- [ ] Implement Yamato Cannon targeting
- [ ] Add Tactical Jump for retreat
- [ ] Test against air-heavy compositions

## Notes
- Yamato costs 125 energy, prioritize carefully
- Jump has 71s cooldown, use defensively
```

## Important Gotchas

1. **Don't modify ares-sc2 submodule** - It's a dependency, treat as read-only
2. **Always call `await super().on_step(iteration)`** - Ensures ares managers update
3. **Behaviors execute every frame** - They're not persistent; re-register each `on_step()`
4. **Build runner is "dumb"** - It follows instructions exactly; ensure build order has resources
5. **Cython extensions** - Import optimized functions from `cython_extensions` for performance
6. **Pathing grids** - Use `self.mediator.get_ground_grid` for influence-aware pathing
7. **Unit queries** - Use mediator methods for cached lookups; avoid filtering `self.units` repeatedly

## Useful Commands

```powershell
# Run bot locally
poetry run python run.py

# Update ares-sc2 submodule
python scripts/update_ares.py

# Format code
black .
isort .

# Create ladder zip (requires Linux)
poetry run python scripts/create_ladder_zip.py
```

## External Resources

- [ares-sc2 Documentation](https://aressc2.github.io/ares-sc2/index.html)
- [python-sc2 GitHub](https://github.com/BurnySc2/python-sc2) - Base framework
- [AI Arena](https://www.aiarena.net/) - Competitive ladder platform
- Build Runner Tutorial: `ares-sc2/docs/tutorials/build_runner.md`
- Behavior System: `ares-sc2/docs/tutorials/custom_behaviors.md`
