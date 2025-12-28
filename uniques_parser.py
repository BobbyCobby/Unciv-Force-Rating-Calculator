"""
uniques_parser.py

Best-effort parser for Unciv unit 'uniques' strings.
Extracts common percent bonuses and flags that are needed for Base Unit Force computation.

Improvements:
- Better detection of naval/ranged naval unit types (submarine, aircraft carrier, melee/ranged water).
- Some heuristics to capture more percent patterns.
"""
import re

def parse_unit_modifiers(unit):
    uniques_list = unit.get('uniques') or []
    promotions = unit.get('promotions') or []
    text = " ".join(uniques_list + promotions).lower()

    # Collect percent entries like "[+50]% Strength <vs cities>" and variants
    percent_entries = []
    # Primary pattern: [NN]% Strength <...>
    for m in re.finditer(r'\[([+-]?\d+)\]\%?\s*%?\s*strength\s*<([^>]+)>', text):
        percent = float(m.group(1))
        tag = m.group(2).strip()
        percent_entries.append((percent, tag))

    # Simpler pattern if the previous missed something
    for m in re.finditer(r'\[([+-]?\d+)\]\%?\s*strength\s*<([^>]+)>', text):
        percent = float(m.group(1))
        tag = m.group(2).strip()
        percent_entries.append((percent, tag))

    city_attack_bonus = 0.0
    attack_vs_bonus = 0.0
    attack_bonus = 0.0
    defend_bonus = 0.0

    for percent, tag in percent_entries:
        if 'city' in tag:
            city_attack_bonus += percent
        elif 'when attacking' in tag or 'when attacking' in text and 'when defending' not in tag:
            if 'when attacking' in tag:
                attack_bonus += percent
            else:
                attack_bonus += percent
        elif 'when defending' in tag or 'when defending' in text:
            defend_bonus += percent
        else:
            # generic 'vs [mounted]' or 'vs [submarine]' -> treat as attack_vs_bonus
            attack_vs_bonus += percent

    # Paradrop detection
    paradrop_able = 'paradrop' in text or 'paratroop' in text or 'paratrooper' in text

    # Must set up detection
    must_set_up = 'must set up to ranged attack' in text or 'must set up' in text or 'must set up to' in text

    # Self-destruct detection
    self_destructs = 'self-destruct' in text or 'self destruct' in text or 'suicide' in text or 'explodes when attacking' in text

    # Extra attacks detection
    extra_attacks = 0
    m = re.search(r'(\d+)\s+extra\s+attacks?', text)
    if m:
        extra_attacks = int(m.group(1))
    else:
        m2 = re.search(r'(\d+)\s+attacks?\s+(per\s+turn|per turn|in one turn)', text)
        if m2:
            count = int(m2.group(1))
            if count > 1:
                extra_attacks = count - 1
    if extra_attacks == 0 and ('extra attack' in text or 'attack twice' in text or 'can attack twice' in text or 'attacks twice' in text):
        extra_attacks = 1

    # Ranged naval detection: check for water/submarine/carrier or unitType containing 'water' or 'submarine' etc.
    unit_type = (unit.get('unitType') or '').lower()
    ut_flags = unit_type
    is_ranged_naval = False
    ranged_strength = unit.get('rangedStrength', 0)

    if ranged_strength and ranged_strength > 0:
        # common naval indicators
        naval_indicators = ['water', 'submarine', 'aircraft carrier', 'carrier', 'ship', 'melee water', 'ranged water']
        if any(k in ut_flags for k in naval_indicators):
            is_ranged_naval = True
        # also if the uniques mention "can only attack [water]" or similar
        if 'can only attack [water]' in text or 'can only attack water' in text:
            is_ranged_naval = True

    return {
        'city_attack_bonus': city_attack_bonus,
        'attack_vs_bonus': attack_vs_bonus,
        'attack_bonus': attack_bonus,
        'defend_bonus': defend_bonus,
        'paradrop_able': paradrop_able,
        'must_set_up': must_set_up,
        'self_destructs': self_destructs,
        'extra_attacks': extra_attacks,
        'is_ranged_naval': is_ranged_naval
    }
