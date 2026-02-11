"""Tests for vizop.charts.line."""

import matplotlib
import matplotlib.collections as mcoll
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

import vizop
from vizop.charts.line import line
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
    """Simple single-series DataFrame."""
    return pd.DataFrame({"year": [2020, 2021, 2022, 2023], "gdp": [100, 110, 105, 120]})


@pytest.fixture()
def wide_df() -> pd.DataFrame:
    """Wide-format multi-series DataFrame."""
    return pd.DataFrame(
        {
            "year": [2020, 2021, 2022],
            "gdp": [100, 110, 120],
            "inflation": [2.1, 3.5, 2.8],
            "unemployment": [5.0, 4.2, 3.8],
        }
    )


@pytest.fixture()
def long_df() -> pd.DataFrame:
    """Long-format grouped DataFrame."""
    return pd.DataFrame(
        {
            "year": [2020, 2021, 2022] * 2,
            "value": [100, 110, 120, 80, 90, 95],
            "country": ["US", "US", "US", "UK", "UK", "UK"],
        }
    )


@pytest.fixture()
def date_df() -> pd.DataFrame:
    """DataFrame with datetime x-axis."""
    dates = pd.date_range("2020-01-01", periods=12, freq="MS")
    return pd.DataFrame({"date": dates, "revenue": np.random.default_rng(42).normal(100, 10, 12)})


# ---------------------------------------------------------------------------
# Smoke tests
# ---------------------------------------------------------------------------


class TestSmoke:
    def test_single_series_returns_chart(self, single_df):
        chart = line(single_df, x="year", y="gdp")
        assert isinstance(chart, Chart)

    def test_base64_output(self, single_df):
        chart = line(single_df, x="year", y="gdp")
        b64 = chart.to_base64()
        assert isinstance(b64, str)
        assert len(b64) > 100

    def test_accessible_via_vizop_namespace(self, single_df):
        chart = vizop.line(single_df, x="year", y="gdp")
        assert isinstance(chart, Chart)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestValidation:
    def test_empty_dataframe_raises(self):
        df = pd.DataFrame({"x": [], "y": []})
        with pytest.raises(ValueError, match="DataFrame is empty"):
            line(df, x="x", y="y")

    def test_missing_x_column_raises(self, single_df):
        with pytest.raises(ValueError, match="Column 'missing'.*Available"):
            line(single_df, x="missing", y="gdp")

    def test_missing_y_column_raises(self, single_df):
        with pytest.raises(ValueError, match="Column 'missing'.*Available"):
            line(single_df, x="year", y="missing")

    def test_missing_y_list_column_raises(self, single_df):
        with pytest.raises(ValueError, match="Column 'nope'.*Available"):
            line(single_df, x="year", y=["gdp", "nope"])

    def test_missing_group_column_raises(self, single_df):
        with pytest.raises(ValueError, match="Column 'grp'.*Available"):
            line(single_df, x="year", y="gdp", group="grp")

    def test_y_list_and_group_mutually_exclusive(self, long_df):
        with pytest.raises(ValueError, match="Cannot use both"):
            line(long_df, x="year", y=["value", "country"], group="country")

    def test_error_message_lists_available_columns(self, single_df):
        with pytest.raises(ValueError, match="'year'"):
            line(single_df, x="nope", y="gdp")


# ---------------------------------------------------------------------------
# Single series rendering
# ---------------------------------------------------------------------------


class TestSingleSeries:
    def test_one_line_drawn(self, single_df):
        chart = line(single_df, x="year", y="gdp")
        ax = chart.fig.axes[0]
        assert len(ax.lines) == 1

    def test_show_area_creates_fill(self, single_df):
        chart = line(single_df, x="year", y="gdp", show_area=True)
        ax = chart.fig.axes[0]
        # fill_between creates a PolyCollection
        poly_collections = [c for c in ax.collections if isinstance(c, mcoll.PolyCollection)]
        assert len(poly_collections) >= 1

    def test_zero_baseline(self, single_df):
        chart = line(single_df, x="year", y="gdp", zero_baseline=True)
        ax = chart.fig.axes[0]
        assert ax.get_ylim()[0] == 0

    def test_show_last_value_adds_annotation(self, single_df):
        chart = line(single_df, x="year", y="gdp", show_last_value=True)
        ax = chart.fig.axes[0]
        # Should have at least one annotation with the last value
        texts = [child for child in ax.get_children() if hasattr(child, "get_text")]
        annotation_texts = [t.get_text() for t in texts if t.get_text()]
        assert any("120" in t for t in annotation_texts)

    def test_title_and_subtitle(self, single_df):
        chart = line(single_df, x="year", y="gdp", title="My Title", subtitle="My Sub")
        ax = chart.fig.axes[0]
        assert ax._left_title.get_text() == "My Title"


