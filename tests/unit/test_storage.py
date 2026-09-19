"""Unit tests for storage functionality."""

import pytest
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# Add the project root to the path so we can import modules
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def test_database_url_default():
    """Test that database URL defaults to SQLite when not configured."""
    with patch.dict('os.environ', {}, clear=True):
        from backend.services.storage import database_url
        url = database_url()
        assert url.startswith("sqlite:///")


def test_storage_backend_label():
    """Test that backend label is generated correctly."""
    from backend.services.storage import backend_label
    label = backend_label()
    assert isinstance(label, str)
    assert len(label) > 0