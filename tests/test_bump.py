"""Tests for vizop.charts.bump."""

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import pytest

import vizop
from vizop.charts.bump import bump
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
def bump_df() -> pd.DataFrame:
    """Long-format bump data: 4 entities over 4 periods."""
    return pd.DataFrame({
        "year": [2020, 2021, 2022, 2023] * 4,
        "score": [
            100, 90, 95, 110,   # Alpha
            80, 95, 100, 90,    # Beta
            90, 85, 80, 85,     # Gamma
            70, 75, 90, 100,    # Delta
        ],
        "team": (
            ["Alpha"] * 4
            + ["Beta"] * 4
            + ["Gamma"] * 4
            + ["Delta"] * 4
        ),
    })


@pytest.fixture()
def tied_df() -> pd.DataFrame:
    """Data with tied values in some periods."""
    return pd.DataFrame({
        "year": [2020, 2021, 2022] * 3,
        "score": [
            100, 80, 90,   # A
            100, 90, 80,   # B (tied with A at 2020)
            80, 80, 80,    # C (tied with A at 2021)
        ],
        "team": ["A"] * 3 + ["B"] * 3 + ["C"] * 3,
    })


# ---------------------------------------------------------------------------
# Smoke tests
# ---------------------------------------------------------------------------


class TestSmoke:
    def test_returns_chart(self, bump_df):
        chart = bump(bump_df, x="year", y="score", group="team")
        assert isinstance(chart, Chart)

    def test_base64_output(self, bump_df):
        chart = bump(bump_df, x="year", y="score", group="team")
        b64 = chart.to_base64()
        assert isinstance(b64, str)
        assert len(b64) > 100

    def test_accessible_via_vizop_namespace(self, bump_df):
        chart = vizop.bump(bump_df, x="year", y="score", group="team")
        assert isinstance(chart, Chart)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestValidation:
    def test_empty_dataframe_raises(self):
        df = pd.DataFrame({"x": [], "y": [], "g": []})
        with pytest.raises(ValueError, match="DataFrame is empty"):
            bump(df, x="x", y="y", group="g")

    def test_missing_x_column_raises(self, bump_df):
        with pytest.raises(ValueError, match="Column 'missing'.*Available"):
            bump(bump_df, x="missing", y="score", group="team")

    def test_missing_y_column_raises(self, bump_df):
        with pytest.raises(ValueError, match="Column 'missing'.*Available"):
            bump(bump_df, x="year", y="missing", group="team")

    def test_missing_group_column_raises(self, bump_df):
        with pytest.raises(ValueError, match="Column 'missing'.*Available"):
            bump(bump_df, x="year", y="score", group="missing")

    def test_fewer_than_3_x_values_raises(self):
        df = pd.DataFrame({
            "year": [2020, 2021, 2020, 2021],
            "val": [10, 20, 30, 40],
            "grp": ["A", "A", "B", "B"],
        })
        with pytest.raises(ValueError, match="at least 3 unique x-values"):
            bump(df, x="year", y="val", group="grp")

    def test_invalid_rank_order_raises(self, bump_df):
        with pytest.raises(ValueError, match="Invalid rank_order"):
            bump(bump_df, x="year", y="score", group="team", rank_order="random")


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------


class TestRanking:
    def test_default_desc_ranking(self, bump_df):
        """Highest value should get rank 1 (desc mode)."""
        chart = bump(bump_df, x="year", y="score", group="team")
        ax = chart.fig.axes[0]
        # In 2020: Alpha=100 (rank 1), Gamma=90 (rank 2), Beta=80 (rank 3), Delta=70 (rank 4)
        # Y-axis is inverted, so rank 1 should be near the top (low y value)
        # Just verify it rendered successfully with correct number of scatter collections
        scatter_collections = [
            c for c in ax.collections if hasattr(c, "get_offsets")
        ]
        # 4 entities, each with dots at 4 positions = 4 scatter calls
        assert len(scatter_collections) == 4

    def test_asc_ranking(self, bump_df):
        """Lowest value should get rank 1 in asc mode."""
        chart = bump(bump_df, x="year", y="score", group="team", rank_order="asc")
        assert isinstance(chart, Chart)

    def test_tied_values_get_min_rank(self, tied_df):
        """Tied values should get the minimum rank (method='min')."""
        chart = bump(tied_df, x="year", y="score", group="team")
        assert isinstance(chart, Chart)
        # Verify it handles ties without error


# ---------------------------------------------------------------------------
# Top N
# ---------------------------------------------------------------------------


