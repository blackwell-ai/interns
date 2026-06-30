"""Put repo root + toolbox src on sys.path so the test can import skill modules.

This folder is a throwaway test suite for the Hunter-credit-burn fix
(_hunter_credits NameError + sourcing circuit breaker). Delete after merge.
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_TOOLBOX_SRC = _ROOT / "toolbox" / "src"

for _p in (str(_ROOT), str(_TOOLBOX_SRC)):
    if _p not in sys.path:
        sys.path.insert(0, _p)
