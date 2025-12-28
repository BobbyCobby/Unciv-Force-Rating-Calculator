#!/usr/bin/env python3
"""
Test harness: fetches all Units.json under android/assets/jsons in yairm210/Unciv (master),
parses unit uniques, computes Base Unit Force and compares to docs/Other/Force-rating-calculation.md (master).

Usage:
  python3 test_units.py [--debug] [--threshold N]
"""
import json
import re
import argparse
import math
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from main import compute_base_force
from uniques_parser import parse_unit_modifiers

GITHUB_API_CONTENTS = "https://api.github.com/repos/yairm210/Unciv/contents/android/assets/jsons"
RAW_BASE = "https://raw.githubusercontent.com/yairm210/Unciv/master/android/assets/jsons"
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

def list_units_json_paths():
    """
    Use GitHub API to list subfolders under android/assets/jsons and build Units.json raw URLs.
    If the API fails (rate limit), fall back to common folders (Vanilla and Gods & Kings).
    Folder names are URL-encoded to avoid spaces/control-character errors.
    """
    try:
        req = Request(GITHUB_API_CONTENTS, headers={"User-Agent": "uncliv-test/1.0"})
        with urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode('utf-8'))
            paths = []
            for entry in data:
                if entry.get('type') == 'dir':
                    name = entry.get('name')
                    # URL-encode the folder name so spaces and special chars are safe
                    paths.append(f"{RAW_BASE}/{quote(name, safe='')}/Units.json")
            if not paths:
                raise RuntimeError("No subfolders found — falling back")
            return paths
    except Exception:
        # fallback: include the two common folders (URL-encoded)
        return [
            f"{RAW_BASE}/{quote('Civ V - Vanilla', safe='')}/Units.json",
            f"{RAW_BASE}/{quote('Civ V - Gods & Kings', safe='')}/Units.json"
        ]

def load_all_units():
    urls = list_units_json_paths()
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
        val = int(float(m.group(2)))  # integer in the docs
        results[name] = val
    return results

def round_half_up(val):
    # Round positive numbers half-up (and negative numbers correctly)
    if val >= 0:
        return int(math.floor(val + 0.5))
    else:
        return int(math.ceil(val - 0.5))

def compute_for_unit_with_breakdown(u):
    name = u.get('name')
    movement = u.get('movement', 2)
    strength = u.get('strength', 0)
    ranged = u.get('rangedStrength', 0)

    parsed = parse_unit_modifiers(u)
    is_nuke = parsed.get('is_nuke', False)

    # compute start and movement
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

    # multiplicative modifiers
    total_mult = 1.0
    if parsed.get('is_ranged_naval', False):
        total_mult *= 0.5
        notes.append("ranged_naval: *0.5")
    if parsed.get('self_destructs', False):
        total_mult *= 0.5
        notes.append("self_destruct: *0.5")

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
    if is_nuke:
        final += 4000.0
        notes.append("nuke:+4000")

    # Provide both the raw float and the rounded integer (half-up)
    rounded = round_half_up(final)
    return final, rounded, parsed, notes, {
        'start': start, 'movement_mult': move_mult, 'base': base, 'total_mult': total_mult
    }

def main():
    argp = argparse.ArgumentParser()
    argp.add_argument("--debug", action="store_true", help="print breakdown for all units")
    argp.add_argument("--threshold", type=float, default=3.0, help="delta threshold for breakdown (in integers)")
    args = argp.parse_args()

    mapping = load_all_units()
    md = fetch_text(MD_RAW)
    expected = parse_expected(md)

    rows = []
    for name, expected_val in expected.items():
        unit = mapping.get(name)
        if not unit:
            rows.append((name, expected_val, None, None, None))
            continue
        comp_float, comp_rounded, parsed, notes, comps = compute_for_unit_with_breakdown(unit)
        delta = comp_rounded - expected_val
        rows.append((name, expected_val, comp_float, comp_rounded, delta, (parsed, notes, comps)))

    # Print summary table (integers, no decimals)
    print("{:40s} {:>8s} {:>12s} {:>10s}".format("Unit", "Expected", "Computed", "Delta"))
    print("-" * 75)
    for row in rows:
        name, exp, comp_float, comp_rounded, delta, _ = row
        if comp_rounded is None:
            print("{:40s} {:8d} {:>12s} {:>10s}".format(name, exp, "MISSING", "N/A"))
        else:
            print("{:40s} {:8d} {:12d} {:10d}".format(name, exp, comp_rounded, delta))

    print("\nDetailed breakdowns (abs(delta) > threshold or --debug):\n")
    for row in rows:
        name, exp, comp_float, comp_rounded, delta, detail = row
        if detail is None:
            continue
        if args.debug or abs(delta) > args.threshold:
            parsed, notes, comps = detail
            print(f"--- {name} ---")
            print(f"Expected: {exp}, Computed (float): {comp_float:.4f}, Computed (rounded): {comp_rounded}, Delta: {delta}")
            print("Parsed modifiers:", parsed)
            print("Computation parts: start={start:.4f}, movement_mult={movement_mult:.4f}, base={base:.4f}, total_mult={total_mult:.6f}".format(**comps))
            for n in notes:
                print("  -", n)
            print()

if __name__ == "__main__":
    main()
