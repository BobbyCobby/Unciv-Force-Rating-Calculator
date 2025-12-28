#!/usr/bin/env python3
"""
Verbose test harness: same as before but prints a breakdown for units with large deltas
(use --debug to print all units).
"""
import json
import re
import argparse
from urllib.request import urlopen, Request
from main import compute_base_force
from uniques_parser import parse_unit_modifiers

COMMIT = "b57046317937f566c5b4d9c2d2c317183bc60c9f"
UNITS_URLS = [
    f"https://raw.githubusercontent.com/yairm210/Unciv/{COMMIT}/android/assets/jsons/Civ%20V%20-%20Vanilla/Units.json",
    f"https://raw.githubusercontent.com/yairm210/Unciv/{COMMIT}/android/assets/jsons/Civ%20V%20-%20Gods%20%26%20Kings/Units.json"
]
MD_RAW = f"https://raw.githubusercontent.com/yairm210/Unciv/{COMMIT}/docs/Other/Force-rating-calculation.md"

def fetch_text(url, timeout=30):
    req = Request(url, headers={"User-Agent": "uncliv-test/1.0"})
    with urlopen(req, timeout=timeout) as r:
        raw = r.read()
        text = raw.decode('utf-8', errors='replace')
        return text

def strip_js_comments_and_trailing_commas(s):
    import re
    s = re.sub(r'/\*.*?\*/', '', s, flags=re.S)
    s = re.sub(r'//.*', '', s)
    s = re.sub(r',\s*(\}|\])', r'\1', s)
    return s

def fetch_json(url):
    txt = fetch_text(url)
    cleaned = strip_js_comments_and_trailing_commas(txt)
    return json.loads(cleaned)

def load_all_units(urls):
    all_units = []
    for u in urls:
        try:
            data = fetch_json(u)
            print(f"Loaded {len(data)} units from {u}")
            all_units.extend(data)
        except Exception as e:
            print(f"Warning: failed to load {u}: {e}")
    mapping = {}
    for unit in all_units:
        mapping[unit.get('name')] = unit
    return mapping

def parse_expected(md_text):
    results = {}
    for m in re.finditer(r'`([^`]+?)\s+(\d+)`', md_text):
        name = m.group(1).strip()
        val = float(m.group(2))
        results[name] = val
    return results

def compute_for_unit_with_breakdown(u):
    name = u.get('name')
    movement = u.get('movement', 2)
    strength = u.get('strength', 0)
    ranged = u.get('rangedStrength', 0)
    is_nuke = name.strip().lower() in {'atomic bomb', 'nuclear missile'}

    parsed = parse_unit_modifiers(u)
    # Save parsed fields
    city_percent = parsed['city_attack_bonus']
    attack_vs_percent = parsed['attack_vs_bonus']
    attack_percent = parsed['attack_bonus']
    defend_percent = parsed['defend_bonus']
    paradrop = parsed['paradrop_able']
    must_set_up = parsed['must_set_up']
    self_destructs = parsed['self_destructs']
    extra_attacks = parsed['extra_attacks']
    is_ranged_naval = parsed['is_ranged_naval']

    # Compute stepwise and capture each multiplier
    from math import pow
    if ranged and ranged > 0:
        start = pow(ranged, 1.45)
        used = f"ranged ({ranged})"
    else:
        start = pow(strength, 1.5)
        used = f"melee ({strength})"
    move_mult = pow(movement, 0.3)
    base = start * move_mult
    notes = []
    notes.append(f"start={start:.4f} (used {used}), movement={movement} => base={base:.4f}")

    if is_nuke:
        base += 4000
        notes.append("nuke:+4000")

    total_mult = 1.0

    if is_ranged_naval:
        total_mult *= 0.5
        notes.append("ranged_naval: *0.5")

    if self_destructs:
        total_mult *= 0.5
        notes.append("self_destruct: *0.5")

    if city_percent:
        m = 1.0 + 0.5 * (city_percent / 100.0)
        total_mult *= m
        notes.append(f"city_percent {city_percent}% -> *{m:.4f}")

    if attack_vs_percent:
        m = 1.0 + 0.25 * (attack_vs_percent / 100.0)
        total_mult *= m
        notes.append(f"attack_vs_percent {attack_vs_percent}% -> *{m:.4f}")

    if attack_percent:
        m = 1.0 + 0.5 * (attack_percent / 100.0)
        total_mult *= m
        notes.append(f"attack_percent {attack_percent}% -> *{m:.4f}")

    if defend_percent:
        m = 1.0 + 0.5 * (defend_percent / 100.0)
        total_mult *= m
        notes.append(f"defend_percent {defend_percent}% -> *{m:.4f}")

    if paradrop:
        total_mult *= 1.25
        notes.append("paradrop: *1.25")
    if must_set_up:
        total_mult *= 0.8
        notes.append("must_set_up: *0.8")
    if extra_attacks:
        m = 1.0 + 0.2 * extra_attacks
        total_mult *= m
        notes.append(f"extra_attacks {extra_attacks} -> *{m:.4f}")
    final = base * total_mult
    return final, parsed, notes, {
        'start': start, 'movement_mult': move_mult, 'base': base, 'total_mult': total_mult
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true", help="print breakdown for all units")
    parser.add_argument("--threshold", type=float, default=3.0, help="delta threshold for breakdown")
    args = parser.parse_args()

    mapping = load_all_units(UNITS_URLS)
    md = fetch_text(MD_RAW)
    expected = parse_expected(md)

    rows = []
    for name, expected_val in expected.items():
        unit = mapping.get(name)
        if not unit:
            rows.append((name, expected_val, None, "MISSING", None))
            continue
        comp, parsed, notes, comps = compute_for_unit_with_breakdown(unit)
        rows.append((name, expected_val, comp, comp - expected_val, (parsed, notes, comps)))

    # short summary
    print("{:40s} {:>8s} {:>12s} {:>10s}".format("Unit", "Expected", "Computed", "Delta"))
    print("-" * 75)
    for row in rows:
        name, exp, comp, delta, detail = row
        if comp is None:
            print("{:40s} {:8.2f} {:>12s} {:>10s}".format(name, exp, "MISSING", "N/A"))
        else:
            print("{:40s} {:8.2f} {:12.2f} {:10.2f}".format(name, exp, comp, delta))

    # print breakdowns
    print("\nDetailed breakdowns (abs(delta) > threshold or --debug):\n")
    for row in rows:
        name, exp, comp, delta, detail = row
        if comp is None:
            continue
        if args.debug or abs(delta) > args.threshold:
            parsed, notes, comps = detail
            print(f"--- {name} ---")
            print(f"Expected: {exp}, Computed: {comp:.4f}, Delta: {delta:.4f}")
            print("Parsed modifiers:", parsed)
            print("Computation parts: start={start:.4f}, movement_mult={movement_mult:.4f}, base={base:.4f}, total_mult={total_mult:.6f}".format(**comps))
            for n in notes:
                print("  -", n)
            print()
if __name__ == "__main__":
    main()
