"""Tests for vizop.core.fonts."""

import vizop.core.fonts as fonts_module
from vizop.core.config import VizopConfig
from vizop.core.fonts import get_font_family, register_fonts


def test_register_fonts_runs_without_error():
    # Reset registration state so it actually runs
    fonts_module._fonts_registered = False
    register_fonts()
    assert fonts_module._fonts_registered is True


def test_register_fonts_idempotent():
    register_fonts()
    register_fonts()  # should be a no-op


def test_get_font_family_returns_configured_font():
    register_fonts()
    cfg = VizopConfig(font="Inter")
    assert get_font_family(cfg) == "Inter"


def test_get_font_family_returns_libre_franklin():
    register_fonts()
    cfg = VizopConfig(font="Libre Franklin")
    assert get_font_family(cfg) == "Libre Franklin"


def test_get_font_family_falls_back_for_unknown():
    register_fonts()
    cfg = VizopConfig(font="Nonexistent Font 12345")
    result = get_font_family(cfg)
    # Should fall back to Inter (which is bundled)
    assert result == "Inter"
