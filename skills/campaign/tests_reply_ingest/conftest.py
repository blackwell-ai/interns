"""Repo root + toolbox src on sys.path so tests can import skill modules.
Throwaway suite for the Railway reply-ingestion fix; delete once confirmed in prod."""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
for _p in (str(_ROOT), str(_ROOT / "toolbox" / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
