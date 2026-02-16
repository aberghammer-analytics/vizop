"""Tests for vizop.charts.waffle."""

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import pytest
from matplotlib.path import Path as MplPath

import vizop
from vizop.charts.waffle import _normalize_largest_remainder, waffle
from vizop.core.chart import Chart
from vizop.core.config import reset_config

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
def category_df() -> pd.DataFrame:
    """DataFrame with group/count columns."""
    return pd.DataFrame(
        {"group": ["Agree", "Disagree", "Unsure"], "count": [65, 25, 10]}
    )


@pytest.fixture()
def values_dict() -> dict[str, float]:
    """Simple dict input."""
    return {"Agree": 65, "Disagree": 25, "Unsure": 10}


@pytest.fixture()
def many_categories_df() -> pd.DataFrame:
    """10 categories for merge testing."""
    return pd.DataFrame(
        {
            "cat": [f"Cat{i}" for i in range(10)],
            "val": [50, 40, 30, 20, 15, 12, 10, 8, 5, 3],
        }
    )


# ---------------------------------------------------------------------------
# Smoke tests
# ---------------------------------------------------------------------------


class TestSmoke:
    def test_square_returns_chart(self, values_dict):
        chart = waffle(values=values_dict)
        assert isinstance(chart, Chart)

    def test_circle_returns_chart(self, values_dict):
        chart = waffle(values=values_dict, style="circle")
        assert isinstance(chart, Chart)

    def test_icon_returns_chart(self, values_dict):
        chart = waffle(values=values_dict, style="icon", icon="person")
        assert isinstance(chart, Chart)

    def test_to_base64_works(self, values_dict):
        chart = waffle(values=values_dict)
        b64 = chart.to_base64()
        assert isinstance(b64, str)
        assert len(b64) > 100

    def test_dataframe_mode(self, category_df):
        chart = waffle(category_df, category="group", value="count")
        assert isinstance(chart, Chart)

    def test_accessible_via_vizop_namespace(self, values_dict):
        chart = vizop.waffle(values=values_dict)
        assert isinstance(chart, Chart)


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


class TestValidation:
    def test_mixed_inputs_raises(self, category_df):
        with pytest.raises(ValueError, match="Cannot use both"):
            waffle(category_df, category="group", value="count", values={"A": 1})

    def test_no_input_raises(self):
        with pytest.raises(ValueError, match="Must provide"):
            waffle()

    def test_empty_dataframe_raises(self):
        df = pd.DataFrame({"cat": [], "val": []})
        with pytest.raises(ValueError, match="DataFrame is empty"):
            waffle(df, category="cat", value="val")

    def test_missing_category_column_raises(self, category_df):
        with pytest.raises(ValueError, match="Column 'missing'.*Available"):
            waffle(category_df, category="missing", value="count")

    def test_missing_value_column_raises(self, category_df):
        with pytest.raises(ValueError, match="Column 'missing'.*Available"):
            waffle(category_df, category="group", value="missing")

    def test_missing_category_param_raises(self, category_df):
        with pytest.raises(ValueError, match="Must provide 'category'"):
            waffle(category_df, value="count")

    def test_missing_value_param_raises(self, category_df):
        with pytest.raises(ValueError, match="Must provide 'value'"):
            waffle(category_df, category="group")

    def test_empty_values_dict_raises(self):
        with pytest.raises(ValueError, match="values dict is empty"):
            waffle(values={})

    def test_negative_values_raises(self):
        with pytest.raises(ValueError, match="values must be >= 0"):
            waffle(values={"A": 10, "B": -5})

    def test_invalid_style_raises(self, values_dict):
        with pytest.raises(ValueError, match="Invalid style"):
            waffle(values=values_dict, style="hexagon")

    def test_icon_style_without_icon_raises(self, values_dict):
        with pytest.raises(ValueError, match="Must provide 'icon'"):
            waffle(values=values_dict, style="icon")

    def test_invalid_legend_raises(self, values_dict):
        with pytest.raises(ValueError, match="Invalid legend"):
            waffle(values=values_dict, legend="left")


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


class TestNormalization:
    def test_cells_sum_to_grid_size_squared(self):
        cat_values = {"A": 65, "B": 25, "C": 10}
        counts = _normalize_largest_remainder(cat_values, 100)
        assert sum(counts.values()) == 100

    def test_cells_sum_with_odd_grid(self):
        cat_values = {"X": 33, "Y": 33, "Z": 34}
        counts = _normalize_largest_remainder(cat_values, 49)
        assert sum(counts.values()) == 49

    def test_single_category_gets_all_cells(self):
        counts = _normalize_largest_remainder({"Only": 100}, 100)
        assert counts["Only"] == 100

    def test_largest_remainder_correctness(self):
        """With 3 equal values and 100 cells, two get 34 and one gets 33 (or similar)."""
        counts = _normalize_largest_remainder({"A": 1, "B": 1, "C": 1}, 100)
        assert sum(counts.values()) == 100
        # Each should be 33 or 34
        for v in counts.values():
            assert v in (33, 34)

    def test_small_grid(self):
        counts = _normalize_largest_remainder({"A": 70, "B": 30}, 25)
        assert sum(counts.values()) == 25
        assert counts["A"] > counts["B"]

    def test_all_zero_values(self):
        counts = _normalize_largest_remainder({"A": 0, "B": 0}, 100)
        assert sum(counts.values()) == 100


