"""Tests for vizop.charts.parliament."""

import math

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import pytest

import vizop
from vizop.charts.parliament import (
    _assign_parties_wedge,
    _auto_rows,
    _compute_seat_positions,
    _largest_remainder,
    parliament,
)
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
def party_df() -> pd.DataFrame:
    """DataFrame with party/seats columns."""
    return pd.DataFrame(
        {"party": ["Democrats", "Republicans", "Independents"], "seats": [213, 222, 0]}
    )


@pytest.fixture()
def values_dict() -> dict[str, int]:
    """Simple dict input (US House split)."""
    return {"Democrats": 213, "Republicans": 222}


# ---------------------------------------------------------------------------
# Smoke tests
# ---------------------------------------------------------------------------


class TestSmoke:
    def test_dict_mode_returns_chart(self, values_dict):
        chart = parliament(values=values_dict)
        assert isinstance(chart, Chart)

    def test_dataframe_mode_returns_chart(self, party_df):
        chart = parliament(party_df, party="party", seats="seats")
        assert isinstance(chart, Chart)

    def test_to_base64_works(self, values_dict):
        chart = parliament(values=values_dict)
        b64 = chart.to_base64()
        assert isinstance(b64, str)
        assert len(b64) > 100

    def test_accessible_via_vizop_namespace(self, values_dict):
        chart = vizop.parliament(values=values_dict)
        assert isinstance(chart, Chart)


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


class TestValidation:
    def test_mixed_inputs_raises(self, party_df):
        with pytest.raises(ValueError, match="Cannot use both"):
            parliament(party_df, party="party", seats="seats", values={"A": 1})

    def test_no_input_raises(self):
        with pytest.raises(ValueError, match="Must provide"):
            parliament()

    def test_empty_dataframe_raises(self):
        df = pd.DataFrame({"party": [], "seats": []})
        with pytest.raises(ValueError, match="DataFrame is empty"):
            parliament(df, party="party", seats="seats")

    def test_missing_party_column_raises(self, party_df):
        with pytest.raises(ValueError, match="Column 'missing'.*Available"):
            parliament(party_df, party="missing", seats="seats")

    def test_missing_seats_column_raises(self, party_df):
        with pytest.raises(ValueError, match="Column 'missing'.*Available"):
            parliament(party_df, party="party", seats="missing")

    def test_missing_party_param_raises(self, party_df):
        with pytest.raises(ValueError, match="Must provide 'party'"):
            parliament(party_df, seats="seats")

    def test_missing_seats_param_raises(self, party_df):
        with pytest.raises(ValueError, match="Must provide 'seats'"):
            parliament(party_df, party="party")

    def test_empty_values_dict_raises(self):
        with pytest.raises(ValueError, match="values dict is empty"):
            parliament(values={})

    def test_negative_values_raises(self):
        with pytest.raises(ValueError, match="values must be >= 0"):
            parliament(values={"A": 10, "B": -5})

    def test_invalid_arc_degrees_zero_raises(self):
        with pytest.raises(ValueError, match="arc_degrees"):
            parliament(values={"A": 10}, arc_degrees=0)

    def test_invalid_arc_degrees_over_360_raises(self):
        with pytest.raises(ValueError, match="arc_degrees"):
            parliament(values={"A": 10}, arc_degrees=361)

    def test_invalid_inner_radius_negative_raises(self):
        with pytest.raises(ValueError, match="inner_radius"):
            parliament(values={"A": 10}, inner_radius=-0.1)

    def test_invalid_inner_radius_one_raises(self):
        with pytest.raises(ValueError, match="inner_radius"):
            parliament(values={"A": 10}, inner_radius=1.0)

    def test_invalid_rows_raises(self):
        with pytest.raises(ValueError, match="rows must be >= 2"):
            parliament(values={"A": 10}, rows=1)

    def test_invalid_legend_raises(self, values_dict):
        with pytest.raises(ValueError, match="Invalid legend"):
            parliament(values=values_dict, legend="left")


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------


