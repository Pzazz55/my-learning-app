"""Integration tests for backend services."""

import pytest
import sys
from pathlib import Path

# Add the project root to the path so we can import modules
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def test_load_topics_integration():
    """Test that topics can be loaded from the backend service."""
    from backend.services.llm_backend import load_topics
    topics = load_topics()
    assert isinstance(topics, dict)
    assert "subjects" in topics or "schools" in topics


def test_load_config_integration():
    """Test that config can be loaded from the backend service."""
    from backend.services.llm_backend import load_config
    config = load_config()
    assert isinstance(config, dict)
    assert "timezone" in config or "zone" in config


def test_load_locations_integration():
    """Test that locations can be loaded from the backend service."""
    from backend.services.llm_backend import load_locations
    locations = load_locations()
    assert isinstance(locations, dict)