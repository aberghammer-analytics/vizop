"""Tests for vizop.charts.bar."""

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

import vizop
from vizop import Annotation
from vizop.charts.bar import bar
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
def single_df() -> pd.DataFrame:
    """Simple single-series bar data."""
    return pd.DataFrame(
        {"country": ["US", "UK", "Germany", "France"], "gdp": [21000, 2800, 3800, 2700]}
    )


@pytest.fixture()
def wide_df() -> pd.DataFrame:
    """Wide-format multi-series bar data."""
    return pd.DataFrame(
        {
            "region": ["North", "South", "East"],
            "sales": [100, 80, 120],
            "costs": [60, 70, 50],
        }
    )


@pytest.fixture()
def long_df() -> pd.DataFrame:
    """Long-format grouped bar data."""
    return pd.DataFrame(
        {
            "category": ["A", "A", "B", "B", "C", "C"],
            "value": [100, 60, 80, 90, 120, 40],
            "product": ["X", "Y", "X", "Y", "X", "Y"],
        }
    )


# ---------------------------------------------------------------------------
# Smoke tests
# ---------------------------------------------------------------------------


class TestSmoke:
    def test_single_series_returns_chart(self, single_df):
        chart = bar(single_df, x="country", y="gdp")
        assert isinstance(chart, Chart)

    def test_base64_output(self, single_df):
        chart = bar(single_df, x="country", y="gdp")
        b64 = chart.to_base64()
        assert isinstance(b64, str)
        assert len(b64) > 100

    def test_accessible_via_vizop_namespace(self, single_df):
        chart = vizop.bar(single_df, x="country", y="gdp")
        assert isinstance(chart, Chart)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestValidation:
    def test_empty_dataframe_raises(self):
        df = pd.DataFrame({"x": [], "y": []})
        with pytest.raises(ValueError, match="DataFrame is empty"):
            bar(df, x="x", y="y")

    def test_missing_x_column_raises(self, single_df):
        with pytest.raises(ValueError, match="Column 'missing'.*Available"):
            bar(single_df, x="missing", y="gdp")

    def test_missing_y_column_raises(self, single_df):
        with pytest.raises(ValueError, match="Column 'missing'.*Available"):
            bar(single_df, x="country", y="missing")

    def test_missing_y_list_column_raises(self, single_df):
        with pytest.raises(ValueError, match="Column 'nope'.*Available"):
            bar(single_df, x="country", y=["gdp", "nope"])

    def test_missing_group_column_raises(self, single_df):
        with pytest.raises(ValueError, match="Column 'grp'.*Available"):
            bar(single_df, x="country", y="gdp", group="grp")

    def test_y_list_and_group_mutually_exclusive(self, long_df):
        with pytest.raises(ValueError, match="Cannot use both"):
            bar(long_df, x="category", y=["value", "product"], group="product")

    def test_invalid_orientation_raises(self, single_df):
        with pytest.raises(ValueError, match="Invalid orientation"):
            bar(single_df, x="country", y="gdp", orientation="diagonal")

    def test_invalid_mode_raises(self, single_df):
        with pytest.raises(ValueError, match="Invalid mode"):
            bar(single_df, x="country", y="gdp", mode="exploded")

    def test_invalid_sort_raises(self, single_df):
        with pytest.raises(ValueError, match="Invalid sort"):
            bar(single_df, x="country", y="gdp", sort="random")

    def test_invalid_show_values_raises(self, single_df):
        with pytest.raises(ValueError, match="Invalid show_values"):
            bar(single_df, x="country", y="gdp", show_values="above")

    def test_inside_end_is_valid(self, single_df):
        chart = bar(single_df, x="country", y="gdp", show_values="inside_end")
        assert isinstance(chart, Chart)

    def test_max_4_groups_in_grouped_mode(self):
        df = pd.DataFrame(
            {
                "cat": ["A"] * 5,
                "val": [10, 20, 30, 40, 50],
                "grp": ["G1", "G2", "G3", "G4", "G5"],
            }
        )
        with pytest.raises(ValueError, match="at most 4 groups"):
            bar(df, x="cat", y="val", group="grp", mode="grouped")

    def test_5_groups_ok_in_stacked_mode(self):
        df = pd.DataFrame(
            {
                "cat": ["A"] * 5,
                "val": [10, 20, 30, 40, 50],
                "grp": ["G1", "G2", "G3", "G4", "G5"],
            }
        )
        chart = bar(df, x="cat", y="val", group="grp", mode="stacked")
        assert isinstance(chart, Chart)


