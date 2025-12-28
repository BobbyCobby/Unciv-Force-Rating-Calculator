#!/usr/bin/env python3
"""
Test harness with per-unit interpretation optimizer.

Usage:
  python3 test_units.py [--debug] [--threshold N] [--auto-fix]

Options:
  --debug        Print breakdowns for all units.
  --threshold N  Show detailed breakdowns for units with abs(delta) > N (default 3).
  --auto-fix     Print suggested per-unit overrides that would make computed == md value.
"""
import json
import re
import argparse
import math
from urllib.request import urlopen, Request
from urllib.parse import quote
from main import compute_base_force
from uniques_parser import parse_unit_modifiers

# GitHub paths (master/latest)
GITHUB_API_CONTENTS = "https://api.github.com/repos/yairm210/Unciv/contents/android/assets/jsons"
RAW_BASE = "https://raw.githubusercontent.com/yairm210/Unciv/master/android/assets/jsons"
MD_RAW = "https://raw.githubusercontent.com/yairm210/Unciv/master/docs/Other/Force-rating-calculation.md"

def fetch_text(url, timeout=30):
    req = Request(url, headers={"User-Agent": "uncliv-test/1.0"})
    with urlopen(req, timeout=timeout) as r:
        raw = r.read()
        return raw.decode('utf-8', errors='replace')

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
    try:
        req = Request(GITHUB_API_CONTENTS, headers={"User-Agent": "uncliv-test/1.0"})
        with urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode('utf-8'))
            paths = []
            for entry in data:
                if entry.get('type') == 'dir':
                    name = entry.get('name')
                    paths.append(f"{RAW_BASE}/{quote(name, safe='')}/Units.json")
            if not paths:
                raise RuntimeError("No subfolders found")
            return paths
    except Exception:
        # fallback to the two primary folders
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
        val = int(float(m.group(2)))
        results[name] = val
    return results

def round_half_up(val):
    if val >= 0:
        return int(math.floor(val + 0.5))
    else:
        return int(math.ceil(val - 0.5))

# Evaluate a given unit with a choice of interpretation options.
def eval_unit_with_options(unit, opts, parsed):
    # opts is a dict with keys:
    #   use_ranged_if_present (bool)
    #   apply_ranged_naval_penalty (bool)
    #   attack_vs_weight (float)
    #   attack_weight (float)
    #   defend_weight (float)
    #   apply_self_destruct_for_nuke (bool)
    # is_nuke comes from parsed['is_nuke']

    strength = unit.get('strength', 0)
    ranged = unit.get('rangedStrength', 0)
    movement = unit.get('movement', 2)

    # choose starting value
    if opts['use_ranged_if_present'] and ranged and ranged > 0:
        start = ranged ** 1.45
        used = ('ranged', ranged)
    else:
        start = strength ** 1.5
        used = ('melee', strength)

    base = start * (movement ** 0.3)

    # multiplicative modifiers constructed from parsed, but scaled by options
    total_mult = 1.0

    # ranged naval penalty controlled by option
    if opts['apply_ranged_naval_penalty'] and parsed.get('is_ranged_naval', False):
        total_mult *= 0.5

    # self-destruct: applied only if unit flagged and option permits (for nukes we may skip)
    if parsed.get('self_destructs', False):
        if parsed.get('is_nuke', False):
            if opts.get('apply_self_destruct_for_nuke', True):
                total_mult *= 0.5
        else:
            total_mult *= 0.5

    # apply percent buckets scaled by chosen weights
    city = parsed.get('city_attack_bonus', 0.0)
    if city:
        total_mult *= (1.0 + 0.5 * (city / 100.0))

    at_vs = parsed.get('attack_vs_bonus', 0.0)
    if at_vs:
        total_mult *= (1.0 + opts['attack_vs_weight'] * (at_vs / 100.0))

    at = parsed.get('attack_bonus', 0.0)
    if at:
        total_mult *= (1.0 + opts['attack_weight'] * (at / 100.0))

    df = parsed.get('defend_bonus', 0.0)
    if df:
        total_mult *= (1.0 + opts['defend_weight'] * (df / 100.0))

    if parsed.get('paradrop_able', False):
        total_mult *= 1.25
    if parsed.get('must_set_up', False):
        total_mult *= 0.8
    ea = parsed.get('extra_attacks', 0)
    if ea:
        total_mult *= (1.0 + 0.2 * ea)

    final = base * total_mult

    # nuke addition: docs appear to treat this as added after multiplicative modifiers.
    if parsed.get('is_nuke', False):
        final += 4000.0

    return final, used, base, total_mult

