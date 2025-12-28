#!/usr/bin/env python3
"""
Test harness: downloads Unciv Units.json (Vanilla + Gods & Kings) from master branch,
parses unit uniques, computes Base Unit Force and compares to docs/Other/Force-rating-calculation.md (master).
Usage: python3 test_units.py [--debug] [--threshold N]
"""
import json
import re
import argparse
from urllib.request import urlopen, Request
from main import compute_base_force
from uniques_parser import parse_unit_modifiers

# Use the latest in master branch
UNITS_URLS = [
    "https://raw.githubusercontent.com/yairm210/Unciv/master/android/assets/jsons/Civ%20V%20-%20Vanilla/Units.json",
    "https://raw.githubusercontent.com/yairm210/Unciv/master/android/assets/jsons/Civ%20V%20-%20Gods%20%26%20Kings/Units.json"
]
MD_RAW = "https://raw.githubusercontent.com/yairm210/Unciv/master/docs/Other/Force-rating-calculation.md"

def fetch_text(url, timeout=30):
    req = Request(url, headers={"User-Agent": "uncliv-test/1.0"})
    with urlopen(req, timeout=timeout) as r:
        raw = r.read()
        text = raw.decode('utf-8', errors='replace')
        return text

def strip_js_comments_and_trailing_commas(s):
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

def compute_for_unit(u):
    name = u.get('name')
    movement = u.get('movement', 2)
    strength = u.get('strength', 0)
    ranged = u.get('rangedStrength', 0)

    parsed = parse_unit_modifiers(u)
    # Use parsed nuke flag instead of name heuristics
    is_nuke = parsed.get('is_nuke', False)

    # If a unit is marked self-destructing but is a nuke, skip applying the self-destruct penalty
    self_destructs_effective = parsed.get('self_destructs', False) and (not is_nuke)

    return compute_base_force(
        strength=strength,
        ranged_strength=ranged,
        movement=movement,
        is_nuke=is_nuke,
        is_ranged_naval=parsed.get('is_ranged_naval', False),
        self_destructs=self_destructs_effective,
        city_attack_bonus=parsed.get('city_attack_bonus', 0.0),
        attack_vs_bonus=parsed.get('attack_vs_bonus', 0.0),
        attack_bonus=parsed.get('attack_bonus', 0.0),
        defend_bonus=parsed.get('defend_bonus', 0.0),
        paradrop_able=parsed.get('paradrop_able', False),
        must_set_up=parsed.get('must_set_up', False),
        terrain_bonus=0.0,
        extra_attacks=parsed.get('extra_attacks', 0)
    )

def compute_for_unit_with_breakdown(u):
    name = u.get('name')
    movement = u.get('movement', 2)
    strength = u.get('strength', 0)
    ranged = u.get('rangedStrength', 0)

    parsed = parse_unit_modifiers(u)
    is_nuke = parsed.get('is_nuke', False)
    self_destructs_effective = parsed.get('self_destructs', False) and (not is_nuke)

    # replicate compute_base_force stepwise for breakdown
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
        base += 4000.0
        notes.append("nuke:+4000")

    total_mult = 1.0

    if parsed.get('is_ranged_naval', False):
        total_mult *= 0.5
        notes.append("ranged_naval: *0.5")

    if self_destructs_effective:
        total_mult *= 0.5
        notes.append("self_destruct: *0.5")
    else:
        if parsed.get('self_destructs', False) and is_nuke:
            notes.append("self_destruct present but skipped for nuke")

    if parsed.get('city_attack_bonus', 0.0):
        m = 1.0 + 0.5 * (parsed['city_attack_bonus'] / 100.0)
        total_mult *= m
        notes.append(f"city_percent {parsed['city_attack_bonus']}% -> *{m:.4f}")

    if parsed.get('attack_vs_bonus', 0.0):
        m = 1.0 + 0.25 * (parsed['attack_vs_bonus'] / 100.0)
        total_mult *= m
        notes.append(f"attack_vs_percent {parsed['attack_vs_bonus']}% -> *{m:.4f}")

    if parsed.get('attack_bonus', 0.0):
        m = 1.0 + 0.5 * (parsed['attack_bonus'] / 100.0)
        total_mult *= m
        notes.append(f"attack_percent {parsed['attack_bonus']}% -> *{m:.4f}")

    if parsed.get('defend_bonus', 0.0):
        m = 1.0 + 0.5 * (parsed['defend_bonus'] / 100.0)
        total_mult *= m
        notes.append(f"defend_percent {parsed['defend_bonus']}% -> *{m:.4f}")

    if parsed.get('paradrop_able', False):
        total_mult *= 1.25
        notes.append("paradrop: *1.25")
    if parsed.get('must_set_up', False):
        total_mult *= 0.8
        notes.append("must_set_up: *0.8")
    if parsed.get('extra_attacks', 0):
        m = 1.0 + 0.2 * parsed['extra_attacks']
        total_mult *= m
        notes.append(f"extra_attacks {parsed['extra_attacks']} -> *{m:.4f}")

    final = base * total_mult
    return final, parsed, notes, {
        'start': start, 'movement_mult': move_mult, 'base': base, 'total_mult': total_mult
    }

def main():
    argp = argparse.ArgumentParser()
    argp.add_argument("--debug", action="store_true", help="print breakdown for all units")
    argp.add_argument("--threshold", type=float, default=3.0, help="delta threshold for breakdown")
    args = argp.parse_args()

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

    print("{:40s} {:>8s} {:>12s} {:>10s}".format("Unit", "Expected", "Computed", "Delta"))
    print("-" * 75)
    for row in rows:
        name, exp, comp, delta, _ = row
        if comp is None:
            print("{:40s} {:8.2f} {:>12s} {:>10s}".format(name, exp, "MISSING", "N/A"))
        else:
            print("{:40s} {:8.2f} {:12.2f} {:10.2f}".format(name, exp, comp, delta))

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