# ---------------------------------------------------------------------------
# Sorting
# ---------------------------------------------------------------------------


class TestSorting:
    def test_default_descending_sort(self, single_df):
        chart = bar(single_df, x="country", y="gdp")
        ax = chart.fig.axes[0]
        # Horizontal bars: y-axis has categories, top to bottom = largest first
        labels = [t.get_text() for t in ax.get_yticklabels()]
        # After descending sort + horizontal reversal, top label should be largest
        assert labels[0] == "US"

    def test_ascending_sort(self, single_df):
        chart = bar(single_df, x="country", y="gdp", sort="ascending")
        ax = chart.fig.axes[0]
        labels = [t.get_text() for t in ax.get_yticklabels()]
        assert labels[0] == "France"

    def test_sort_none_preserves_order(self):
        df = pd.DataFrame({"name": ["Zara", "Alice", "Mike"], "score": [50, 90, 70]})
        chart = bar(df, x="name", y="score", sort=None)
        ax = chart.fig.axes[0]
        labels = [t.get_text() for t in ax.get_yticklabels()]
        # Horizontal reverses positions, so first label (top) corresponds to last category
        assert set(labels) == {"Zara", "Alice", "Mike"}

    def test_limit_reduces_categories(self, single_df):
        chart = bar(single_df, x="country", y="gdp", limit=2)
        ax = chart.fig.axes[0]
        labels = [t.get_text() for t in ax.get_yticklabels()]
        assert len(labels) == 2


# ---------------------------------------------------------------------------
# Orientation
# ---------------------------------------------------------------------------


class TestOrientation:
    def test_horizontal_default(self, single_df):
        chart = bar(single_df, x="country", y="gdp")
        ax = chart.fig.axes[0]
        # Horizontal bars create patches with non-zero width
        patches = ax.patches
        assert len(patches) == 4
        assert all(p.get_width() > 0 for p in patches)

    def test_vertical_orientation(self, single_df):
        chart = bar(single_df, x="country", y="gdp", orientation="vertical")
        ax = chart.fig.axes[0]
        patches = ax.patches
        assert len(patches) == 4
        assert all(p.get_height() > 0 for p in patches)

    def test_vertical_has_category_labels_on_x(self, single_df):
        chart = bar(single_df, x="country", y="gdp", orientation="vertical")
        ax = chart.fig.axes[0]
        labels = [t.get_text() for t in ax.get_xticklabels()]
        assert "US" in labels


# ---------------------------------------------------------------------------
# Single series
# ---------------------------------------------------------------------------


class TestSingleSeries:
    def test_correct_number_of_bars(self, single_df):
        chart = bar(single_df, x="country", y="gdp")
        ax = chart.fig.axes[0]
        assert len(ax.patches) == 4

    def test_title_left_aligned(self, single_df):
        chart = bar(single_df, x="country", y="gdp", title="GDP")
        fig_texts = [t.get_text() for t in chart.fig.texts]
        assert "GDP" in fig_texts

    def test_accent_color_applied(self, single_df):
        chart = bar(single_df, x="country", y="gdp", accent_color="#ff0000")
        ax = chart.fig.axes[0]
        for patch in ax.patches:
            assert matplotlib.colors.to_hex(patch.get_facecolor()) == "#ff0000"


