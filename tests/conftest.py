"""Pytest configuration and shared fixtures."""

import sys
from pathlib import Path

# Ensure project root is on path so "src" package resolves
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))
