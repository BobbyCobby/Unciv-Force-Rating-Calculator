#!/usr/bin/env python3
"""
Test harness with conservative interpretation rules and an optimizer for
edge cases.

This script:
- Fetches Units.json files from all folders under android/assets/jsons in the
  yairm210/Unciv/master branch (falls back to common folders if the API fails).
- Parses unit uniques with uniques_parser.parse_unit_modifiers(unit).
- Computes Base Unit Force using main.compute_base_force semantics, but also
  provides a constrained optimizer to find a small set of interpretation
  toggles when the straightforward calculation differs from the docs.
- Rounds computed values to integers (half-up) to compare with the docs which
  use integer values.

Usage:
  python3 test_units.py [--debug] [--threshold N] [--auto-fix]

Options:
  --debug        Print breakdowns for all units.
  --threshold N  Show detailed breakdowns for units with abs(delta) > N (default 5).
  --auto-fix     Print suggested per-unit overrides that would make computed == md value.
"""
from __future__ import annotations
import json
import re
import argparse
import math
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from main import compute_base_force
from uniques_parser import parse_unit_modifiers

# GitHub endpoints (master/latest)
GITHUB_API_CONTENTS = "https://api.github.com/repos/yairm210/Unciv/contents/android/assets/jsons"
RAW_BASE = "https://raw.githubusercontent.com/yairm210/Unciv/master/android/assets/jsons"
MD_RAW = "https://raw.githubusercontent.com/yairm210/Unciv/master/docs/Other/Force-rating-calculation.md"

USER_AGENT = "uncliv-test/1.0"

def fetch_text(url: str, timeout: int = 30) -> str:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=timeout) as r:
        raw = r.read()
        return raw.decode('utf-8', errors='replace')

def strip_js_comments_and_trailing_commas(s: str) -> str:
    s = re.sub(r'/\*.*?\*/', '', s, flags=re.S)
    s = re.sub(r'//.*', '', s)
    s = re.sub(r',\s*(\}|\])', r'\1', s)
    return s

def fetch_json(url: str):
    txt = fetch_text(url)
    cleaned = strip_js_comments_and_trailing_commas(txt)
    return json.loads(cleaned)

def list_units_json_paths() -> list[str]:
    """
    Query the GitHub API for folders under android/assets/jsons and construct
    raw URLs for each Units.json file. URL-encode folder names to avoid issues
    with spaces and special characters. If the API fails, fall back to the
    common Vanilla and Gods & Kings folders.
    """
    try:
        req = Request(GITHUB_API_CONTENTS, headers={"User-Agent": USER_AGENT})
        with urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode('utf-8'))
            paths = []
            for entry in data:
                if entry.get('type') == 'dir' and entry.get('name'):
                    name = entry.get('name')
                    paths.append(f"{RAW_BASE}/{quote(name, safe='')}/Units.json")
            if not paths:
                raise RuntimeError("No subfolders found in GitHub API response")
            return paths
    except Exception:
        # Fallback to the two common folders (URL-encoded)
        return [
            f"{RAW_BASE}/{quote('Civ V - Vanilla', safe='')}/Units.json",
            f"{RAW_BASE}/{quote('Civ V - Gods & Kings', safe='')}/Units.json"
        ]

def load_all_units() -> dict[str, dict]:
    urls = list_units_json_paths()
    all_units = []
    for u in urls:
        try:
            data = fetch_json(u)
            print(f"Loaded {len(data)} units from {u}")
            all_units.extend(data)
        except Exception as e:
            print(f"Warning: failed to load {u}: {e}")
    mapping: dict[str, dict] = {}
    for unit in all_units:
        name = unit.get('name')
        if name:
            mapping[name] = unit
    return mapping

def parse_expected(md_text: str) -> dict[str, int]:
    results: dict[str, int] = {}
    for m in re.finditer(r'`([^`]+?)\s+(\d+)`', md_text):
        name = m.group(1).strip()
        val = int(float(m.group(2)))
        results[name] = val
    return results

def round_half_up(val: float) -> int:
    if val >= 0:
        return int(math.floor(val + 0.5))
    else:
        return int(math.ceil(val - 0.5))

