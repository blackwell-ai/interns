"""Put the repo root and toolbox src on sys.path so tests can import skill modules.

Mirrors skills/campaign/tests/conftest.py. This folder is a throwaway test suite
for the sourcing-ceiling fixes (niche-cap scaling, ICP-hash normalization) and is
meant to be deleted once the next large run is confirmed to fill.
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_TOOLBOX_SRC = _ROOT / "toolbox" / "src"

for _p in (str(_ROOT), str(_TOOLBOX_SRC)):
    if _p not in sys.path:
        sys.path.insert(0, _p)
