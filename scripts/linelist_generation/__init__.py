"""Linelist generation: ascertainment-biased case logs from ABM output.

The modules here use flat imports (``from rucc_utils import ...``) so they can
be run directly as scripts, which is how they have always been used. Adding
this directory to sys.path on package import keeps that working when the code
is instead imported as ``linelist_generation.*`` from an installed wheel.
"""

import os as _os
import sys as _sys

_here = _os.path.dirname(_os.path.abspath(__file__))
if _here not in _sys.path:
    _sys.path.insert(0, _here)
