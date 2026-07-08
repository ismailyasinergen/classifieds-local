#!/usr/bin/env python3
"""
LARGE_ACTIVE_VIEW_REFACTOR_PLANNING_V140_WRAPPER

Root-level convenience wrapper for the backend-visible v140 audit module.
"""

from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from listings.large_view_refactor_audit_v140 import main


if __name__ == "__main__":
    raise SystemExit(main())