# ---------------------------------------------------------------------------
# Multi-series
# ---------------------------------------------------------------------------


class TestMultiSeries:
    def test_wide_format_grouped(self, wide_df):
        chart = bar(wide_df, x="region", y=["sales", "costs"])
        ax = chart.fig.axes[0]
        # 3 regions × 2 series = 6 bars
        assert len(ax.patches) == 6

    def test_long_format_grouped(self, long_df):
        chart = bar(long_df, x="category", y="value", group="product")
        ax = chart.fig.axes[0]
        # 3 categories × 2 groups = 6 bars
        assert len(ax.patches) == 6

    def test_stacked_mode(self, wide_df):
        chart = bar(wide_df, x="region", y=["sales", "costs"], mode="stacked")
        ax = chart.fig.axes[0]
        assert len(ax.patches) == 6

    def test_legend_present_for_multi(self, wide_df):
        chart = bar(wide_df, x="region", y=["sales", "costs"])
        ax = chart.fig.axes[0]
        legend = ax.get_legend()
        assert legend is not None
        legend_texts = [t.get_text() for t in legend.get_texts()]
        assert "sales" in legend_texts
        assert "costs" in legend_texts

    def test_no_legend_for_single(self, single_df):
        chart = bar(single_df, x="country", y="gdp")
        ax = chart.fig.axes[0]
        assert ax.get_legend() is None


# ---------------------------------------------------------------------------
# Legend position
# ---------------------------------------------------------------------------


class TestLegendPosition:
    def test_legend_top_default(self, wide_df):
        """Default legend="top" renders legend above the chart area."""
        chart = bar(wide_df, x="region", y=["sales", "costs"])
        ax = chart.fig.axes[0]
        legend = ax.get_legend()
        assert legend is not None
        # top uses loc="lower left" with bbox_to_anchor=(0.0, 1.0)
        bbox = legend.get_bbox_to_anchor()
        assert bbox is not None

    def test_legend_bottom(self, wide_df):
        chart = bar(wide_df, x="region", y=["sales", "costs"], legend="bottom")
        ax = chart.fig.axes[0]
        legend = ax.get_legend()
        assert legend is not None
        legend_texts = [t.get_text() for t in legend.get_texts()]
        assert "sales" in legend_texts
        assert "costs" in legend_texts

    def test_legend_right(self, wide_df):
        chart = bar(wide_df, x="region", y=["sales", "costs"], legend="right")
        ax = chart.fig.axes[0]
        legend = ax.get_legend()
        assert legend is not None
        legend_texts = [t.get_text() for t in legend.get_texts()]
        assert "sales" in legend_texts

    def test_legend_false_no_legend(self, wide_df):
        chart = bar(wide_df, x="region", y=["sales", "costs"], legend=False)
        ax = chart.fig.axes[0]
        assert ax.get_legend() is None

    def test_legend_none_no_legend(self, wide_df):
        chart = bar(wide_df, x="region", y=["sales", "costs"], legend=None)
        ax = chart.fig.axes[0]
        assert ax.get_legend() is None

    def test_single_series_legend_ignored(self, single_df):
        """legend="top" is silently ignored for single-series charts."""
        chart = bar(single_df, x="country", y="gdp", legend="top")
        ax = chart.fig.axes[0]
        assert ax.get_legend() is None

    def test_top_legend_with_subtitle_no_overlap(self, wide_df):
        """Top legend with subtitle should not overlap — subtitle must be above legend."""
        chart = bar(
            wide_df,
            x="region",
            y=["sales", "costs"],
            title="Revenue",
            subtitle="By region, 2025",
            legend="top",
        )
        ax = chart.fig.axes[0]
        chart.fig.canvas.draw()
        renderer = chart.fig.canvas.get_renderer()

        # Find subtitle text object (figure-level text tagged with _vizop_type)
        subtitle_obj = None
        for t in chart.fig.texts:
            if t.get_text() == "By region, 2025":
                subtitle_obj = t
                break
        assert subtitle_obj is not None, "Subtitle text not found"

        legend = ax.get_legend()
        assert legend is not None, "Legend not found"

        subtitle_bbox = subtitle_obj.get_window_extent(renderer=renderer)
        legend_bbox = legend.get_window_extent(renderer=renderer)

        # Subtitle bottom edge must be at or above legend top edge (pixel y increases upward)
        assert subtitle_bbox.y0 >= legend_bbox.y1, (
            f"Subtitle overlaps legend: subtitle bottom={subtitle_bbox.y0:.1f}, "
            f"legend top={legend_bbox.y1:.1f}"
        )

    def test_invalid_legend_raises(self, single_df):
        with pytest.raises(ValueError, match="Invalid legend"):
            bar(single_df, x="country", y="gdp", legend="left")