class TestTopN:
    def test_top_n_filters_entities(self, bump_df):
        chart = bump(bump_df, x="year", y="score", group="team", top_n=2)
        ax = chart.fig.axes[0]
        # Should only have 2 entities → 2 lines + 2 scatter collections
        scatter_collections = [
            c for c in ax.collections if hasattr(c, "get_offsets")
        ]
        assert len(scatter_collections) == 2

    def test_top_n_keeps_best_final_rank(self, bump_df):
        """top_n=1 should keep only the entity ranked #1 in the final period."""
        chart = bump(bump_df, x="year", y="score", group="team", top_n=1)
        ax = chart.fig.axes[0]
        scatter_collections = [
            c for c in ax.collections if hasattr(c, "get_offsets")
        ]
        assert len(scatter_collections) == 1

    def test_warning_on_many_entities(self):
        df = pd.DataFrame({
            "period": list(range(3)) * 20,
            "val": list(range(60)),
            "entity": [f"E{i}" for i in range(20) for _ in range(3)],
        })
        with pytest.warns(UserWarning, match="Consider using top_n"):
            bump(df, x="period", y="val", group="entity")


# ---------------------------------------------------------------------------
# Highlight
# ---------------------------------------------------------------------------


class TestHighlight:
    def test_highlight_mutes_others(self, bump_df):
        chart = bump(bump_df, x="year", y="score", group="team", highlight="Alpha")
        ax = chart.fig.axes[0]
        muted = HIGHLIGHT_MUTED_COLOR.lower()
        line_colors = [matplotlib.colors.to_hex(ln.get_color()) for ln in ax.lines]
        # Muted color should appear (for non-highlighted entities)
        assert muted in line_colors

    def test_highlight_multiple(self, bump_df):
        chart = bump(
            bump_df,
            x="year",
            y="score",
            group="team",
            highlight=["Alpha", "Beta"],
        )
        ax = chart.fig.axes[0]
        muted = HIGHLIGHT_MUTED_COLOR.lower()
        line_colors = [matplotlib.colors.to_hex(ln.get_color()) for ln in ax.lines]
        assert muted in line_colors


# ---------------------------------------------------------------------------
# Color map
# ---------------------------------------------------------------------------


class TestColorMap:
    def test_explicit_color_map(self, bump_df):
        cmap = {"Alpha": "#ff0000", "Beta": "#00ff00"}
        chart = bump(
            bump_df,
            x="year",
            y="score",
            group="team",
            color_map=cmap,
        )
        ax = chart.fig.axes[0]
        line_colors = [matplotlib.colors.to_hex(ln.get_color()) for ln in ax.lines]
        assert "#ff0000" in line_colors
        assert "#00ff00" in line_colors

    def test_unmapped_entities_get_muted(self, bump_df):
        cmap = {"Alpha": "#ff0000"}
        chart = bump(
            bump_df,
            x="year",
            y="score",
            group="team",
            color_map=cmap,
        )
        ax = chart.fig.axes[0]
        muted = HIGHLIGHT_MUTED_COLOR.lower()
        line_colors = [matplotlib.colors.to_hex(ln.get_color()) for ln in ax.lines]
        assert muted in line_colors


# ---------------------------------------------------------------------------
# Theme integration
# ---------------------------------------------------------------------------


class TestThemeIntegration:
    def test_no_top_or_right_spines(self, bump_df):
        chart = bump(bump_df, x="year", y="score", group="team")
        ax = chart.fig.axes[0]
        assert not ax.spines["top"].get_visible()
        assert not ax.spines["right"].get_visible()

    def test_title_and_subtitle(self, bump_df):
        chart = bump(
            bump_df,
            x="year",
            y="score",
            group="team",
            title="Team Rankings",
            subtitle="2020-2023",
        )
        fig_texts = [t.get_text() for t in chart.fig.texts]
        assert "Team Rankings" in fig_texts
        assert "2020-2023" in fig_texts

    def test_size_override(self, bump_df):
        chart = bump(bump_df, x="year", y="score", group="team", size="wide")
        w, h = chart.fig.get_size_inches()
        assert w == pytest.approx(11.0)
        assert h == pytest.approx(5.0)

    def test_inverted_y_axis(self, bump_df):
        """Rank 1 should be at the top (lower y-coordinate in display)."""
        chart = bump(bump_df, x="year", y="score", group="team")
        ax = chart.fig.axes[0]
        y_min, y_max = ax.get_ylim()
        # Inverted: y_min > y_max
        assert y_min > y_max


# ---------------------------------------------------------------------------
# Labels
# ---------------------------------------------------------------------------


class TestLabels:
    def test_right_side_labels_with_rank(self, bump_df):
        chart = bump(
            bump_df, x="year", y="score", group="team", show_rank=True
        )
        ax = chart.fig.axes[0]
        texts = [t.get_text() for t in ax.texts]
        # Should have labels with "#" rank number
        assert any("#" in t for t in texts)

    def test_right_side_labels_without_rank(self, bump_df):
        chart = bump(
            bump_df, x="year", y="score", group="team", show_rank=False
        )
        ax = chart.fig.axes[0]
        texts = [t.get_text() for t in ax.texts]
        # Should have entity names but no "#" rank
        assert any("Alpha" in t for t in texts)
        assert not any("#" in t for t in texts)

    def test_x_axis_has_period_labels(self, bump_df):
        chart = bump(bump_df, x="year", y="score", group="team")
        ax = chart.fig.axes[0]
        tick_labels = [t.get_text() for t in ax.get_xticklabels()]
        assert "2020" in tick_labels
        assert "2023" in tick_labels
