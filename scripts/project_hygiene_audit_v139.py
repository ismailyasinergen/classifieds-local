#!/usr/bin/env python3
"""
PROJECT_HYGIENE_AUDIT_CLEANUP_V139_WRAPPER

Root-level convenience wrapper for the backend-visible audit module.
The actual implementation lives in backend/listings/project_hygiene_audit_v139.py
so Docker/Django tests can import it from /app/listings.
"""

from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from listings.project_hygiene_audit_v139 import main


if __name__ == "__main__":
    raise SystemExit(main())
