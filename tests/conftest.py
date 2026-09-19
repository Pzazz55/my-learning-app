"""Pytest configuration and fixtures for the learning application."""

import pytest
from pathlib import Path
import sys

# Add the project root to the path so we can import modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def base_dir():
    """Fixture to provide the base directory of the project."""
    return Path(__file__).parent.parent


@pytest.fixture
def config_dir(base_dir):
    """Fixture to provide the config directory."""
    return base_dir / "config"