"""Tests for vizop.core.palettes."""

import pytest

from vizop.core.palettes import HIGHLIGHT_MUTED_COLOR, get_colors, get_palette


def test_default_palette_exists():
    colors = get_palette("default")
    assert len(colors) == 10


def test_all_palettes_are_nonempty():
    for name in ("default", "warm", "cool", "diverging", "muted"):
        assert len(get_palette(name)) > 0


def test_unknown_palette_raises():
    with pytest.raises(ValueError, match="Unknown palette 'nope'"):
        get_palette("nope")


def test_get_colors_returns_correct_count():
    assert len(get_colors(3)) == 3
    assert len(get_colors(1)) == 1


def test_get_colors_with_accent_override():
    colors = get_colors(3, accent_color="#FF0000")
    assert colors[0] == "#FF0000"


def test_get_colors_cycles_for_large_n():
    colors = get_colors(15)
    assert len(colors) == 15


def test_highlight_muted_color():
    assert HIGHLIGHT_MUTED_COLOR == "#D3D3D3"
