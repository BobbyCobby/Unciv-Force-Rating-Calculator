# Unciv Force Rating Calculator

This Python script computes the Base Unit Force of a unit in a Unciv mod.

The calculations are based on:
https://yairm210.github.io/Unciv/Other/Force-rating-calculation/#base-unit-force-evaluation

This repository contains:
- main.py — interactive CLI and compute_base_force function
- uniques_parser.py — heuristic parser for common Unit 'uniques' strings
- test_units.py — harness to compare computed Base Unit Force against
  the values in Unciv's docs/Other/Force-rating-calculation.md (uses the specified commit)
- user_input.py, math_stuff.py — small helpers

Notes:
- The parser is best-effort; some uniques are free-form and require additional rules.
- This tool computes Base Unit Force only (not per-unit promotions * health or civ aggregation).
