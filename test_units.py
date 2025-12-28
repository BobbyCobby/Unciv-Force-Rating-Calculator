#!/usr/bin/env python3

"""
Test harness: downloads Unciv Units.json (Vanilla) at the requested commit and the
docs/Other/Force-rating-calculation.md file, computes base unit forces using the
parser, and compares with the expected values in the markdown.

Usage:
  python3 test_units.py

Note: This is best-effort — the parser extracts many common uniques, but Unciv's
uniques strings are free-form and may require fine-tuning for edge cases.
"""
import json
import re
from urllib.request import urlopen
from main import compute_base_force
from uniques_parser import parse_unit_modifiers

# Use the commit the user specified earlier
COMMIT = "b57046317937f566c5b4d9c2d2c317183bc60c9f"
UNITS_RAW = f"https://raw.githubusercontent.com/yairm210/Unciv/{COMMIT}/android/assets/jsons/Civ%20V%20-%20Vanilla/Units.json"
MD_RAW = f"https://raw.githubusercontent.com/yairm210/Unciv/{COMMIT}/docs/Other/Force-rating-calculation.md"

def fetch_json(url):
    with urlopen(url) as r:
        return json.loads(r.read().decode('utf-8'))

def fetch_text(url):
    with urlopen(url) as r:
        return r.read().decode('utf-8')

def parse_expected(md_text):
    results = {}
    for m in re.finditer(r'`([^`]+?)\s+(\d+)`', md_text):
        name = m.group(1).strip()
        val = float(m.group(2))
        results[name] = val
    return results

def compute_for_unit(u):
    name = u.get('name')
    movement = u.get('movement', 2)
    strength = u.get('strength', 0)
    ranged = u.get('rangedStrength', 0)
    is_nuke = (name.lower().find('atomic') >= 0 or name.lower().find('nuclear') >= 0)

    parsed = parse_unit_modifiers(u)
    city_percent = parsed['city_attack_bonus']
    attack_vs_percent = parsed['attack_vs_bonus']
    attack_percent = parsed['attack_bonus']
    defend_percent = parsed['defend_bonus']
    paradrop = parsed['paradrop_able']
    must_set_up = parsed['must_set_up']
    self_destructs = parsed['self_destructs']
    extra_attacks = parsed['extra_attacks']
    is_ranged_naval = parsed['is_ranged_naval']

    return compute_base_force(
        strength=strength,
        ranged_strength=ranged,
        movement=movement,
        is_nuke=is_nuke,
        is_ranged_naval=is_ranged_naval,
        self_destructs=self_destructs,
        city_attack_bonus=city_percent,
        attack_vs_bonus=attack_vs_percent,
        attack_bonus=attack_percent,
        defend_bonus=defend_percent,
        paradrop_able=paradrop,
        must_set_up=must_set_up,
        terrain_bonus=0.0,
        extra_attacks=extra_attacks
    )

def main():
    units = fetch_json(UNITS_RAW)
    md = fetch_text(MD_RAW)
    expected = parse_expected(md)

    mapping = {u.get('name'): u for u in units}

    results = []
    for name, expected_val in expected.items():
        unit = mapping.get(name)
        if not unit:
            results.append((name, expected_val, None, 'unit not found in Units.json'))
            continue
        computed = compute_for_unit(unit)
        results.append((name, expected_val, computed, computed - expected_val))

    # Print a report
    print("{:40s} {:>8s} {:>12s} {:>10s}".format("Unit", "Expected", "Computed", "Delta"))
    print("-" * 75)
    for r in results:
        name, exp, comp, delta = r
        if comp is None:
            print("{:40s} {:8.2f} {:>12s} {:>10s}".format(name, exp, "MISSING", "N/A"))
        else:
            print("{:40s} {:8.2f} {:12.2f} {:10.2f}".format(name, exp, comp, delta))

if __name__ == "__main__":
    main()
