import sys
import random
import platform
from pathlib import Path
from typing import List
from loguru import logger

from sc2 import maps
from sc2.data import AIBuild, Difficulty, Race
from sc2.main import run_game
from sc2.player import Bot, Computer

sys.path.append("ares-sc2/src/ares")
sys.path.append("ares-sc2/src")
sys.path.append("ares-sc2")

from bot.main import BruceBot
from ladder import run_ladder_game


plt = platform.system()

if plt == "Windows":
    MAPS_PATH: str = "C:\\Program Files (x86)\\StarCraft II\\Maps"
elif plt == "Darwin":
    MAPS_PATH: str = "/Applications/StarCraft II/Maps"
elif plt == "Linux":
    MAPS_PATH: str = ("~/<username>/Games/battlenet/drive_c/Program Files (x86)/StarCraft II/Maps")
else:
    logger.error(f"{plt} not supported")
    sys.exit()

def main():
    bot_name: str = "BruceBot"
    race: Race = Race.Terran
    player1 = Bot(race, BruceBot(), bot_name)

    # Ladder game started by LadderManager
    if "--LadderServer" in sys.argv:
        print("Starting ladder game...")
        result, opponentid = run_ladder_game(player1)
        print(result, " against opponent ", opponentid)

    # Local game
    else:
        map_list: List[str] = [p.name.replace(f".SC2Map", "") for p in Path(MAPS_PATH).glob(f"*.SC2Map") if p.is_file()]
        random_race = random.choice([Race.Zerg, Race.Terran, Race.Protoss])
        random_difficulty = random.choice([Difficulty.CheatVision])
        player2 = Computer(random_race, random_difficulty, ai_build=AIBuild.Macro)

        print("Starting local game...")
        run_game(maps.get(random.choice(map_list)),[player1, player2], realtime=False)

if __name__ == "__main__":
    main()
