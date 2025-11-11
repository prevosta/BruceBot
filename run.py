import sys
import random
import platform

from os import path
from pathlib import Path
from loguru import logger

from sc2 import maps
from sc2.data import AIBuild, Difficulty, Race
from sc2.main import run_game
from sc2.player import Bot, Computer

sys.path.append("ares-sc2/src/ares")
sys.path.append("ares-sc2/src")
sys.path.append("ares-sc2")

from ladder import run_ladder_game
from bot.main import BruceBot

plt = platform.system()

if plt == "Windows":
    MAPS_PATH: str = "C:\\Program Files (x86)\\StarCraft II\\Maps"
elif plt == "Darwin":
    MAPS_PATH: str = "/Applications/StarCraft II/Maps"
elif plt == "Linux":
    MAPS_PATH: str = "~/<username>/Games/battlenet/drive_c/Program Files (x86)/StarCraft II/Maps"
else:
    logger.error(f"{plt} not supported")
    sys.exit()

MAP_FILE_EXT: str = "SC2Map"

def main():
    __user_config_location__: str = path.abspath(".")

    bot_race: Race = Race.Terran
    bot = Bot(bot_race, BruceBot(), "Bruce")

    if "--LadderServer" in sys.argv:
        print("Starting ladder game...")
        result, opponentid = run_ladder_game(bot)
        print(result, " against opponent ", opponentid)

    else:
        print("Starting local game...")
        game_map = maps.get(random.choice([
            p.name.replace(f".{MAP_FILE_EXT}", "")
            for p in Path(MAPS_PATH).glob(f"*.{MAP_FILE_EXT}")
            if p.is_file() # and "Pylon" in p.name
        ]))

        random_race = random.choice([Race.Zerg, Race.Terran, Race.Protoss])
        # random_race = Race.Protoss
        random_difficulty = random.choice([Difficulty.VeryHard, Difficulty.CheatVision, Difficulty.CheatMoney, Difficulty.CheatInsane])
        # random_difficulty = Difficulty.CheatInsane
        random_build = AIBuild.RandomBuild
        # random_build = AIBuild.Macro  # AIBuild.Rush

        player1 = Bot(bot_race, BruceBot(), "Bruce")
        player2 = Computer(random_race, difficulty=random_difficulty, ai_build=random_build)

        run_game(game_map, [player1, player2], realtime=False)

if __name__ == "__main__":
    main()