# ---------------------------------------------------------------------------
# Show values
# ---------------------------------------------------------------------------


class TestShowValues:
    def test_outside_labels_drawn(self, single_df):
        chart = bar(single_df, x="country", y="gdp", show_values="outside")
        ax = chart.fig.axes[0]
        texts = [t.get_text().strip() for t in ax.texts if t.get_text().strip()]
        # Should have value labels for each bar
        assert len(texts) >= 4

    def test_inside_labels_drawn(self, single_df):
        chart = bar(single_df, x="country", y="gdp", show_values="inside")
        ax = chart.fig.axes[0]
        texts = [t.get_text().strip() for t in ax.texts if t.get_text().strip()]
        assert len(texts) >= 4

    def test_vertical_show_values(self, single_df):
        chart = bar(
            single_df, x="country", y="gdp", orientation="vertical", show_values="outside"
        )
        ax = chart.fig.axes[0]
        texts = [t.get_text().strip() for t in ax.texts if t.get_text().strip()]
        assert len(texts) >= 4

    def test_inside_end_labels_drawn(self, single_df):
        chart = bar(single_df, x="country", y="gdp", show_values="inside_end")
        ax = chart.fig.axes[0]
        texts = [t.get_text().strip() for t in ax.texts if t.get_text().strip()]
        assert len(texts) >= 4

    def test_inside_end_vertical(self, single_df):
        chart = bar(
            single_df, x="country", y="gdp", orientation="vertical", show_values="inside_end"
        )
        ax = chart.fig.axes[0]
        texts = [t.get_text().strip() for t in ax.texts if t.get_text().strip()]
        assert len(texts) >= 4


# ---------------------------------------------------------------------------
# Reference line
# ---------------------------------------------------------------------------


class TestReferenceLine:
    def test_horizontal_reference_line(self, single_df):
        chart = bar(single_df, x="country", y="gdp", reference_line=5000)
        ax = chart.fig.axes[0]
        # axvline adds a line to the axes
        assert len(ax.lines) >= 1

    def test_vertical_reference_line(self, single_df):
        chart = bar(
            single_df, x="country", y="gdp", orientation="vertical", reference_line=5000
        )
        ax = chart.fig.axes[0]
        assert len(ax.lines) >= 1

    def test_reference_line_with_label(self, single_df):
        chart = bar(
            single_df,
            x="country",
            y="gdp",
            reference_line=5000,
            reference_line_label="Target",
        )
        ax = chart.fig.axes[0]
        texts = [t.get_text() for t in ax.texts]
        assert "Target" in texts


# ---------------------------------------------------------------------------
# Highlight
# ---------------------------------------------------------------------------


