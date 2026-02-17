"""Tests for vizop.charts.slope."""

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import pytest

import vizop
from vizop.charts.slope import slope
from vizop.core.chart import Chart
from vizop.core.config import reset_config
from vizop.core.palettes import HIGHLIGHT_MUTED_COLOR

matplotlib.use("Agg")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _cleanup():
    """Reset config and close all figures after each test."""
    yield
    reset_config()
    plt.close("all")


@pytest.fixture()
def wide_df() -> pd.DataFrame:
    """Wide-format slope data: each row is an entity."""
    return pd.DataFrame(
        {
            "country": ["US", "UK", "Germany", "France"],
            "2020": [100, 80, 90, 70],
            "2024": [120, 75, 95, 85],
        }
    )


@pytest.fixture()
def long_df() -> pd.DataFrame:
    """Long-format slope data: two rows per entity."""
    return pd.DataFrame(
        {
            "year": [2020, 2024, 2020, 2024, 2020, 2024],
            "gdp": [100, 120, 80, 75, 90, 95],
            "country": ["US", "US", "UK", "UK", "Germany", "Germany"],
        }
    )


# ---------------------------------------------------------------------------
# Smoke tests
# ---------------------------------------------------------------------------


class TestSmoke:
    def test_wide_format_returns_chart(self, wide_df):
        chart = slope(wide_df, label="country", left="2020", right="2024")
        assert isinstance(chart, Chart)

    def test_long_format_returns_chart(self, long_df):
        chart = slope(long_df, x="year", y="gdp", group="country")
        assert isinstance(chart, Chart)

    def test_base64_output(self, wide_df):
        chart = slope(wide_df, label="country", left="2020", right="2024")
        b64 = chart.to_base64()
        assert isinstance(b64, str)
        assert len(b64) > 100

    def test_accessible_via_vizop_namespace(self, wide_df):
        chart = vizop.slope(wide_df, label="country", left="2020", right="2024")
        assert isinstance(chart, Chart)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestValidation:
    def test_empty_dataframe_raises(self):
        df = pd.DataFrame({"label": [], "a": [], "b": []})
        with pytest.raises(ValueError, match="DataFrame is empty"):
            slope(df, label="label", left="a", right="b")

    def test_missing_label_column_raises(self, wide_df):
        with pytest.raises(ValueError, match="Column 'missing'.*Available"):
            slope(wide_df, label="missing", left="2020", right="2024")

    def test_missing_left_column_raises(self, wide_df):
        with pytest.raises(ValueError, match="Column 'missing'.*Available"):
            slope(wide_df, label="country", left="missing", right="2024")

    def test_missing_right_column_raises(self, wide_df):
        with pytest.raises(ValueError, match="Column 'missing'.*Available"):
            slope(wide_df, label="country", left="2020", right="missing")

    def test_missing_x_column_raises(self, long_df):
        with pytest.raises(ValueError, match="Column 'missing'.*Available"):
            slope(long_df, x="missing", y="gdp", group="country")

    def test_missing_y_column_raises(self, long_df):
        with pytest.raises(ValueError, match="Column 'missing'.*Available"):
            slope(long_df, x="year", y="missing", group="country")

    def test_missing_group_column_raises(self, long_df):
        with pytest.raises(ValueError, match="Column 'missing'.*Available"):
            slope(long_df, x="year", y="gdp", group="missing")

    def test_mixed_format_raises(self, wide_df):
        with pytest.raises(ValueError, match="Cannot mix"):
            slope(
                wide_df, label="country", left="2020", right="2024",
                x="country", y="2020", group="country",
            )

    def test_no_params_raises(self, wide_df):
        with pytest.raises(ValueError, match="Must provide"):
            slope(wide_df)

    def test_incomplete_wide_raises(self, wide_df):
        with pytest.raises(ValueError, match="Wide format requires all three"):
            slope(wide_df, label="country", left="2020")

    def test_incomplete_long_raises(self, long_df):
        with pytest.raises(ValueError, match="Long format requires all three"):
            slope(long_df, x="year", y="gdp")

    def test_long_format_not_2_x_values_raises(self):
        df = pd.DataFrame(
            {
                "year": [2020, 2022, 2024, 2020, 2022, 2024],
                "val": [10, 20, 30, 40, 50, 60],
                "grp": ["A", "A", "A", "B", "B", "B"],
            }
        )
        with pytest.raises(ValueError, match="exactly 2 unique x-values"):
            slope(df, x="year", y="val", group="grp")

    def test_invalid_sort_raises(self, wide_df):
        with pytest.raises(ValueError, match="Invalid sort"):
            slope(wide_df, label="country", left="2020", right="2024", sort="random")


