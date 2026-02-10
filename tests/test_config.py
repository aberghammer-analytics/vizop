"""Tests for vizop.core.config."""

import pytest
from pydantic import ValidationError

from vizop.core.config import VizopConfig, configure, get_config, reset_config


@pytest.fixture(autouse=True)
def _clean_config():
    """Reset config before each test."""
    reset_config()
    yield
    reset_config()


def test_default_config_values():
    cfg = get_config()
    assert cfg.accent_color == "#4E79A7"
    assert cfg.font == "Inter"
    assert cfg.background == "white"
    assert cfg.size == "standard"
    assert cfg.source_label is None


def test_configure_updates_values():
    configure(accent_color="#FF0000", font="IBM Plex Sans")
    cfg = get_config()
    assert cfg.accent_color == "#FF0000"
    assert cfg.font == "IBM Plex Sans"


def test_configure_preserves_other_values():
    configure(accent_color="#FF0000")
    cfg = get_config()
    assert cfg.font == "Inter"  # unchanged


def test_invalid_background_raises():
    with pytest.raises(ValidationError):
        configure(background="dark")


def test_invalid_size_raises():
    with pytest.raises(ValidationError):
        configure(size="huge")


def test_reset_config_restores_defaults():
    configure(font="Source Sans Pro")
    reset_config()
    cfg = get_config()
    assert cfg.font == "Inter"


def test_get_config_returns_same_instance():
    cfg1 = get_config()
    cfg2 = get_config()
    assert cfg1 is cfg2


def test_vizop_config_model_directly():
    cfg = VizopConfig(accent_color="#000000", background="light_gray", size="wide")
    assert cfg.accent_color == "#000000"
    assert cfg.background == "light_gray"
    assert cfg.size == "wide"
