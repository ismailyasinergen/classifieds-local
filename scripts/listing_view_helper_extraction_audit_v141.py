#!/usr/bin/env python3
"""
LISTING_VIEW_HELPER_EXTRACTION_CANDIDATE_LOCK_V141_WRAPPER

Root-level convenience wrapper for the backend-visible v141 audit module.
"""

from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from listings.listing_view_helper_extraction_audit_v141 import main


if __name__ == "__main__":
    raise SystemExit(main())
