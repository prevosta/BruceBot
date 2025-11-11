# Development Log

Track changes, decisions, and important updates to the BruceBot codebase.

---

## 2025-11-11 - Initial copilot-instructions.md and tracking system

### Added
- `.github/copilot-instructions.md` - Comprehensive guidance for AI agents
  - Project architecture and inheritance hierarchy
  - Mediator pattern explanation with API examples
  - Behavior system documentation
  - Build order system syntax and usage
  - Common code patterns from existing codebase
  - Development workflow and deployment process
  - Coding guidelines and quality principles

- `copilot-task.md` - Task planning and tracking file
  - Template for managing current work
  - Archive section for completed tasks

- `copilot-devlog.md` - This development log
  - Track changes and important decisions
  - Document what changed and why

### Purpose
These files help AI coding agents (and human developers) quickly understand:
- How the ares-sc2 framework works with BruceBot
- Project-specific patterns and conventions
- Development workflows and deployment
- How to track work and maintain project history

### Key Decisions
- Focused on actionable, project-specific knowledge rather than generic advice
- Included real examples from the codebase (ProxyBuilder, BattleCruiser behaviors)
- Emphasized the mediator pattern as the critical access point for game state
- Documented the behavior registration system as the core architecture pattern

---

## 2025-11-11 - Fixed AI Arena initialization bug

### Fixed
- **Import path issues in bot/main.py** - AI Arena ladder was failing to initialize due to incorrect module imports
  - Changed: `from behaviors.combat.group.BattleCruiser import BattleCruiser` 
  - To: `from bot.behaviors.combat.group.BattleCruiser import BattleCruiser`
  - Changed: `from behaviors.macro.group import ...`
  - To: `from bot.behaviors.macro.group import ...`

### Added
- **Proper Python module structure** for behaviors directory
  - Created `bot/__init__.py` to make it a proper package
  - Created `bot/behaviors/__init__.py` and subdirectory `__init__.py` files
  - Moved all behaviors from `behaviors/` to `bot/behaviors/` for consistent module structure

### Modified
- `bot/main.py` - Updated import statements to use qualified module paths
- `bot/behaviors/combat/group/__init__.py` - Added proper exports
- `bot/behaviors/macro/group/__init__.py` - Added proper exports

### Root Cause
The behaviors were originally in a top-level `behaviors/` directory but imported as if they were inside the `bot/` package. When the ladder system tried to initialize the bot, Python couldn't resolve the imports because the package structure didn't match the import statements.

### Notes
- The bot now has a clean module hierarchy: `bot.behaviors.{combat|macro}.group.{BehaviorName}`
- All behaviors are properly packaged and can be imported consistently
- This fix ensures the bot will initialize correctly on AI Arena ladder infrastructure

---

## Template for Future Entries

```markdown
## YYYY-MM-DD - Brief description

### Added
- New files or features

### Modified
- Changed files with explanation

### Removed
- Deleted files or deprecated features

### Fixed
- Bug fixes

### Notes
- Important decisions or context
```
