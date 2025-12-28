#!/usr/bin/env python3

from user_input import get_input_as_bool, get_input_as_int, get_input_as_float
from math_stuff import percent_to_decimal

def compute_base_force(strength=None, ranged_strength=None, movement=2, is_nuke=False,
                        is_ranged_naval=False, self_destructs=False,
                        city_attack_bonus=0.0, attack_vs_bonus=0.0,
                        attack_bonus=0.0, defend_bonus=0.0,
                        paradrop_able=False, must_set_up=False, terrain_bonus=0.0,
                        extra_attacks=0):
    """
    Compute Base Unit Force using corrected application of bonuses.
    All percent arguments are in percent, e.g. city_attack_bonus=50 means +50%.
    """
    from math import pow

    if ranged_strength is not None and ranged_strength > 0:
        base = pow(ranged_strength, 1.45)
    else:
        base = pow(strength, 1.5)

    base *= pow(movement, 0.3)

    if is_nuke:
        base += 4000.0

    # Ranged naval halves the force
    if is_ranged_naval:
        base *= 0.5

    if self_destructs:
        base *= 0.5

    # Apply percentage modifiers as multipliers (1 + fraction)
    if city_attack_bonus != 0:
        base *= (1.0 + 0.5 * percent_to_decimal(city_attack_bonus))

    if attack_vs_bonus != 0:
        base *= (1.0 + 0.25 * percent_to_decimal(attack_vs_bonus))

    if attack_bonus != 0:
        base *= (1.0 + 0.5 * percent_to_decimal(attack_bonus))

    if defend_bonus != 0:
        base *= (1.0 + 0.5 * percent_to_decimal(defend_bonus))

    if paradrop_able:
        base *= 1.25

    if must_set_up:
        base *= 0.8

    if terrain_bonus != 0:
        base *= (1.0 + 0.5 * percent_to_decimal(terrain_bonus))

    if extra_attacks != 0:
        # +20% per extra attack -> multiply by (1 + 0.2 * extra_attacks)
        base *= (1.0 + 0.2 * extra_attacks)

    return base

def interactive_main():
    is_ranged = get_input_as_bool("Is the unit ranged? ")
    if is_ranged:
        ranged_strength = get_input_as_int("Ranged strength: ")
        strength = get_input_as_int("Melee strength (0 if none): ")
    else:
        strength = get_input_as_int("Strength: ")
        ranged_strength = 0

    movement = get_input_as_int("Movement: ")
    is_nuke = get_input_as_bool("Is it a nuke? ")
    is_ranged_naval = False
    if is_ranged and get_input_as_bool("Is it naval (ranged naval)? "):
        is_ranged_naval = True

    self_destructs = get_input_as_bool("Does it self-destruct when attacking? ")
    city_attack_bonus = get_input_as_float("Percent bonus when attacking cities (0 if none): ")
    attack_vs_bonus = get_input_as_float("Bonus when attacking something that's not a city (0 if none): ")
    attack_bonus = get_input_as_float("Bonus when attacking (0 if none): ")
    defend_bonus = get_input_as_float("Bonus when defending (0 if none): ")
    paradrop_able = get_input_as_bool("Can it paradrop? ")
    must_set_up = get_input_as_bool("Does it need to Set Up to attack? ")
    terrain_bonus = get_input_as_float("Bonus on a particular terrain (0 if none): ")
    extra_attacks = get_input_as_int("Number of extra attacks per turn (0 if none): ")

    force = compute_base_force(strength=strength,
                               ranged_strength=ranged_strength,
                               movement=movement,
                               is_nuke=is_nuke,
                               is_ranged_naval=is_ranged_naval,
                               self_destructs=self_destructs,
                               city_attack_bonus=city_attack_bonus,
                               attack_vs_bonus=attack_vs_bonus,
                               attack_bonus=attack_bonus,
                               defend_bonus=defend_bonus,
                               paradrop_able=paradrop_able,
                               must_set_up=must_set_up,
                               terrain_bonus=terrain_bonus,
                               extra_attacks=extra_attacks)

    print("\n*************************\n")
    print("Base Unit Force: {:.2f}".format(force))
    print("\n*************************\n")

if __name__ == "__main__":
    interactive_main()
