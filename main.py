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

from user_input import get_input_as_bool
from math_stuff import percent_to_decimal

is_ranged = get_input_as_bool("Is the unit ranged? ")

if is_ranged:
	strength = int(input("Ranged strength: "))
	force = strength ** 1.45
else:
	strength = int(input("Strength: "))
	force = strength ** 1.5

movement = int(input("Movement: "))
force *= (movement ** 0.3)

is_nuke = get_input_as_bool("Is it a nuke? ")

if is_nuke:
	force += 4000

if is_ranged:
	is_ranged_naval = get_input_as_bool("Is it a naval unit?")
	
	if is_ranged_naval:
		force *= 0.5

self_destructs = get_input_as_bool("Does it self-destruct when attacking? ")

if self_destructs:
	force *= 0.5

city_attack_bonus = float(input("Percent bonus when attacking cities (0 if none): "))

if city_attack_bonus != 0: #If city_attack_bonus were 0, multiplying by half of it would make force zero
	force *= percent_to_decimal(0.5 * city_attack_bonus)

attack_vs_bonus = float(input("Bonus when attacking something that's not a city (0 if none): "))

if attack_vs_bonus != 0: #If attack_vs_bonus were 0, multiplying by a quarter of it would make force zero
	force *= percent_to_decimal(0.25 * attack_vs_bonus)

attack_bonus = float(input("Bonus when attacking (0 if none): "))

if attack_bonus != 0: #If attack_bonus were 0, multiplying by half of it would make force zero
	force *= percent_to_decimal(0.5 * attack_bonus)

defend_bonus = float(input("Bonus when defending (0 if none): "))

if defend_bonus != 0: #If defend_bonus were 0, multiplying by half of it would make force zero
	force *= percent_to_decimal(0.5 * defend_bonus)

paradrop_able = get_input_as_bool("Can it paradrop? ")

if paradrop_able:
	force *= 1.25

must_set_up = get_input_as_bool("Does it need to Set Up to attack? ")

if must_set_up:
	force *= 0.8

terrain_bonus = float(input("Bonus on a particular terrain (0 if none): "))

if terrain_bonus != 0: #If terrain_bonus were 0, multiplying by half of it would make force zero
	force *= percent_to_decimal(0.5 * terrain_bonus)

extra_attacks = int(input("Number of extra attacks per turn (0 if none): "))

if extra_attacks != 0: #If terrain_bonus were 0, multiplying by half of it would make force zero
	force *= (1.2 * extra_attacks)

print("\n*************************\n")
print("Base Unit Force: " + force)
print("\n*************************\n")
