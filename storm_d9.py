#!/usr/bin/env python3
"""D9 -- Storm --exact on the kt1b_d9 models (same comparison as storm_check.py, which is
driven by kt1b_results.csv; this reads kt1b_d9_results.csv and writes storm_d9_results.csv)."""
import os, runpy, sys
from pathlib import Path
H = Path(__file__).resolve().parent
src = (H / "storm_check.py").read_text()
src = src.replace('"kt1b_results.csv"', '"kt1b_d9_results.csv"').replace('"storm_results.csv"', '"storm_d9_results.csv"')
assert src.count("kt1b_d9_results.csv") == 1 and src.count("storm_d9_results.csv") >= 1
exec(compile(src, str(H / "storm_check.py"), "exec"), {"__name__": "__main__", "__file__": str(H / "storm_check.py")})