class TestLayout:
    def test_total_dots_match_total_seats(self, values_dict):
        chart = parliament(values=values_dict)
        ax = chart.fig.axes[0]
        total_seats = sum(values_dict.values())
        circles = [p for p in ax.patches if isinstance(p, matplotlib.patches.Circle)]
        assert len(circles) == total_seats

    def test_auto_rows_computed(self):
        # sqrt(100 / pi) ≈ 5.64, ceil = 6
        assert _auto_rows(100) == 6

    def test_auto_rows_clamped_low(self):
        assert _auto_rows(5) == 3  # clamped to minimum 3

    def test_auto_rows_clamped_high(self):
        assert _auto_rows(10000) == 12  # clamped to maximum 12

    def test_custom_rows_respected(self, values_dict):
        chart = parliament(values=values_dict, rows=5)
        # Should not error; chart renders with 5 rows
        assert isinstance(chart, Chart)

    def test_seat_positions_count(self):
        positions, seats_per_row = _compute_seat_positions(100, 5, math.pi, 0.4)
        assert len(positions) == 100
        assert sum(seats_per_row.values()) == 100

    def test_largest_remainder_sums_correctly(self):
        arc_lengths = {0: 1.2, 1: 2.0, 2: 3.5}
        result = _largest_remainder(arc_lengths, 50)
        assert sum(result.values()) == 50


# ---------------------------------------------------------------------------
# Majority line
# ---------------------------------------------------------------------------


class TestMajorityLine:
    def test_auto_threshold(self, values_dict):
        chart = parliament(values=values_dict, majority_line=True)
        ax = chart.fig.axes[0]
        # Should have a dashed line (Line2D) among artists
        lines = ax.get_lines()
        assert any(line.get_linestyle() == "--" for line in lines)

    def test_custom_threshold(self, values_dict):
        chart = parliament(values=values_dict, majority_line=250)
        ax = chart.fig.axes[0]
        lines = ax.get_lines()
        assert any(line.get_linestyle() == "--" for line in lines)

    def test_no_majority_line_by_default(self, values_dict):
        chart = parliament(values=values_dict)
        ax = chart.fig.axes[0]
        lines = ax.get_lines()
        dashed = [line for line in lines if line.get_linestyle() == "--"]
        assert len(dashed) == 0


# ---------------------------------------------------------------------------
# Center label
# ---------------------------------------------------------------------------


class TestCenterLabel:
    def test_default_shows_total(self, values_dict):
        chart = parliament(values=values_dict)
        ax = chart.fig.axes[0]
        texts = [t.get_text() for t in ax.texts]
        total = str(sum(values_dict.values()))
        assert total in texts

    def test_custom_string(self, values_dict):
        chart = parliament(values=values_dict, center_label="House")
        ax = chart.fig.axes[0]
        texts = [t.get_text() for t in ax.texts]
        assert "House" in texts

    def test_disabled(self, values_dict):
        chart = parliament(values=values_dict, center_label=False)
        ax = chart.fig.axes[0]
        total = str(sum(values_dict.values()))
        texts = [t.get_text() for t in ax.texts]
        assert total not in texts


# ---------------------------------------------------------------------------
# Highlight
# ---------------------------------------------------------------------------


class TestHighlight:
    def test_highlighted_full_alpha(self, values_dict):
        chart = parliament(values=values_dict, highlight="Democrats")
        ax = chart.fig.axes[0]
        circles = [p for p in ax.patches if isinstance(p, matplotlib.patches.Circle)]
        alphas = [p.get_alpha() for p in circles]
        assert any(a == 1.0 or a is None for a in alphas)  # highlighted
        assert any(a == pytest.approx(0.3) for a in alphas)  # muted

    def test_no_highlight_all_full_alpha(self, values_dict):
        chart = parliament(values=values_dict)
        ax = chart.fig.axes[0]
        circles = [p for p in ax.patches if isinstance(p, matplotlib.patches.Circle)]
        for p in circles:
            alpha = p.get_alpha()
            assert alpha is None or alpha == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Theme integration
