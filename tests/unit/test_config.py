"""Unit tests for configuration loading."""

import pytest
from pathlib import Path
import json
import sys

# Add the project root to the path so we can import modules
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def test_config_files_exist(config_dir):
    """Test that configuration files exist."""
    assert (config_dir / "config.json").exists()
    assert (config_dir / "topics.json").exists()
    assert (config_dir / "models.json").exists()
    assert (config_dir / "locations.json").exists()


def test_config_json_structure(config_dir):
    """Test that config.json has the expected structure."""
    config_path = config_dir / "config.json"
    with open(config_path) as f:
        config = json.load(f)
    
    assert isinstance(config, dict)
    assert "timezone" in config or "defaults" in config


def test_topics_json_structure(config_dir):
    """Test that topics.json has the expected structure."""
    topics_path = config_dir / "topics.json"
    with open(topics_path) as f:
        topics = json.load(f)
    
    assert isinstance(topics, dict)
    # Should have at least one of the expected sections
    expected_sections = ["schools", "default", "grades", "subjects"]
    has_valid_section = any(section in topics for section in expected_sections)
    assert has_valid_section