class TestHighlight:
    def test_single_series_highlight_category(self, single_df):
        chart = bar(single_df, x="country", y="gdp", highlight="US")
        ax = chart.fig.axes[0]
        # US bar should be colored, others muted
        colors = [matplotlib.colors.to_hex(p.get_facecolor()) for p in ax.patches]
        muted = HIGHLIGHT_MUTED_COLOR.lower()
        assert any(c != muted for c in colors)
        assert any(c == muted for c in colors)

    def test_multi_series_highlight_group(self, long_df):
        chart = bar(long_df, x="category", y="value", group="product", highlight="X")
        ax = chart.fig.axes[0]
        # Check legend to identify which series is highlighted
        legend = ax.get_legend()
        assert legend is not None

    def test_highlight_multiple(self, single_df):
        chart = bar(single_df, x="country", y="gdp", highlight=["US", "Germany"])
        ax = chart.fig.axes[0]
        colors = [matplotlib.colors.to_hex(p.get_facecolor()) for p in ax.patches]
        muted = HIGHLIGHT_MUTED_COLOR.lower()
        # 2 highlighted, 2 muted
        assert colors.count(muted) == 2


# ---------------------------------------------------------------------------
# Color map
# ---------------------------------------------------------------------------


class TestColorMap:
    def test_single_series_color_map(self, single_df):
        chart = bar(
            single_df,
            x="country",
            y="gdp",
            color_map={"US": "#ff0000", "UK": "#0000ff"},
        )
        assert isinstance(chart, Chart)

    def test_multi_series_color_map(self, long_df):
        chart = bar(
            long_df,
            x="category",
            y="value",
            group="product",
            color_map={"X": "#ff0000", "Y": "#0000ff"},
        )
        assert isinstance(chart, Chart)

    def test_warning_on_unknown_color_map_keys(self, single_df):
        with pytest.warns(UserWarning, match="color_map contains keys not found"):
            bar(
                single_df,
                x="country",
                y="gdp",
                color_map={"US": "#ff0000", "Mars": "#00ff00"},
            )


# ---------------------------------------------------------------------------
# Theme integration
# ---------------------------------------------------------------------------


class TestThemeIntegration:
    def test_no_top_or_right_spines(self, single_df):
        chart = bar(single_df, x="country", y="gdp")
        ax = chart.fig.axes[0]
        assert not ax.spines["top"].get_visible()
        assert not ax.spines["right"].get_visible()

    def test_gridlines_off_by_default(self, single_df):
        chart = bar(single_df, x="country", y="gdp")
        ax = chart.fig.axes[0]
        assert not ax.xaxis.get_gridlines()[0].get_visible()

    def test_gridlines_on_horizontal(self, single_df):
        chart = bar(single_df, x="country", y="gdp", gridlines=True)
        ax = chart.fig.axes[0]
        # Horizontal bars: value axis gridlines should be on x-axis
        assert ax.xaxis.get_gridlines()[0].get_visible()

    def test_gridlines_on_vertical(self, single_df):
        chart = bar(single_df, x="country", y="gdp", orientation="vertical", gridlines=True)
        ax = chart.fig.axes[0]
        # Vertical bars: value axis gridlines should be on y-axis
        assert ax.yaxis.get_gridlines()[0].get_visible()

    def test_size_override(self, single_df):
        chart = bar(single_df, x="country", y="gdp", size="wide")
        w, h = chart.fig.get_size_inches()
        assert w == pytest.approx(11.0)
        assert h == pytest.approx(5.0)


# ---------------------------------------------------------------------------
# Annotations
# ---------------------------------------------------------------------------


class TestAnnotations:
    def test_basic_annotation(self, single_df):
        # Categories map to integer positions; "US" is at some index
        chart = bar(
            single_df,
            x="country",
            y="gdp",
            annotate=[Annotation(x=0, label="Largest", y=21000)],
        )
        ax = chart.fig.axes[0]
        texts = [t.get_text() for t in ax.texts]
        assert "Largest" in texts

    def test_empty_annotate_list(self, single_df):
        chart = bar(single_df, x="country", y="gdp", annotate=[])
        assert isinstance(chart, Chart)
