"""Tests for vizop.charts.scatter."""

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

import vizop
from vizop import Annotation
from vizop.charts.scatter import scatter
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
def simple_df() -> pd.DataFrame:
    """Simple ungrouped scatter data."""
    return pd.DataFrame(
        {"height": [160, 170, 175, 180, 185], "weight": [55, 65, 70, 80, 90]}
    )


@pytest.fixture()
def grouped_df() -> pd.DataFrame:
    """Grouped scatter data with two categories."""
    return pd.DataFrame(
        {
            "x": [1, 2, 3, 4, 5, 6],
            "y": [10, 20, 15, 25, 30, 35],
            "group": ["A", "A", "A", "B", "B", "B"],
        }
    )


@pytest.fixture()
def labeled_df() -> pd.DataFrame:
    """Small scatter data with a label column."""
    return pd.DataFrame(
        {
            "x": [1, 2, 3, 4, 5],
            "y": [10, 20, 15, 25, 30],
            "name": ["Alpha", "Beta", "Gamma", "Delta", "Epsilon"],
        }
    )


@pytest.fixture()
def sized_df() -> pd.DataFrame:
    """Scatter data with a size column."""
    return pd.DataFrame(
        {
            "x": [1, 2, 3, 4, 5],
            "y": [10, 20, 15, 25, 30],
            "pop": [100, 500, 200, 800, 300],
        }
    )


# ---------------------------------------------------------------------------
# Smoke tests
# ---------------------------------------------------------------------------


class TestSmoke:
    def test_returns_chart(self, simple_df):
        chart = scatter(simple_df, x="height", y="weight")
        assert isinstance(chart, Chart)

    def test_base64_output(self, simple_df):
        chart = scatter(simple_df, x="height", y="weight")
        b64 = chart.to_base64()
        assert isinstance(b64, str)
        assert len(b64) > 100

    def test_accessible_via_vizop_namespace(self, simple_df):
        chart = vizop.scatter(simple_df, x="height", y="weight")
        assert isinstance(chart, Chart)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestValidation:
    def test_empty_dataframe_raises(self):
        df = pd.DataFrame({"x": [], "y": []})
        with pytest.raises(ValueError, match="DataFrame is empty"):
            scatter(df, x="x", y="y")

    def test_missing_x_column_raises(self, simple_df):
        with pytest.raises(ValueError, match="Column 'missing'.*Available"):
            scatter(simple_df, x="missing", y="weight")

    def test_missing_y_column_raises(self, simple_df):
        with pytest.raises(ValueError, match="Column 'missing'.*Available"):
            scatter(simple_df, x="height", y="missing")

    def test_missing_group_column_raises(self, simple_df):
        with pytest.raises(ValueError, match="Column 'grp'.*Available"):
            scatter(simple_df, x="height", y="weight", group="grp")

    def test_missing_size_column_raises(self, simple_df):
        with pytest.raises(ValueError, match="Column 'sz'.*Available"):
            scatter(simple_df, x="height", y="weight", size="sz")

    def test_missing_label_column_raises(self, simple_df):
        with pytest.raises(ValueError, match="Column 'lbl'.*Available"):
            scatter(simple_df, x="height", y="weight", label="lbl")

    def test_too_many_groups_raises(self):
        df = pd.DataFrame(
            {
                "x": range(10),
                "y": range(10),
                "g": [f"G{i}" for i in range(10)],
            }
        )
        with pytest.raises(ValueError, match="Too many groups"):
            scatter(df, x="x", y="y", group="g", max_groups=6)

    def test_invalid_trend_raises(self, simple_df):
        with pytest.raises(ValueError, match="Invalid trend"):
            scatter(simple_df, x="height", y="weight", trend="quadratic")


# ---------------------------------------------------------------------------
# Single series
# ---------------------------------------------------------------------------


