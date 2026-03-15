"""Pytest configuration and shared fixtures."""

import os
import sys
import tempfile
from pathlib import Path

import pytest

# Ensure project root is on path so "src" package resolves
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))


@pytest.fixture
def notification_db_path():
    """Temp DB path for notification routing tests. Cleared between tests."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    try:
        os.unlink(path)
    except OSError:
        pass
