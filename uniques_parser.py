"""
uniques_parser.py

Heuristic parser for Unciv unit 'uniques' strings.

Fixes:
- Only classify percent bonuses based on the tag inside <>.
- Deduplicate percent entries.
- No fallback using 'when attacking' presence in full text.
- Improved naval detection remains.
"""
import re

def parse_unit_modifiers(unit):
    uniques_list = unit.get('uniques') or []
    promotions = unit.get('promotions') or []
    text = " ".join(uniques_list + promotions).lower()

    # Find bracketed percent patterns followed by 'strength' and a tag in <>
    # Example: "[+50]% Strength <vs cities>"
    percent_entries = set()
    for m in re.finditer(r'\[([+-]?\d+)\]\s*%?\s*strength\s*<([^>]+)>', text, flags=re.IGNORECASE):
        try:
            percent = float(m.group(1))
        except ValueError:
            continue
        tag = m.group(2).strip().lower()
        percent_entries.add((percent, tag))

    # Initialize result buckets
    city_attack_bonus = 0.0
    attack_vs_bonus = 0.0
    attack_bonus = 0.0
    defend_bonus = 0.0

    # Classify purely by tag content (no global-text fallback)
    for percent, tag in percent_entries:
        if 'city' in tag:
            city_attack_bonus += percent
        elif 'when attacking' in tag:
            attack_bonus += percent
        elif 'when defending' in tag:
            defend_bonus += percent
        else:
            # Generic "vs ..." (including specific unit classes) -> attack_vs
            attack_vs_bonus += percent

    # Paradrop detection
    paradrop_able = 'paradrop' in text or 'paratroop' in text or 'paratrooper' in text

    # Must set up detection
    must_set_up = 'must set up to ranged attack' in text or 'must set up' in text or 'must set up to' in text

    # Self-destruct detection
    self_destructs = 'self-destruct' in text or 'self destruct' in text or 'suicide' in text or 'explodes when attacking' in text

    # Extra attacks detection (heuristic variations)
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

    # Ranged naval detection
    unit_type = (unit.get('unitType') or '').lower()
    ranged_strength = unit.get('rangedStrength', 0)
    naval_indicators = ['water', 'submarine', 'aircraft carrier', 'carrier', 'ship', 'melee water', 'ranged water']
    is_ranged_naval = (ranged_strength and ranged_strength > 0) and any(k in unit_type for k in naval_indicators)

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