# ---------------------------------------------------------------------------
# Color by direction
# ---------------------------------------------------------------------------


class TestColorByDirection:
    def test_bool_true(self, wide_df):
        chart = slope(wide_df, label="country", left="2020", right="2024", color_by_direction=True)
        ax = chart.fig.axes[0]
        # Should have lines — just verify it renders without error
        assert isinstance(chart, Chart)
        # Check that at least two different colors are used (up vs down)
        line_colors = set()
        for ln in ax.lines:
            color = matplotlib.colors.to_hex(ln.get_color())
            line_colors.add(color)
        # Should have at least 2 colors (up and down, plus spine color)
        assert len(line_colors) >= 2

    def test_custom_dict(self, wide_df):
        chart = slope(
            wide_df,
            label="country",
            left="2020",
            right="2024",
            color_by_direction={"up": "#00ff00", "down": "#ff0000"},
        )
        ax = chart.fig.axes[0]
        line_colors = set()
        for ln in ax.lines:
            color = matplotlib.colors.to_hex(ln.get_color())
            line_colors.add(color)
        assert "#00ff00" in line_colors or "#ff0000" in line_colors


# ---------------------------------------------------------------------------
# Show change
# ---------------------------------------------------------------------------


class TestShowChange:
    def test_show_change_adds_delta(self, wide_df):
        chart = slope(
            wide_df, label="country", left="2020", right="2024", show_change=True
        )
        ax = chart.fig.axes[0]
        texts = [t.get_text() for t in ax.texts]
        # Delta text should contain parentheses with +/- prefix
        assert any("(" in t and ")" in t for t in texts)


# ---------------------------------------------------------------------------
# Highlight
# ---------------------------------------------------------------------------


class TestHighlight:
    def test_highlight_mutes_others(self, wide_df):
        chart = slope(
            wide_df, label="country", left="2020", right="2024", highlight="US"
        )
        ax = chart.fig.axes[0]
        muted = HIGHLIGHT_MUTED_COLOR.lower()
        line_colors = set()
        for ln in ax.lines:
            color = matplotlib.colors.to_hex(ln.get_color())
            # Exclude spine lines (spine color)
            if color != matplotlib.colors.to_hex(HIGHLIGHT_MUTED_COLOR):
                line_colors.add(color)
        # The muted color should appear on at least some lines
        all_colors = [matplotlib.colors.to_hex(ln.get_color()) for ln in ax.lines]
        assert muted in all_colors

    def test_highlight_multiple(self, wide_df):
        chart = slope(
            wide_df,
            label="country",
            left="2020",
            right="2024",
            highlight=["US", "Germany"],
        )
        ax = chart.fig.axes[0]
        muted = HIGHLIGHT_MUTED_COLOR.lower()
        all_colors = [matplotlib.colors.to_hex(ln.get_color()) for ln in ax.lines]
        # Muted color should appear (for UK and France lines)
        assert muted in all_colors


# ---------------------------------------------------------------------------
# Sort and limit
# ---------------------------------------------------------------------------


class TestSortAndLimit:
    def test_sort_ascending(self, wide_df):
        chart = slope(
            wide_df, label="country", left="2020", right="2024", sort="ascending"
        )
        assert isinstance(chart, Chart)

    def test_sort_descending(self, wide_df):
        chart = slope(
            wide_df, label="country", left="2020", right="2024", sort="descending"
        )
        assert isinstance(chart, Chart)

    def test_limit_reduces_entities(self, wide_df):
        chart = slope(
            wide_df, label="country", left="2020", right="2024", limit=2
        )
        ax = chart.fig.axes[0]
        # 2 entities = 2 slope lines + 2 spine lines = 4 lines
        # Plus scatter dots — just check it doesn't have all 4 entities
        # Count slope lines (exclude the 2 vertical spine lines)
        slope_lines = [
            ln for ln in ax.lines
            if ln.get_xdata()[0] != ln.get_xdata()[-1]  # exclude vertical spines
        ]
        assert len(slope_lines) == 2

    def test_warning_on_many_entities(self):
        df = pd.DataFrame(
            {
                "name": [f"Entity{i}" for i in range(20)],
                "start": list(range(20)),
                "end": list(range(1, 21)),
            }
        )
        with pytest.warns(UserWarning, match="Consider using limit"):
            slope(df, label="name", left="start", right="end")


# ---------------------------------------------------------------------------
# Theme integration
# ---------------------------------------------------------------------------


