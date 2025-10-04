"""Convenience launcher for the PyNetworkGT GUI."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if SRC.exists() and str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from pynetworkgt_app.__main__ import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