# ---------------------------------------------------------------------------
# Multi-series
# ---------------------------------------------------------------------------


class TestMultiSeries:
    def test_wide_format_draws_multiple_lines(self, wide_df):
        chart = line(wide_df, x="year", y=["gdp", "inflation", "unemployment"])
        ax = chart.fig.axes[0]
        assert len(ax.lines) == 3

    def test_long_format_draws_multiple_lines(self, long_df):
        chart = line(long_df, x="year", y="value", group="country")
        ax = chart.fig.axes[0]
        assert len(ax.lines) == 2

    def test_show_area_ignored_for_multi_series(self, wide_df):
        with pytest.warns(UserWarning, match="show_area.*single-series"):
            chart = line(wide_df, x="year", y=["gdp", "inflation"], show_area=True)
        ax = chart.fig.axes[0]
        poly_collections = [c for c in ax.collections if isinstance(c, mcoll.PolyCollection)]
        assert len(poly_collections) == 0

    def test_endpoint_labels_drawn(self, wide_df):
        chart = line(wide_df, x="year", y=["gdp", "inflation"])
        ax = chart.fig.axes[0]
        # Should have annotations for each series
        annotation_texts = [a.get_text() for a in ax.texts]
        assert any("gdp" in t for t in annotation_texts)
        assert any("inflation" in t for t in annotation_texts)


# ---------------------------------------------------------------------------
# Highlight
# ---------------------------------------------------------------------------


class TestHighlight:
    def test_muted_lines_use_highlight_muted_color(self, wide_df):
        chart = line(wide_df, x="year", y=["gdp", "inflation", "unemployment"], highlight="gdp")
        ax = chart.fig.axes[0]
        line_colors = {}
        for ln in ax.lines:
            label = ln.get_label()
            color = matplotlib.colors.to_hex(ln.get_color())
            line_colors[label] = color
        assert line_colors["inflation"] == HIGHLIGHT_MUTED_COLOR.lower()
        assert line_colors["unemployment"] == HIGHLIGHT_MUTED_COLOR.lower()
        assert line_colors["gdp"] != HIGHLIGHT_MUTED_COLOR.lower()

    def test_muted_lines_thinner(self, wide_df):
        chart = line(wide_df, x="year", y=["gdp", "inflation", "unemployment"], highlight="gdp")
        ax = chart.fig.axes[0]
        for ln in ax.lines:
            if ln.get_label() == "gdp":
                assert ln.get_linewidth() == pytest.approx(2.5)
            else:
                assert ln.get_linewidth() == pytest.approx(1.0)

    def test_highlight_multiple_series(self, wide_df):
        chart = line(
            wide_df,
            x="year",
            y=["gdp", "inflation", "unemployment"],
            highlight=["gdp", "inflation"],
        )
        ax = chart.fig.axes[0]
        for ln in ax.lines:
            color = matplotlib.colors.to_hex(ln.get_color())
            if ln.get_label() == "unemployment":
                assert color == HIGHLIGHT_MUTED_COLOR.lower()
            else:
                assert color != HIGHLIGHT_MUTED_COLOR.lower()


# ---------------------------------------------------------------------------
# Highlight range
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Color map
# ---------------------------------------------------------------------------


