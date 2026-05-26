"""Pytest configuration for the backend test suite.

Ensures the backend package root is on ``sys.path`` so tests can import
``application`` and ``infrastructure`` modules without a separate install step.
"""

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