# ---------------------------------------------------------------------------


class TestThemeIntegration:
    def test_title_in_figure_texts(self, values_dict):
        chart = parliament(values=values_dict, title="US House")
        fig_texts = [t.get_text() for t in chart.fig.texts]
        assert "US House" in fig_texts

    def test_axes_hidden(self, values_dict):
        chart = parliament(values=values_dict)
        ax = chart.fig.axes[0]
        assert not ax.axison

    def test_size_override(self, values_dict):
        chart = parliament(values=values_dict, size="standard")
        w, h = chart.fig.get_size_inches()
        assert w == pytest.approx(8.0)
        assert h == pytest.approx(5.5)

    def test_default_size_wide(self, values_dict):
        chart = parliament(values=values_dict)
        w, _h = chart.fig.get_size_inches()
        assert w == pytest.approx(11.0)

    def test_source_label(self, values_dict):
        chart = parliament(values=values_dict, source="AP News")
        fig_texts = [t.get_text() for t in chart.fig.texts]
        assert any("AP News" in t for t in fig_texts)


# ---------------------------------------------------------------------------
# Legend
# ---------------------------------------------------------------------------


class TestLegend:
    def test_legend_present_by_default(self, values_dict):
        chart = parliament(values=values_dict)
        ax = chart.fig.axes[0]
        assert ax.get_legend() is not None

    def test_legend_false_no_legend(self, values_dict):
        chart = parliament(values=values_dict, legend=False)
        ax = chart.fig.axes[0]
        assert ax.get_legend() is None

    def test_legend_none_no_legend(self, values_dict):
        chart = parliament(values=values_dict, legend=None)
        ax = chart.fig.axes[0]
        assert ax.get_legend() is None

    def test_single_party_no_legend(self):
        chart = parliament(values={"Only": 50})
        ax = chart.fig.axes[0]
        assert ax.get_legend() is None


# ---------------------------------------------------------------------------
# Wedge fill contiguity
# ---------------------------------------------------------------------------


class TestWedgeFill:
    def test_parties_contiguous_within_each_row(self):
        """Each party's seats within a single row should be adjacent (contiguous block)."""
        party_seats = {"A": 100, "B": 60, "C": 40}
        seats_per_row = {0: 15, 1: 20, 2: 25, 3: 30, 4: 35, 5: 40, 6: 35}
        seat_parties, _ = _assign_parties_wedge(party_seats, seats_per_row)

        # Walk each row's slice and verify no party appears, disappears, then reappears
        offset = 0
        for row_idx in sorted(seats_per_row):
            n = seats_per_row[row_idx]
            row_slice = seat_parties[offset : offset + n]
            offset += n

            # Collect party runs — each party should appear in exactly one run
            seen_parties: list[str] = []
            prev = None
            for p in row_slice:
                if p != prev:
                    assert p not in seen_parties, (
                        f"Party '{p}' reappears in row {row_idx}: {row_slice}"
                    )
                    seen_parties.append(p)
                    prev = p

    def test_sorted_order_largest_leftmost(self):
        """Parties should be ordered by descending seat count (largest on left)."""
        party_seats = {"Small": 10, "Big": 100, "Medium": 50}
        seats_per_row = {0: 10, 1: 15, 2: 20, 3: 25, 4: 30, 5: 35, 6: 25}
        seat_parties, sorted_names = _assign_parties_wedge(party_seats, seats_per_row)
        assert sorted_names == ["Big", "Medium", "Small"]

    def test_total_seats_preserved(self):
        """Total assigned seats should match input."""
        party_seats = {"A": 50, "B": 30, "C": 20}
        seats_per_row = {0: 10, 1: 15, 2: 20, 3: 25, 4: 30}
        seat_parties, _ = _assign_parties_wedge(party_seats, seats_per_row)
        assert len(seat_parties) == 100
        assert seat_parties.count("A") == 50
        assert seat_parties.count("B") == 30
        assert seat_parties.count("C") == 20