# ---------------------------------------------------------------------------
# Category merging
# ---------------------------------------------------------------------------


class TestCategoryMerging:
    def test_10_categories_merged_to_7(self, many_categories_df):
        with pytest.warns(UserWarning, match="merging smallest into 'Other'"):
            chart = waffle(many_categories_df, category="cat", value="val")
        assert isinstance(chart, Chart)

    def test_7_categories_not_merged(self):
        values = {f"Cat{i}": 10 + i for i in range(7)}
        chart = waffle(values=values)
        assert isinstance(chart, Chart)

    def test_other_category_present_after_merge(self, many_categories_df):
        with pytest.warns(UserWarning):
            chart = waffle(many_categories_df, category="cat", value="val")
        # Should have rendered — check legend for "Other"
        ax = chart.fig.axes[0]
        legend = ax.get_legend()
        if legend is not None:
            legend_texts = [t.get_text() for t in legend.get_texts()]
            assert "Other" in legend_texts


# ---------------------------------------------------------------------------
# Highlight
# ---------------------------------------------------------------------------


class TestHighlight:
    def test_highlighted_full_alpha(self, values_dict):
        chart = waffle(values=values_dict, highlight="Agree")
        ax = chart.fig.axes[0]
        # Patches should have mixed alphas
        alphas = [p.get_alpha() for p in ax.patches]
        assert any(a == 1.0 or a is None for a in alphas)  # highlighted
        assert any(a == pytest.approx(0.3) for a in alphas)  # muted

    def test_no_highlight_all_full_alpha(self, values_dict):
        chart = waffle(values=values_dict)
        ax = chart.fig.axes[0]
        for p in ax.patches:
            alpha = p.get_alpha()
            assert alpha is None or alpha == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Custom icon path
# ---------------------------------------------------------------------------


class TestCustomIcon:
    def test_raw_matplotlib_path(self, values_dict):
        # A simple triangle as a custom path
        triangle = MplPath(
            [(0.5, 1.0), (0.0, 0.0), (1.0, 0.0), (0.5, 1.0)],
            [MplPath.MOVETO, MplPath.LINETO, MplPath.LINETO, MplPath.CLOSEPOLY],
        )
        chart = waffle(values=values_dict, style="icon", icon=triangle)
        assert isinstance(chart, Chart)

    def test_unknown_icon_name_raises(self, values_dict):
        with pytest.raises(ValueError, match="Unknown icon"):
            waffle(values=values_dict, style="icon", icon="rocket")

    def test_all_builtin_icons(self, values_dict):
        for name in ("person", "circle", "square", "house", "dollar", "heart"):
            chart = waffle(values=values_dict, style="icon", icon=name)
            assert isinstance(chart, Chart)
            chart.close()


# ---------------------------------------------------------------------------
# Grid size override
# ---------------------------------------------------------------------------


class TestGridSize:
    def test_grid_size_5_produces_25_cells(self):
        values = {"A": 60, "B": 40}
        chart = waffle(values=values, grid_size=5)
        ax = chart.fig.axes[0]
        # 25 patches total (one per cell)
        assert len(ax.patches) == 25

    def test_default_grid_size_produces_100_cells(self, values_dict):
        chart = waffle(values=values_dict)
        ax = chart.fig.axes[0]
        assert len(ax.patches) == 100


# ---------------------------------------------------------------------------
# Theme integration
# ---------------------------------------------------------------------------


class TestThemeIntegration:
    def test_title_in_figure_texts(self, values_dict):
        chart = waffle(values=values_dict, title="Survey Results")
        fig_texts = [t.get_text() for t in chart.fig.texts]
        assert "Survey Results" in fig_texts

    def test_subtitle_in_figure_texts(self, values_dict):
        chart = waffle(values=values_dict, title="Survey", subtitle="2025 data")
        fig_texts = [t.get_text() for t in chart.fig.texts]
        assert "2025 data" in fig_texts

    def test_axes_hidden(self, values_dict):
        chart = waffle(values=values_dict)
        ax = chart.fig.axes[0]
        # All spines should be hidden when axis is off
        assert not ax.axison

    def test_size_override(self, values_dict):
        chart = waffle(values=values_dict, size="wide")
        w, h = chart.fig.get_size_inches()
        assert w == pytest.approx(11.0)
        assert h == pytest.approx(5.0)

    def test_source_label(self, values_dict):
        chart = waffle(values=values_dict, source="Pew Research")
        fig_texts = [t.get_text() for t in chart.fig.texts]
        assert any("Pew Research" in t for t in fig_texts)


# ---------------------------------------------------------------------------
# Legend
# ---------------------------------------------------------------------------


class TestLegend:
    def test_legend_bottom_default(self, values_dict):
        chart = waffle(values=values_dict)
        ax = chart.fig.axes[0]
        legend = ax.get_legend()
        assert legend is not None

    def test_legend_false_no_legend(self, values_dict):
        chart = waffle(values=values_dict, legend=False)
        ax = chart.fig.axes[0]
        assert ax.get_legend() is None

    def test_legend_none_no_legend(self, values_dict):
        chart = waffle(values=values_dict, legend=None)
        ax = chart.fig.axes[0]
        assert ax.get_legend() is None

    def test_single_category_no_legend(self):
        chart = waffle(values={"Only": 100})
        ax = chart.fig.axes[0]
        assert ax.get_legend() is None
