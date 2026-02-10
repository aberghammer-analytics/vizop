"""Tests for vizop.core.theme."""

import matplotlib
import matplotlib.pyplot as plt

from vizop.core.config import VizopConfig, reset_config
from vizop.core.theme import BACKGROUND_COLORS, LAYOUT, SIZES, TYPOGRAPHY, apply_theme

matplotlib.use("Agg")


class TestConstants:
    def test_sizes_contains_all_presets(self):
        assert set(SIZES.keys()) == {"standard", "wide", "tall"}

    def test_standard_size_dimensions(self):
        assert SIZES["standard"].width == 8.0
        assert SIZES["standard"].height == 5.5

    def test_background_colors(self):
        assert BACKGROUND_COLORS["white"] == "#ffffff"
        assert BACKGROUND_COLORS["light_gray"] == "#f5f5f5"

    def test_typography_defaults(self):
        assert TYPOGRAPHY.title_size == 18.0
        assert TYPOGRAPHY.title_weight == "bold"

    def test_layout_defaults(self):
        assert LAYOUT.line_width == 2.5
        assert LAYOUT.bar_width == 0.7


class TestApplyTheme:
    def setup_method(self):
        reset_config()

    def teardown_method(self):
        reset_config()
        plt.close("all")

    def test_removes_top_and_right_spines(self):
        fig, ax = plt.subplots()
        ax.plot([1, 2], [1, 2])
        apply_theme(fig, ax)
        assert not ax.spines["top"].get_visible()
        assert not ax.spines["right"].get_visible()

    def test_left_and_bottom_spines_visible(self):
        fig, ax = plt.subplots()
        ax.plot([1, 2], [1, 2])
        apply_theme(fig, ax)
        assert ax.spines["left"].get_visible()
        assert ax.spines["bottom"].get_visible()

    def test_figure_size_matches_config(self):
        fig, ax = plt.subplots()
        ax.plot([1, 2], [1, 2])
        config = VizopConfig(size="wide")
        apply_theme(fig, ax, config=config)
        w, h = fig.get_size_inches()
        assert w == SIZES["wide"].width
        assert h == SIZES["wide"].height

    def test_background_color_white(self):
        fig, ax = plt.subplots()
        ax.plot([1, 2], [1, 2])
        apply_theme(fig, ax)
        assert matplotlib.colors.to_hex(fig.get_facecolor()) == "#ffffff"

    def test_background_color_light_gray(self):
        fig, ax = plt.subplots()
        ax.plot([1, 2], [1, 2])
        config = VizopConfig(background="light_gray")
        apply_theme(fig, ax, config=config)
        assert matplotlib.colors.to_hex(fig.get_facecolor()) == "#f5f5f5"

    def test_title_is_left_aligned(self):
        fig, ax = plt.subplots()
        ax.plot([1, 2], [1, 2])
        apply_theme(fig, ax, title="Test Title")
        # loc="left" stores the title in _left_title, not the center title
        left_title = ax._left_title
        assert left_title.get_text() == "Test Title"
        plt.close(fig)

    def test_horizontal_gridlines_only(self):
        fig, ax = plt.subplots()
        ax.plot([1, 2], [1, 2])
        apply_theme(fig, ax, gridlines="horizontal")
        # y-axis grid should be on, x-axis should be off
        assert ax.yaxis.get_gridlines()[0].get_visible()

    def test_both_gridlines(self):
        fig, ax = plt.subplots()
        ax.plot([1, 2], [1, 2])
        apply_theme(fig, ax, gridlines="both")
        assert ax.yaxis.get_gridlines()[0].get_visible()
        assert ax.xaxis.get_gridlines()[0].get_visible()
