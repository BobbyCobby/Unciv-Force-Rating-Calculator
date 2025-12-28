"""
uniques_parser.py

Heuristic parser for Unciv unit 'uniques' strings.

- Classifies bracketed percent Strength entries by their explicit tag inside <>.
- Deduplicates bracketed entries.
- Detects paradrop, must-set-up, self-destruct, extra attacks, ranged-naval, and nuclear-weapon uniques.
- Nuclear detection examines uniques/promotions text (no hardcoded unit name list).
"""
import re

def parse_unit_modifiers(unit):
    uniques_list = unit.get('uniques') or []
    promotions = unit.get('promotions') or []
    text = " ".join(uniques_list + promotions).lower()

    # Collect bracketed "percent Strength <tag>" entries and dedupe
    percent_entries = set()
    for m in re.finditer(r'\[([+-]?\d+)\]\s*%?\s*strength\s*<([^>]+)>', text, flags=re.IGNORECASE):
        try:
            percent = float(m.group(1))
        except ValueError:
            continue
        tag = m.group(2).strip().lower()
        percent_entries.add((percent, tag))

    city_attack_bonus = 0.0
    attack_vs_bonus = 0.0
    attack_bonus = 0.0
    defend_bonus = 0.0

    for percent, tag in percent_entries:
        if 'city' in tag:
            city_attack_bonus += percent
        elif 'when attacking' in tag:
            attack_bonus += percent
        elif 'when defending' in tag:
            defend_bonus += percent
        else:
            attack_vs_bonus += percent

    # Simple flags
    paradrop_able = 'paradrop' in text or 'paratroop' in text or 'paratrooper' in text
    must_set_up = 'must set up to ranged attack' in text or 'must set up' in text or 'must set up to' in text
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

    # Ranged naval detection: unitType containing water/submarine/carrier etc. AND rangedStrength present
    unit_type = (unit.get('unitType') or '').lower()
    ranged_strength = unit.get('rangedStrength', 0)
    naval_indicators = ['water', 'submarine', 'carrier', 'ship', 'melee water', 'ranged water']
    is_ranged_naval = (ranged_strength and ranged_strength > 0) and any(k in unit_type for k in naval_indicators)

    # Nuclear detection (inspect uniques/promotions text, heuristic)
    nuke_patterns = [
        r'\bnuclear missile\b',
        r'\batomic bomb\b',
        r'\bnuclear weapon\b',
        r'\bnuke\b',
        r'\bnuclear\b',
        r'\batomic\b'
    ]
    is_nuke = False
    for p in nuke_patterns:
        if re.search(p, text):
            is_nuke = True
            break

    return {
        'city_attack_bonus': city_attack_bonus,
        'attack_vs_bonus': attack_vs_bonus,
        'attack_bonus': attack_bonus,
        'defend_bonus': defend_bonus,
        'paradrop_able': paradrop_able,
        'must_set_up': must_set_up,
        'self_destructs': self_destructs,
        'extra_attacks': extra_attacks,
        'is_ranged_naval': is_ranged_naval,
        'is_nuke': is_nuke
    }