class TestColorMap:
    def test_basic_mapping(self, long_df):
        chart = line(
            long_df, x="year", y="value", group="country",
            color_map={"US": "#ff0000", "UK": "#0000ff"},
        )
        ax = chart.fig.axes[0]
        line_colors = {}
        for ln in ax.lines:
            line_colors[ln.get_label()] = matplotlib.colors.to_hex(ln.get_color())
        assert line_colors["US"] == "#ff0000"
        assert line_colors["UK"] == "#0000ff"

    def test_unmapped_series_get_gray(self, wide_df):
        chart = line(
            wide_df, x="year", y=["gdp", "inflation", "unemployment"],
            color_map={"gdp": "#ff0000"},
        )
        ax = chart.fig.axes[0]
        line_colors = {}
        for ln in ax.lines:
            line_colors[ln.get_label()] = matplotlib.colors.to_hex(ln.get_color())
        assert line_colors["gdp"] == "#ff0000"
        assert line_colors["inflation"] == HIGHLIGHT_MUTED_COLOR.lower()
        assert line_colors["unemployment"] == HIGHLIGHT_MUTED_COLOR.lower()

    def test_color_map_with_highlight(self, long_df):
        chart = line(
            long_df, x="year", y="value", group="country",
            color_map={"US": "#ff0000", "UK": "#0000ff"},
            highlight="US",
        )
        ax = chart.fig.axes[0]
        for ln in ax.lines:
            color = matplotlib.colors.to_hex(ln.get_color())
            if ln.get_label() == "US":
                assert color == "#ff0000"
                assert ln.get_linewidth() == pytest.approx(2.5)
            else:
                assert color == "#0000ff"
                assert ln.get_linewidth() == pytest.approx(1.0)

    def test_warning_on_unknown_keys(self, long_df):
        with pytest.warns(UserWarning, match="color_map contains keys not found"):
            line(
                long_df, x="year", y="value", group="country",
                color_map={"US": "#ff0000", "Mars": "#00ff00"},
            )

    def test_single_series_color_map_overrides_accent(self, single_df):
        chart = line(
            single_df, x="year", y="gdp",
            accent_color="#999999", color_map={"gdp": "#ff0000"},
        )
        ax = chart.fig.axes[0]
        color = matplotlib.colors.to_hex(ax.lines[0].get_color())
        assert color == "#ff0000"


class TestHighlightRange:
    def test_axvspan_created(self, single_df):
        chart = line(single_df, x="year", y="gdp", highlight_range=(2021, 2022))
        ax = chart.fig.axes[0]
        # axvspan creates a Polygon patch
        patches = ax.patches
        assert len(patches) >= 1

    def test_highlight_range_with_label(self, single_df):
        chart = line(
            single_df,
            x="year",
            y="gdp",
            highlight_range=(2021, 2022),
            highlight_range_label="Recession",
        )
        ax = chart.fig.axes[0]
        texts = [t.get_text() for t in ax.texts]
        assert "Recession" in texts


# ---------------------------------------------------------------------------
# Date handling
# ---------------------------------------------------------------------------


class TestDateAxis:
    def test_datetime_x_no_error(self, date_df):
        chart = line(date_df, x="date", y="revenue")
        assert isinstance(chart, Chart)

    def test_string_dates_converted(self):
        df = pd.DataFrame(
            {
                "date": ["2020-01-01", "2020-02-01", "2020-03-01"],
                "value": [10, 20, 15],
            }
        )
        chart = line(df, x="date", y="value")
        assert isinstance(chart, Chart)


# ---------------------------------------------------------------------------
# Theme integration
# ---------------------------------------------------------------------------


class TestThemeIntegration:
    def test_no_top_or_right_spines(self, single_df):
        chart = line(single_df, x="year", y="gdp")
        ax = chart.fig.axes[0]
        assert not ax.spines["top"].get_visible()
        assert not ax.spines["right"].get_visible()

    def test_gridlines_off_by_default(self, single_df):
        chart = line(single_df, x="year", y="gdp")
        ax = chart.fig.axes[0]
        assert not ax.yaxis.get_gridlines()[0].get_visible()

    def test_gridlines_on(self, single_df):
        chart = line(single_df, x="year", y="gdp", gridlines=True)
        ax = chart.fig.axes[0]
        assert ax.yaxis.get_gridlines()[0].get_visible()

    def test_size_override(self, single_df):
        chart = line(single_df, x="year", y="gdp", size="wide")
        w, h = chart.fig.get_size_inches()
        assert w == pytest.approx(11.0)
        assert h == pytest.approx(5.0)
