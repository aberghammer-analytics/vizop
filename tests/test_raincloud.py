"""Tests for vizop.charts.raincloud."""

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

import vizop
from vizop.charts.raincloud import raincloud
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
    """Simple single-group data with enough points for KDE."""
    rng = np.random.default_rng(0)
    return pd.DataFrame({"score": rng.normal(50, 10, size=30)})


@pytest.fixture()
def grouped_df() -> pd.DataFrame:
    """Long-format grouped data."""
    rng = np.random.default_rng(0)
    return pd.DataFrame(
        {
            "score": np.concatenate([rng.normal(50, 10, 20), rng.normal(70, 8, 20)]),
            "treatment": ["Control"] * 20 + ["Drug"] * 20,
        }
    )


@pytest.fixture()
def wide_df() -> pd.DataFrame:
    """Wide-format data with multiple value columns."""
    rng = np.random.default_rng(0)
    return pd.DataFrame(
        {
            "pre_score": rng.normal(50, 10, 25),
            "post_score": rng.normal(65, 8, 25),
        }
    )


# ---------------------------------------------------------------------------
# Smoke tests
# ---------------------------------------------------------------------------


class TestSmoke:
    def test_raincloud_basic(self, single_df):
        chart = raincloud(single_df, value="score")
        assert isinstance(chart, Chart)

    def test_raincloud_base64(self, single_df):
        chart = raincloud(single_df, value="score")
        b64 = chart.to_base64()
        assert isinstance(b64, str)
        assert len(b64) > 100

    def test_accessible_via_vizop_namespace(self, single_df):
        chart = vizop.raincloud(single_df, value="score")
        assert isinstance(chart, Chart)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestValidation:
    def test_raincloud_empty_df(self):
        df = pd.DataFrame({"score": []})
        with pytest.raises(ValueError, match="DataFrame is empty"):
            raincloud(df, value="score")

    def test_raincloud_invalid_column(self):
        df = pd.DataFrame({"score": [1, 2, 3]})
        with pytest.raises(ValueError, match="Column 'missing'.*Available"):
            raincloud(df, value="missing")

    def test_raincloud_invalid_column_in_list(self):
        df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        with pytest.raises(ValueError, match="Column 'nope'.*Available"):
            raincloud(df, value=["a", "nope"])

    def test_raincloud_invalid_group_column(self, single_df):
        with pytest.raises(ValueError, match="Column 'grp'.*Available"):
            raincloud(single_df, value="score", group="grp")

    def test_raincloud_group_and_list_exclusive(self, grouped_df):
        with pytest.raises(ValueError, match="Cannot use both"):
            raincloud(grouped_df, value=["score", "treatment"], group="treatment")


# ---------------------------------------------------------------------------
# Data formats
# ---------------------------------------------------------------------------


class TestDataFormats:
    def test_raincloud_grouped(self, grouped_df):
        chart = raincloud(grouped_df, value="score", group="treatment")
        assert isinstance(chart, Chart)
        ax = chart.fig.axes[0]
        labels = [t.get_text() for t in ax.get_yticklabels()]
        assert "Control" in labels
        assert "Drug" in labels

    def test_raincloud_wide(self, wide_df):
        chart = raincloud(wide_df, value=["pre_score", "post_score"])
        assert isinstance(chart, Chart)
        ax = chart.fig.axes[0]
        labels = [t.get_text() for t in ax.get_yticklabels()]
        assert "pre_score" in labels
        assert "post_score" in labels


# ---------------------------------------------------------------------------
# Layer toggles
# ---------------------------------------------------------------------------


class TestLayerToggles:
    def _count_artists(self, chart) -> int:
        """Count drawable artists (patches, lines, collections) on the axes."""
        ax = chart.fig.axes[0]
        return len(ax.patches) + len(ax.lines) + len(ax.collections)

    def test_all_layers_on(self, single_df):
        chart_all = raincloud(single_df, value="score")
        count_all = self._count_artists(chart_all)
        assert count_all > 0

    def test_no_density_fewer_artists(self, single_df):
        chart_all = raincloud(single_df, value="score")
        chart_no_density = raincloud(single_df, value="score", show_density=False)
        assert self._count_artists(chart_no_density) < self._count_artists(chart_all)

    def test_no_box_fewer_artists(self, single_df):
        chart_all = raincloud(single_df, value="score")
        chart_no_box = raincloud(single_df, value="score", show_box=False)
        assert self._count_artists(chart_no_box) < self._count_artists(chart_all)

    def test_no_points_fewer_artists(self, single_df):
        chart_all = raincloud(single_df, value="score")
        chart_no_points = raincloud(single_df, value="score", show_points=False)
        assert self._count_artists(chart_no_points) < self._count_artists(chart_all)


# ---------------------------------------------------------------------------
# Highlight
# ---------------------------------------------------------------------------


class TestHighlight:
    def test_raincloud_highlight(self, grouped_df):
        chart = raincloud(
            grouped_df, value="score", group="treatment", highlight="Drug"
        )
        assert isinstance(chart, Chart)


# ---------------------------------------------------------------------------
# Theme integration
# ---------------------------------------------------------------------------


class TestThemeIntegration:
    def test_no_top_or_right_spines(self, single_df):
        chart = raincloud(single_df, value="score")
        ax = chart.fig.axes[0]
        assert not ax.spines["top"].get_visible()
        assert not ax.spines["right"].get_visible()

    def test_title_rendered(self, single_df):
        chart = raincloud(single_df, value="score", title="My Raincloud")
        fig_texts = [t.get_text() for t in chart.fig.texts]
        assert "My Raincloud" in fig_texts

    def test_size_override(self, single_df):
        chart = raincloud(single_df, value="score", size="wide")
        w, h = chart.fig.get_size_inches()
        assert w == pytest.approx(11.0)
        assert h == pytest.approx(5.0)