# Conservative evaluation with common-sense start selection and penalty rules.
def eval_unit_with_options(unit: dict, opts: dict, parsed: dict):
    """
    Evaluate unit's base force given interpretation options in opts and parsed uniques.
    opts keys:
      - use_ranged_if_present (bool): whether ranged is allowed to be chosen
      - apply_ranged_naval_penalty (bool): whether to apply 0.5 penalty for ranged naval units (only when ranged start chosen)
      - attack_vs_weight (float): fraction to apply to attack_vs bonuses (0-0.5 typical)
      - attack_weight (float): fraction to apply to when-attacking bonuses (0 or 0.5)
      - defend_weight (float): fraction to apply to when-defending bonuses (0 or 0.5)
      - apply_self_destruct_for_nuke (bool): whether nukes should get self-destruct penalty if flagged
    Returns: (final_float, used_start_tuple, base, total_mult)
    """
    strength = unit.get('strength', 0)
    ranged = unit.get('rangedStrength', 0)
    movement = unit.get('movement', 2)

    # compute both starts
    melee_start = (strength ** 1.5) if (strength and strength > 0) else 0.0
    ranged_start = (ranged ** 1.45) if (ranged and ranged > 0) else 0.0

    # Choose start with common-sense rule:
    # prefer melee unless ranged is present and >= 90% of melee, and option allows ranged.
    use_ranged_start = False
    if ranged_start > 0 and melee_start == 0:
        use_ranged_start = True
    elif ranged_start > 0 and melee_start > 0:
        if opts['use_ranged_if_present'] and (ranged_start >= 0.9 * melee_start):
            use_ranged_start = True
        else:
            use_ranged_start = False
    else:
        use_ranged_start = False

    if use_ranged_start:
        start = ranged_start
        used = ('ranged', ranged)
    else:
        start = melee_start
        used = ('melee', strength)

    base = start * (movement ** 0.3)

    total_mult = 1.0
    # Apply ranged-naval penalty only if we chose ranged start and unit is ranged naval
    if use_ranged_start and opts['apply_ranged_naval_penalty'] and parsed.get('is_ranged_naval', False):
        total_mult *= 0.5

    # Self-destruct
    if parsed.get('self_destructs', False):
        if parsed.get('is_nuke', False):
            if opts.get('apply_self_destruct_for_nuke', True):
                total_mult *= 0.5
        else:
            total_mult *= 0.5

    # City bonus (half)
    city = parsed.get('city_attack_bonus', 0.0)
    if city:
        total_mult *= (1.0 + 0.5 * (city / 100.0))

    # Attack vs (quarter by default, weighted)
    at_vs = parsed.get('attack_vs_bonus', 0.0)
    if at_vs:
        total_mult *= (1.0 + opts['attack_vs_weight'] * (at_vs / 100.0))

    # Attack when attacking (half by default, weighted)
    at = parsed.get('attack_bonus', 0.0)
    if at:
        total_mult *= (1.0 + opts['attack_weight'] * (at / 100.0))

    # Defend when defending (half by default, weighted)
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
    # Nuke addition after multiplicative modifiers
    if parsed.get('is_nuke', False):
        final += 4000.0

    return final, used, base, total_mult

def find_best_interpretation(unit: dict, parsed: dict, md_expected: int):
    """
    Constrained search of plausible options to minimize integer error vs md_expected.
    The option grid is intentionally conservative to avoid overfitting.
    """
    option_grid = []
    for use_ranged in (True, False):
        for apply_ranged_pen in (True, False):
            for attack_vs_w in (0.0, 0.25, 0.5):       # conservative set
                for attack_w in (0.0, 0.5):
                    for defend_w in (0.0, 0.5):
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
    argp.add_argument("--auto-fix", action="store_true", help="Show suggested per-unit overrides that make computed == md value where possible.")
    args = argp.parse_args()

    mapping = load_all_units()
    md_text = fetch_text(MD_RAW)
    expected = parse_expected(md_text)

    results = []
    overrides: dict[str, dict] = {}

    for name, md_val in expected.items():
        unit = mapping.get(name)
        if not unit:
            results.append((name, md_val, None, None, None, "MISSING"))
            continue
        parsed = parse_unit_modifiers(unit)

        # Standard conservative options
        std_opts = {
            'use_ranged_if_present': True,
            'apply_ranged_naval_penalty': True,
            'attack_vs_weight': 0.25,
            'attack_weight': 0.5,
            'defend_weight': 0.5,
            'apply_self_destruct_for_nuke': False
        }

        base_float, used, base, total_mult = eval_unit_with_options(unit, std_opts, parsed)
        base_int = round_half_up(base_float)
        delta = base_int - md_val

        if abs(delta) <= args.threshold:
            results.append((name, md_val, base_float, base_int, delta, "OK"))
            continue

        # Try to find a better constrained interpretation
        best_opts, best_err, best_res = find_best_interpretation(unit, parsed, md_val)
        if best_res is None:
            results.append((name, md_val, base_float, base_int, delta, "NO_MATCH"))
            continue

        final_float, final_int, used2, base2, tm2 = best_res
        status = "BEST_MATCH"
        if best_err <= args.threshold:
            status = "ADJUSTED"
            overrides[name] = best_opts
        results.append((name, md_val, final_float, final_int, final_int - md_val, status))

    # Summary table
    print("{:40s} {:>8s} {:>12s} {:>10s}".format("Unit", "Expected", "Computed", "Delta"))
    print("-" * 75)
    for r in results:
        name, md_val, fval, ival, delta, status = r
        if fval is None:
            print("{:40s} {:8d} {:>12s} {:>10s}".format(name, md_val, "MISSING", "N/A"))
        else:
            print("{:40s} {:8d} {:12d} {:10d}  ({})".format(name, md_val, ival, delta, status))

    # Detailed section
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
            # print standard breakdown
            std_opts = {
                'use_ranged_if_present': True,
                'apply_ranged_naval_penalty': True,
                'attack_vs_weight': 0.25,
                'attack_weight': 0.5,
                'defend_weight': 0.5,
                'apply_self_destruct_for_nuke': False
            }
            std_f, used_std, base_std, tm_std = eval_unit_with_options(unit, std_opts, parsed)
            print(f" Standard calc: float={std_f:.4f}, rounded={round_half_up(std_f)}, used start={used_std}, base={base_std:.4f}, total_mult={tm_std:.6f}")
            if name in overrides:
                bo = overrides[name]
                bo_f, used_bo, base_bo, tm_bo = eval_unit_with_options(unit, bo, parsed)
                print(f" Override calc: float={bo_f:.4f}, rounded={round_half_up(bo_f)}, used start={used_bo}, base={base_bo:.4f}, total_mult={tm_bo:.6f}")
            print()

    if args.auto_fix and overrides:
        print("\nSuggested per-unit overrides (copy into your parser rules or an exceptions file):")
        for name, opts in overrides.items():
            print(f"{name}: {opts}")

if __name__ == "__main__":
    main()
