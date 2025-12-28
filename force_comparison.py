#    Unciv Force Rating Calculator is a Python script to calculate the base unit force of a unit in a mod for the game Unciv (https://github.com/yairm210/Unciv).
#    Copyright (C) 2025 BobbyCobby.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.

# This module (force_comparison.py) was written by GitHub Copilot.

# List taken from the provided Unciv "Force rating calculation" data.
# Function: find_force_bounds(force: float) -> str
# Returns:
#  - "Between X and Y" where X is the next-lowest standard unit and Y the next-highest standard unit
#  - "Higher than any G&K unit" if force > max standard unit
#  - "Lower than any G&K unit" if force < min standard unit

from bisect import bisect_right
from typing import List, Tuple

_UNITS: List[Tuple[str, float]] = [
    ("Scout", 13.0),
    ("Archer", 19.0),
    ("Slinger", 19.0),
    ("Dromon", 23.0),
    ("Warrior", 27.0),
    ("Maori Warrior", 27.0),
    ("Brute", 27.0),
    ("Bowman", 29.0),
    ("Jaguar", 36.0),
    ("Catapult", 39.0),
    ("Composite Bowman", 39.0),
    ("Galleass", 41.0),
    ("Chariot Archer", 42.0),
    ("War Elephant", 44.0),
    ("War Chariot", 45.0),
    ("Horse Archer", 45.0),
    ("Trireme", 46.0),
    ("Spearman", 49.0),
    ("Ballista", 55.0),
    ("Persian Immortal", 56.0),
    ("Horseman", 62.0),
    ("Hoplite", 63.0),
    ("Swordsman", 64.0),
    ("Chu-Ko-Nu", 66.0),
    ("Quinquereme", 69.0),
    ("African Forest Elephant", 72.0),
    ("Battering Ram", 80.0),
    ("Cataphract", 80.0),
    ("Crossbowman", 81.0),
    ("Longbowman", 81.0),
    ("Companion Cavalry", 84.0),
    ("Legion", 86.0),
    ("Mohawk Warrior", 86.0),
    ("Pikeman", 87.0),
    ("Landsknecht", 87.0),
    ("Trebuchet", 88.0),
    ("Keshik", 89.0),
    ("Frigate", 100.0),
    ("Hwach'a", 110.0),
    ("Longswordsman", 118.0),
    ("Camel Archer", 124.0),
    ("Samurai", 126.0),
    ("Berserker", 133.0),
    ("Knight", 134.0),
    ("Conquistador", 134.0),
    ("Mandekalu Cavalry", 134.0),
    ("Caravel", 134.0),
    ("Ship of the Line", 139.0),
    ("Musketman", 144.0),
    ("Cannon", 151.0),
    ("Minuteman", 154.0),
    ("Janissary", 162.0),
    ("Gatling Gun", 169.0),
    ("Musketeer", 182.0),
    ("Tercio", 182.0),
    ("Naresuan's Elephant", 194.0),
    ("Lancer", 204.0),
    ("Hakkapeliitta", 204.0),
    ("Sipahi", 218.0),
    ("Privateer", 222.0),
    ("Rifleman", 243.0),
    ("Carolean", 243.0),
    ("Sea Beggar", 244.0),
    ("Artillery", 245.0),
    ("Battleship", 269.0),
    ("Great War Bomber", 290.0),
    ("Cavalry", 300.0),
    ("Hussar", 320.0),
    ("Triplane", 325.0),
    ("Turtle Ship", 327.0),
    ("Cossack", 337.0),
    ("Norwegian Ski Infantry", 345.0),
    ("Guided Missile", 378.0),
    ("Carrier", 408.0),
    ("Submarine", 420.0),
    ("Bomber", 425.0),
    ("Great War Infantry", 434.0),
    ("Machine Gun", 465.0),
    ("Fighter", 470.0),
    ("Foreign Legion", 477.0),
    ("Ironclad", 486.0),
    ("Zero", 508.0),
    ("Anti-Tank Gun", 542.0),
    ("B17", 551.0),
    ("Marine", 645.0),
    ("Landship", 703.0),
    ("Infantry", 720.0),
    ("Nuclear Submarine", 735.0),
    ("Stealth Bomber", 771.0),
    ("Paratrooper", 806.0),
    ("Anti-Aircraft Gun", 819.0),
    ("Destroyer", 870.0),
    ("Missile Cruiser", 888.0),
    ("Rocket Artillery", 930.0),
    ("Tank", 948.0),
    ("Jet Fighter", 988.0),
    ("Helicopter Gunship", 992.0),
    ("Mechanized Infantry", 1186.0),
    ("Panzer", 1223.0),
    ("Mobile SAM", 1376.0),
    ("Modern Armor", 1620.0),
    ("Giant Death Robot", 2977.0),
    ("Atomic Bomb", 4714.0),
    ("Nuclear Missile", 7906.0),
]

# Split into parallel lists for fast bisect operations
_FORCES: List[float] = [f for (_n, f) in _UNITS]
_NAMES: List[str] = [n for (n, _f) in _UNITS]


def find_force_bounds(force: float) -> str:
    """
    Given a float 'force', return:
      - "Between X and Y" where X is the next lowest standard unit and Y the next highest standard unit.
      - "Lower than any G&K unit" if force < min standard force.
      - "Higher than any G&K unit" if force > max standard force.

    Behavior notes:
      - If force is exactly equal to a standard unit's force, the function returns the unit below (or the unit itself when it's the minimum)
        and the next unit above (or the unit itself when it's the maximum) so the output remains in "Between X and Y" form.
    """
    if force < _FORCES[0]:
        return "Lower than any G&K unit"
    if force > _FORCES[-1]:
        return "Higher than any G&K unit"

    # j = count of elements <= force
    j = bisect_right(_FORCES, force)

    # If j == len, force is >= max; but we handled force > max above.
    if j == len(_FORCES):
        # force is equal to the maximum value
        lower_idx = len(_FORCES) - 2 if len(_FORCES) >= 2 else 0
        higher_idx = len(_FORCES) - 1
    else:
        lower_idx = max(0, j - 1)
        higher_idx = j

    return f"Between {_NAMES[lower_idx]} and {_NAMES[higher_idx]}"

# Example usages (commented out):
# print(find_force_bounds(15.0))    # Between Scout and Archer
# print(find_force_bounds(19.0))    # Between Slinger and Dromon (since there are two 19.0 units)
# print(find_force_bounds(8000.0))  # Higher than any G&K unit
# print(find_force_bounds(10.0))    # Lower than any G&K unit
