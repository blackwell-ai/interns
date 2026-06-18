"""Put the repo root and toolbox src on sys.path so tests can import skill modules."""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_TOOLBOX_SRC = _ROOT / "toolbox" / "src"

for _p in (str(_ROOT), str(_TOOLBOX_SRC)):
    if _p not in sys.path:
        sys.path.insert(0, _p)
