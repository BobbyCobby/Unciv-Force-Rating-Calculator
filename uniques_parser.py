"""
uniques_parser.py

Best-effort parser for Unciv unit 'uniques' strings.
Extracts common percent bonuses and flags that are needed for Base Unit Force computation.

Limitations: this is heuristic-driven and tries to match the most common patterns found in
android/assets/jsons/.../Units.json. It won't be perfect for every mod or free-form unique,
but it finds: [+N]% Strength <vs cities>, [+N]% Strength <when attacking>, <when defending>,
generic [+N]% Strength <vs [TYPE]>, paradrop, must set up, self-destruct, extra attacks,
and detects ranged naval units.
"""

import re

def parse_unit_modifiers(unit):
    """
    Accepts a unit dict as in Units.json and returns a dict with keys:
      - city_attack_bonus (percent)
      - attack_vs_bonus (percent: vs non-city/general)
      - attack_bonus (percent when attacking)
      - defend_bonus (percent when defending)
      - paradrop_able (bool)
      - must_set_up (bool)
      - self_destructs (bool)
      - extra_attacks (int)
      - is_ranged_naval (bool)
    """
    uniques_list = unit.get('uniques') or []
    promotions = unit.get('promotions') or []
    text = " ".join(uniques_list + promotions).lower()

    # Helper to find all [+N]% or [-N]% occurrences with their tags in <>
    percent_entries = []
    for m in re.finditer(r'\[([+-]?\d+)\]\%?\s*%?\s*strength\s*<([^>]+)>', text):
        percent = float(m.group(1))
        tag = m.group(2).strip()
        percent_entries.append((percent, tag))

    # Also capture simpler forms like "[+50]% Strength <vs cities>" variations
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
            # if tag explicitly says when attacking
            if 'when attacking' in tag:
                attack_bonus += percent
            else:
                # heuristics: if tag mentions 'when attacking' or text overall suggests attack
                attack_bonus += percent
        elif 'when defending' in tag or 'when defending' in text:
            defend_bonus += percent
        else:
            # generic 'vs [mounted]' or 'vs [submarine]' -> treat as attack_vs_bonus
            attack_vs_bonus += percent

    # Paradrop detection
    paradrop_able = 'paradrop' in text or 'paratroop' in text or 'can paradrop' in text or 'paratrooper' in text

    # Must set up detection
    must_set_up = 'must set up to ranged attack' in text or 'must set up' in text or 'must set up to' in text

    # Self-destruct detection (phrases like 'self-destructs when attacking' or 'suicide' or 'explodes')
    self_destructs = 'self-destruct' in text or 'self destruct' in text or 'suicide' in text or 'explodes when attacking' in text

    # Extra attacks detection
    extra_attacks = 0
    # Look for phrases like "Number of extra attacks" or "[+1] attack" or "extra attack"
    m = re.search(r'(\d+)\s+extra\s+attacks?', text)
    if m:
        extra_attacks = int(m.group(1))
    else:
        # look for patterns like "makes 2 attacks per turn", "2 attacks"
        m2 = re.search(r'(\d+)\s+attacks?\s+(per\s+turn|per turn|in one turn)', text)
        if m2:
            count = int(m2.group(1))
            # if the text mentions "attacks" and it's >1, treat extra attacks = count - 1
            if count > 1:
                extra_attacks = count - 1
    # Some units have phrasing like "Extra attack" or "Can attack twice"
    if extra_attacks == 0 and ('extra attack' in text or 'attack twice' in text or 'can attack twice' in text or 'attacks twice' in text):
        extra_attacks = 1

    # Ranged naval detection: unitType containing water and rangedStrength exists
    unit_type = unit.get('unitType', '').lower()
    is_ranged_naval = ('water' in unit_type and unit.get('rangedStrength', 0) > 0)

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