class TestThemeIntegration:
    def test_no_top_or_right_spines(self, wide_df):
        chart = slope(wide_df, label="country", left="2020", right="2024")
        ax = chart.fig.axes[0]
        # All default spines hidden (custom vertical spines drawn manually)
        assert not ax.spines["top"].get_visible()
        assert not ax.spines["right"].get_visible()

    def test_gridlines_off_by_default(self, wide_df):
        chart = slope(wide_df, label="country", left="2020", right="2024")
        ax = chart.fig.axes[0]
        # Slope charts have no y-ticks, so gridlines list may be empty
        gridlines = ax.yaxis.get_gridlines()
        if gridlines:
            assert not gridlines[0].get_visible()

    def test_title_and_subtitle(self, wide_df):
        chart = slope(
            wide_df,
            label="country",
            left="2020",
            right="2024",
            title="GDP Change",
            subtitle="2020 vs 2024",
        )
        fig_texts = [t.get_text() for t in chart.fig.texts]
        assert "GDP Change" in fig_texts
        assert "2020 vs 2024" in fig_texts

    def test_size_override(self, wide_df):
        chart = slope(
            wide_df, label="country", left="2020", right="2024", size="wide"
        )
        w, h = chart.fig.get_size_inches()
        assert w == pytest.approx(11.0)
        assert h == pytest.approx(5.0)


# ---------------------------------------------------------------------------
# Span (figure width)
# ---------------------------------------------------------------------------


class TestSpan:
    def test_default_span_is_medium(self, wide_df):
        chart = slope(wide_df, label="country", left="2020", right="2024")
        w, _ = chart.fig.get_size_inches()
        assert w == pytest.approx(6.0)

    def test_narrow_span(self, wide_df):
        chart = slope(wide_df, label="country", left="2020", right="2024", span="narrow")
        w, _ = chart.fig.get_size_inches()
        assert w == pytest.approx(4.5)

    def test_wide_span(self, wide_df):
        chart = slope(wide_df, label="country", left="2020", right="2024", span="wide")
        w, _ = chart.fig.get_size_inches()
        assert w == pytest.approx(8.0)

    def test_span_preserves_height_from_size(self, wide_df):
        chart = slope(
            wide_df, label="country", left="2020", right="2024",
            span="narrow", size="tall",
        )
        w, h = chart.fig.get_size_inches()
        assert w == pytest.approx(4.5)
        assert h == pytest.approx(8.0)

    def test_size_alone_not_overridden(self, wide_df):
        """When size is set but span is not, size controls width."""
        chart = slope(
            wide_df, label="country", left="2020", right="2024", size="wide"
        )
        w, h = chart.fig.get_size_inches()
        assert w == pytest.approx(11.0)
        assert h == pytest.approx(5.0)

    def test_invalid_span_raises(self, wide_df):
        with pytest.raises(ValueError, match="Invalid span"):
            slope(wide_df, label="country", left="2020", right="2024", span="huge")


# ---------------------------------------------------------------------------
# X-axis labels (show_axes)
# ---------------------------------------------------------------------------


class TestShowAxes:
    def test_x_labels_shown_by_default(self, wide_df):
        chart = slope(wide_df, label="country", left="2020", right="2024")
        ax = chart.fig.axes[0]
        tick_labels = [t.get_text() for t in ax.get_xticklabels()]
        assert "2020" in tick_labels
        assert "2024" in tick_labels

    def test_x_labels_hidden_when_disabled(self, wide_df):
        chart = slope(
            wide_df, label="country", left="2020", right="2024", show_axes=False
        )
        ax = chart.fig.axes[0]
        assert ax.get_xticks().tolist() == []

    def test_x_labels_long_format(self, long_df):
        chart = slope(long_df, x="year", y="gdp", group="country")
        ax = chart.fig.axes[0]
        tick_labels = [t.get_text() for t in ax.get_xticklabels()]
        assert "2020" in tick_labels
        assert "2024" in tick_labels

    def test_x_labels_are_bold(self, wide_df):
        chart = slope(wide_df, label="country", left="2020", right="2024")
        ax = chart.fig.axes[0]
        for label in ax.get_xticklabels():
            assert label.get_fontweight() == "bold"


# ---------------------------------------------------------------------------
# Vertical reference lines (show_verticals)
# ---------------------------------------------------------------------------


class TestShowVerticals:
    def _count_vertical_lines(self, ax):
        """Count lines where x-start equals x-end (vertical)."""
        return sum(1 for ln in ax.lines if ln.get_xdata()[0] == ln.get_xdata()[-1])

    def test_verticals_hidden_by_default(self, wide_df):
        chart = slope(wide_df, label="country", left="2020", right="2024")
        ax = chart.fig.axes[0]
        assert self._count_vertical_lines(ax) == 0

    def test_verticals_shown_when_enabled(self, wide_df):
        chart = slope(
            wide_df, label="country", left="2020", right="2024", show_verticals=True
        )
        ax = chart.fig.axes[0]
        assert self._count_vertical_lines(ax) == 2
