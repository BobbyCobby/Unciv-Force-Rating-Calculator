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

def get_input_as_bool(prompt, error_on_bad_input=False):
	positive = {"yes", "y", "true"}
	negative = {"no", "n", "false"}
	
	answer = input(prompt)
	answer = answer.lower()
	
	if answer in positive:
		return True
	elif answer in negative:
		return False
	else:
		if error_on_bad_input:
			raise ValueError("Input must be yes, y, true, no, n, or false")
		else:
			return get_input_as_bool(prompt, error_on_bad_input=error_on_bad_input)