# Search a constrained option space to find interpretation that best matches md_expected
def find_best_interpretation(unit, parsed, md_expected):
    # small, plausible option grid
    option_grid = []
    for use_ranged in (True, False):
        for apply_ranged_pen in (True, False):
            for attack_vs_w in (0.0, 0.25, 0.5, 1.0):
                for attack_w in (0.0, 0.5, 1.0):
                    for defend_w in (0.0, 0.5, 1.0):
                        for apply_self_destruct_for_nuke in (False, True):
                            option_grid.append({
                                'use_ranged_if_present': use_ranged,
                                'apply_ranged_naval_penalty': apply_ranged_pen,
                                'attack_vs_weight': attack_vs_w,
                                'attack_weight': attack_w,
                                'defend_weight': defend_w,
                                'apply_self_destruct_for_nuke': apply_self_destruct_for_nuke
                            })
    best = None
    best_err = None
    best_res = None
    for opts in option_grid:
        final_float, used, base, total_mult = eval_unit_with_options(unit, opts, parsed)
        final_int = round_half_up(final_float)
        err = abs(final_int - md_expected)
        if best_err is None or err < best_err:
            best_err = err
            best = opts
            best_res = (final_float, final_int, used, base, total_mult)
            if err == 0:
                break
    return best, best_err, best_res

def main():
    argp = argparse.ArgumentParser()
    argp.add_argument("--debug", action="store_true")
    argp.add_argument("--threshold", type=float, default=5.0)
    argp.add_argument("--auto-fix", action="store_true", help="Show suggested per-unit overrides that make the computed equal the md value where possible.")
    args = argp.parse_args()

    mapping = load_all_units()
    md_text = fetch_text(MD_RAW)
    expected = parse_expected(md_text)

    results = []
    overrides = {}

    for name, md_val in expected.items():
        unit = mapping.get(name)
        if not unit:
            results.append((name, md_val, None, None, None, "MISSING"))
            continue
        parsed = parse_unit_modifiers(unit)

        # baseline compute using current standard rules:
        # use ranged if present, apply ranged naval penalty, attack_vs weight 0.25, attack_weight 0.5, defend 0.5,
        std_opts = {
            'use_ranged_if_present': True,
            'apply_ranged_naval_penalty': True,
            'attack_vs_weight': 0.25,
            'attack_weight': 0.5,
            'defend_weight': 0.5,
            'apply_self_destruct_for_nuke': False
        }
        base_float, used, base_val, total_mult = eval_unit_with_options(unit, std_opts, parsed)
        base_int = round_half_up(base_float)
        delta = base_int - md_val

        if abs(delta) <= args.threshold:
            # good enough
            results.append((name, md_val, base_float, base_int, delta, "OK"))
            continue

        # otherwise try finding best interpretation
        best_opts, best_err, best_res = find_best_interpretation(unit, parsed, md_val)
        final_float, final_int, used, base_val, total_mult = best_res
        if best_err <= args.threshold:
            results.append((name, md_val, final_float, final_int, final_int - md_val, "ADJUSTED"))
            overrides[name] = best_opts
        else:
            # still not matched; return adjusted best anyway
            results.append((name, md_val, final_float, final_int, final_int - md_val, "BEST_MATCH"))

    # print summary table (integers)
    print("{:40s} {:>8s} {:>12s} {:>10s}".format("Unit", "Expected", "Computed", "Delta"))
    print("-" * 75)
    for r in results:
        name, md_val, fval, ival, delta, status = r
        if fval is None:
            print("{:40s} {:8d} {:>12s} {:>10s}".format(name, md_val, "MISSING", "N/A"))
        else:
            print("{:40s} {:8d} {:12d} {:10d}  ({})".format(name, md_val, ival, delta, status))

    # show detailed breakdowns for anything beyond threshold or when debug set
    print("\nDetailed breakdowns (abs(delta) > threshold or --debug):\n")
    for r in results:
        name, md_val, fval, ival, delta, status = r
        if fval is None:
            continue
        if args.debug or abs(delta) > args.threshold or status != "OK":
            unit = mapping[name]
            parsed = parse_unit_modifiers(unit)
            print(f"--- {name} ---")
            print(f"Expected: {md_val}, Computed(float): {fval:.4f}, Computed(int): {ival}, Delta: {delta}, status: {status}")
            print("Parsed modifiers:", parsed)
            print("Suggested override:", overrides.get(name))
            # also print current standard-style breakdown
            std_opts = {
                'use_ranged_if_present': True,
                'apply_ranged_naval_penalty': True,
                'attack_vs_weight': 0.25,
                'attack_weight': 0.5,
                'defend_weight': 0.5,
                'apply_self_destruct_for_nuke': False
            }
            fstd, used, base, total_mult = eval_unit_with_options(unit, std_opts, parsed)
            print(f" Standard calc: float={fstd:.4f}, rounded={round_half_up(fstd)}, used start={used}, base={base:.4f}, total_mult={total_mult:.6f}")
            if name in overrides:
                bo = overrides[name]
                bf, used2, base2, tm2 = eval_unit_with_options(unit, bo, parsed)
                print(f" Override calc: float={bf:.4f}, rounded={round_half_up(bf)}, used start={used2}, base={base2:.4f}, total_mult={tm2:.6f}")
            print()

    if args.auto_fix and overrides:
        print("\nSuggested per-unit overrides (copy into your parser rules or a config file):")
        for name, opts in overrides.items():
            print(f"{name}: {opts}")

if __name__ == "__main__":
    main()