class TestSingleSeries:
    def test_one_path_collection(self, simple_df):
        chart = scatter(simple_df, x="height", y="weight")
        ax = chart.fig.axes[0]
        collections = [c for c in ax.collections if isinstance(c, matplotlib.collections.PathCollection)]
        assert len(collections) == 1

    def test_opacity_applied(self, simple_df):
        chart = scatter(simple_df, x="height", y="weight", opacity=0.5)
        ax = chart.fig.axes[0]
        collection = ax.collections[0]
        alphas = collection.get_alpha()
        assert alphas == pytest.approx(0.5)

    def test_jitter_adds_noise(self, simple_df):
        chart_no_jitter = scatter(simple_df, x="height", y="weight", jitter=False)
        chart_jitter = scatter(simple_df, x="height", y="weight", jitter=True)
        ax_no = chart_no_jitter.fig.axes[0]
        ax_yes = chart_jitter.fig.axes[0]
        offsets_no = ax_no.collections[0].get_offsets()
        offsets_yes = ax_yes.collections[0].get_offsets()
        # Jittered positions should differ from original
        assert not np.allclose(offsets_no, offsets_yes)


# ---------------------------------------------------------------------------
# Grouped
# ---------------------------------------------------------------------------


class TestGrouped:
    def test_correct_number_of_collections(self, grouped_df):
        chart = scatter(grouped_df, x="x", y="y", group="group")
        ax = chart.fig.axes[0]
        collections = [c for c in ax.collections if isinstance(c, matplotlib.collections.PathCollection)]
        assert len(collections) == 2

    def test_colors_match_palette(self, grouped_df):
        chart = scatter(grouped_df, x="x", y="y", group="group")
        ax = chart.fig.axes[0]
        collections = [c for c in ax.collections if isinstance(c, matplotlib.collections.PathCollection)]
        # Two groups should have different colors
        color_0 = matplotlib.colors.to_hex(collections[0].get_facecolor()[0])
        color_1 = matplotlib.colors.to_hex(collections[1].get_facecolor()[0])
        assert color_0 != color_1


# ---------------------------------------------------------------------------
# Highlight
# ---------------------------------------------------------------------------


class TestHighlight:
    def test_muted_groups_get_muted_color(self, grouped_df):
        chart = scatter(grouped_df, x="x", y="y", group="group", highlight="A")
        ax = chart.fig.axes[0]
        collections = [c for c in ax.collections if isinstance(c, matplotlib.collections.PathCollection)]
        # One group should be muted (HIGHLIGHT_MUTED_COLOR)
        colors = [matplotlib.colors.to_hex(c.get_facecolor()[0]) for c in collections]
        muted = HIGHLIGHT_MUTED_COLOR.lower()
        assert muted in colors

    def test_highlighted_groups_get_palette_color(self, grouped_df):
        chart = scatter(grouped_df, x="x", y="y", group="group", highlight="A")
        ax = chart.fig.axes[0]
        collections = [c for c in ax.collections if isinstance(c, matplotlib.collections.PathCollection)]
        colors = [matplotlib.colors.to_hex(c.get_facecolor()[0]) for c in collections]
        muted = HIGHLIGHT_MUTED_COLOR.lower()
        assert any(c != muted for c in colors)


# ---------------------------------------------------------------------------
# Trend line
# ---------------------------------------------------------------------------


class TestTrendLine:
    def test_linear_trend_adds_line(self, simple_df):
        chart = scatter(simple_df, x="height", y="weight", trend="linear")
        ax = chart.fig.axes[0]
        assert len(ax.lines) >= 1

    def test_lowess_works_if_statsmodels_installed(self, simple_df):
        try:
            import statsmodels  # noqa: F401

            chart = scatter(simple_df, x="height", y="weight", trend="lowess")
            ax = chart.fig.axes[0]
            assert len(ax.lines) >= 1
        except ImportError:
            pytest.skip("statsmodels not installed")

    def test_lowess_falls_back_to_linear_without_statsmodels(self, simple_df, monkeypatch):
        """If statsmodels is not importable, LOWESS falls back to linear with a warning."""
        import builtins

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if "statsmodels" in name:
                raise ImportError("Mocked")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)
        with pytest.warns(UserWarning, match="statsmodels"):
            chart = scatter(simple_df, x="height", y="weight", trend="lowess")
        ax = chart.fig.axes[0]
        assert len(ax.lines) >= 1


# ---------------------------------------------------------------------------
# Size encoding
# ---------------------------------------------------------------------------


class TestSizeEncoding:
    def test_size_column_produces_variable_sizes(self, sized_df):
        chart = scatter(sized_df, x="x", y="y", size="pop")
        ax = chart.fig.axes[0]
        collection = ax.collections[0]
        sizes = collection.get_sizes()
        # Sizes should vary (not all the same)
        assert np.std(sizes) > 0

    def test_sizes_in_expected_range(self, sized_df):
        chart = scatter(sized_df, x="x", y="y", size="pop")
        ax = chart.fig.axes[0]
        collection = ax.collections[0]
        sizes = collection.get_sizes()
        assert np.min(sizes) >= 20.0 - 0.1
        assert np.max(sizes) <= 200.0 + 0.1


# ---------------------------------------------------------------------------
# Point labels
# ---------------------------------------------------------------------------


class TestPointLabels:
    def test_labels_drawn(self, labeled_df):
        chart = scatter(labeled_df, x="x", y="y", label="name")
        ax = chart.fig.axes[0]
        texts = [t.get_text() for t in ax.texts]
        assert "Alpha" in texts
        assert "Epsilon" in texts

    def test_too_many_points_warns_and_skips(self):
        df = pd.DataFrame(
            {"x": range(25), "y": range(25), "lbl": [f"P{i}" for i in range(25)]}
        )
        with pytest.warns(UserWarning, match="Too many points"):
            chart = scatter(df, x="x", y="y", label="lbl")
        ax = chart.fig.axes[0]
        # No point labels should be drawn
        texts = [t.get_text() for t in ax.texts]
        assert not any(t.startswith("P") for t in texts)


# ---------------------------------------------------------------------------
# Log scales
# ---------------------------------------------------------------------------


class TestLogScales:
    def test_log_x(self):
        df = pd.DataFrame({"x": [1, 10, 100, 1000], "y": [1, 2, 3, 4]})
        chart = scatter(df, x="x", y="y", log_x=True)
        ax = chart.fig.axes[0]
        assert ax.get_xscale() == "log"

    def test_log_y(self):
        df = pd.DataFrame({"x": [1, 2, 3, 4], "y": [1, 10, 100, 1000]})
        chart = scatter(df, x="x", y="y", log_y=True)
        ax = chart.fig.axes[0]
        assert ax.get_yscale() == "log"


# ---------------------------------------------------------------------------
# Theme integration
# ---------------------------------------------------------------------------


class TestThemeIntegration:
    def test_both_gridlines_enabled(self, simple_df):
        chart = scatter(simple_df, x="height", y="weight", gridlines=True)
        ax = chart.fig.axes[0]
        assert ax.yaxis.get_gridlines()[0].get_visible()
        assert ax.xaxis.get_gridlines()[0].get_visible()

    def test_no_top_or_right_spines(self, simple_df):
        chart = scatter(simple_df, x="height", y="weight")
        ax = chart.fig.axes[0]
        assert not ax.spines["top"].get_visible()
        assert not ax.spines["right"].get_visible()

    def test_figure_size_override(self, simple_df):
        chart = scatter(simple_df, x="height", y="weight", figure_size="wide")
        w, h = chart.fig.get_size_inches()
        assert w == pytest.approx(11.0)
        assert h == pytest.approx(5.0)


# ---------------------------------------------------------------------------
# Annotations
# ---------------------------------------------------------------------------


class TestAnnotations:
    def test_basic_annotation(self, simple_df):
        chart = scatter(
            simple_df,
            x="height",
            y="weight",
            annotate=[Annotation(x=175, label="Midpoint", y=70)],
        )
        ax = chart.fig.axes[0]
        texts = [t.get_text() for t in ax.texts]
        assert "Midpoint" in texts

    def test_empty_annotate_list(self, simple_df):
        chart = scatter(simple_df, x="height", y="weight", annotate=[])
        assert isinstance(chart, Chart)
