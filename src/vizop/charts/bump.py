"""Bump chart implementation for vizop."""

import warnings
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from vizop.core.annotations import Annotation
from vizop.core.chart import Chart
from vizop.core.config import get_config
from vizop.core.fonts import get_font_family
from vizop.core.palettes import assign_colors, normalize_highlight
from vizop.core.theme import LAYOUT, TYPOGRAPHY, apply_theme

try:
    from scipy.interpolate import PchipInterpolator

    _HAS_SCIPY = True
except ImportError:  # pragma: no cover
    _HAS_SCIPY = False


def bump(
    data: pd.DataFrame,
    *,
    x: str,
    y: str,
    group: str,
    title: str | None = None,
    subtitle: str | None = None,
    source: str | None = None,
    note: str | None = None,
    accent_color: str | None = None,
    palette: str = "default",
    highlight: str | list[str] | None = None,
    color_map: dict[str, str] | None = None,
    top_n: int | None = None,
    show_rank: bool = True,
    rank_order: str = "desc",
    gridlines: bool = False,
    size: str | None = None,
    annotate: list[Annotation] | None = None,
) -> Chart:
    """Create a bump chart showing rank changes over multiple time periods.

    Requires long-format data with x (time periods), y (values to rank),
    and group (entity identifier) columns. Values are automatically ranked
    within each period.

    Args:
        data: Source DataFrame in long format.
        x: Column with time periods (must have 3+ unique values).
        y: Column with raw values (auto-ranked per period).
        group: Column identifying entities.
        title: Chart title (left-aligned).
        subtitle: Subtitle below the title.
        source: Source attribution below the chart.
        note: Note text below the chart.
        accent_color: Override color for single-entity charts.
        palette: Color palette name.
        highlight: Entity name(s) to highlight; others are muted.
        color_map: Dict mapping entity names to hex colors.
        top_n: Show only top N entities by final-period rank.
        show_rank: Append rank number to endpoint labels (default True).
        rank_order: "desc" = highest value → rank 1, "asc" = lowest → rank 1.
        gridlines: Show horizontal gridlines (default False).
        size: Override figure size preset.
        annotate: List of Annotation objects.

    Returns:
        A Chart object wrapping the matplotlib figure.
    """
    _validate(data, x, y, group, rank_order)
    config = get_config()

    if size is not None:
        config = config.model_copy(update={"size": size})

    # --- Prepare ranked data ---
    x_values, ranked_data = _prepare_ranks(data, x, y, group, rank_order)

    # --- Filter to top_n by final-period rank ---
    if top_n is not None:
        final_ranks = {entity: ranks[-1] for entity, ranks in ranked_data.items()}
        sorted_entities = sorted(final_ranks, key=lambda e: final_ranks[e])
        keep = set(sorted_entities[:top_n])
        ranked_data = {e: r for e, r in ranked_data.items() if e in keep}

    entity_names = list(ranked_data.keys())

    if len(entity_names) > 15 and top_n is None:
        warnings.warn(
            f"Bump chart has {len(entity_names)} entities. "
            f"Consider using top_n= to reduce clutter.",
            stacklevel=2,
        )

    # --- Color assignment ---
    colors = assign_colors(
        entity_names,
        accent_color=accent_color,
        palette=palette,
        highlight=highlight,
        color_map=color_map,
        config_accent=config.accent_color,
    )

    # --- Create figure ---
    fig, ax = plt.subplots()

    # --- Draw bump lines and dots ---
    x_positions = list(range(len(x_values)))
    _draw_bump_lines(ax, ranked_data, x_positions, colors, highlight)

    # --- Apply theme ---
    apply_theme(
        fig,
        ax,
        config=config,
        title=title,
        subtitle=subtitle,
        source=source,
        note=note,
        gridlines=gridlines,
    )

    # --- Bump-specific axis customization ---
    font_family = get_font_family(config)

    # Invert y-axis: rank 1 at top
    all_ranks = [r for ranks in ranked_data.values() for r in ranks]
    max_rank = max(all_ranks) if all_ranks else 1
    ax.set_ylim(max_rank + 0.5, 0.5)

    # Integer y-ticks for ranks
    ax.set_yticks(list(range(1, int(max_rank) + 1)))
    ax.set_yticklabels([str(i) for i in range(1, int(max_rank) + 1)])

    # Bold period labels on x-axis
    ax.set_xticks(x_positions)
    ax.set_xticklabels([str(v) for v in x_values])
    ax.tick_params(axis="x", length=0, pad=8)
    for tick_label in ax.get_xticklabels():
        tick_label.set_fontweight("bold")
        tick_label.set_fontsize(TYPOGRAPHY.label_size)
        tick_label.set_color(TYPOGRAPHY.label_color)
        tick_label.set_fontfamily(font_family)

    # X limits with padding for labels
    ax.set_xlim(-0.3, len(x_values) - 1 + 0.3)

    # Hide left spine (rank labels are enough)
    ax.spines["left"].set_visible(False)
    ax.spines["bottom"].set_visible(False)

    # --- Draw right-side labels with collision avoidance ---
    _draw_labels(ax, ranked_data, x_positions, colors, show_rank)

    return Chart(fig)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _validate(
    data: pd.DataFrame,
    x: str,
    y: str,
    group: str,
    rank_order: str,
) -> None:
    """Validate inputs before creating any figure."""
    if data.empty:
        raise ValueError("DataFrame is empty. Cannot create chart.")

    available = list(data.columns)
    available_str = ", ".join(repr(c) for c in available)

    for _col_name, col_val in [("x", x), ("y", y), ("group", group)]:
        if col_val not in data.columns:
            raise ValueError(
                f"Column '{col_val}' not found in DataFrame. Available: {available_str}"
            )

    n_unique = data[x].nunique()
    if n_unique < 3:
        raise ValueError(
            f"Bump charts require at least 3 unique x-values (time periods), got {n_unique}. "
            f"Unique values: {sorted(data[x].unique().tolist())}"
        )

    if rank_order not in ("desc", "asc"):
        raise ValueError(f"Invalid rank_order '{rank_order}'. Must be 'desc' or 'asc'.")


def _prepare_ranks(
    data: pd.DataFrame,
    x: str,
    y: str,
    group: str,
    rank_order: str,
) -> tuple[list[Any], dict[str, list[float]]]:
    """Pivot long data and compute ranks within each period.

    Returns:
        (x_values, ranked_data) where ranked_data maps entity → list of ranks.
    """
    x_values = sorted(data[x].unique().tolist(), key=str)
    ascending = rank_order == "asc"

    # Pivot: rows = groups, columns = x-values, values = y
    pivot = data.pivot_table(index=group, columns=x, values=y, aggfunc="first")

    # Rank within each column (period)
    rank_df = pivot.rank(method="min", ascending=ascending)

    # Build {entity: [rank_per_period]}
    ranked_data: dict[str, list[float]] = {}
    for entity in rank_df.index:
        ranks = []
        for xv in x_values:
            if xv in rank_df.columns and pd.notna(rank_df.loc[entity, xv]):
                ranks.append(float(rank_df.loc[entity, xv]))
            else:
                ranks.append(float("nan"))
        ranked_data[str(entity)] = ranks

    return x_values, ranked_data


def _interpolate_curve(
    x_positions: list[int],
    ranks: list[float],
    num_points: int = 200,
) -> tuple[np.ndarray, np.ndarray]:
    """Generate smooth S-curve through rank positions.

    Uses PCHIP (monotone cubic) interpolation for smooth curves without
    overshoot. Falls back to linear interpolation if scipy is unavailable.
    """
    x_arr = np.array(x_positions, dtype=float)
    y_arr = np.array(ranks, dtype=float)

    x_smooth = np.linspace(x_arr[0], x_arr[-1], num_points)

    if _HAS_SCIPY:
        interp = PchipInterpolator(x_arr, y_arr)
        y_smooth = interp(x_smooth)
    else:  # pragma: no cover
        y_smooth = np.interp(x_smooth, x_arr, y_arr)

    return x_smooth, y_smooth


def _draw_bump_lines(
    ax: plt.Axes,
    ranked_data: dict[str, list[float]],
    x_positions: list[int],
    colors: dict[str, str],
    highlight: str | list[str] | None,
) -> None:
    """Render bump lines and endpoint dots, muted-first draw order."""
    highlight_set = normalize_highlight(highlight)
    entity_names = list(ranked_data.keys())

    muted_names = []
    highlighted_names = []
    if highlight_set:
        for name in entity_names:
            if name in highlight_set:
                highlighted_names.append(name)
            else:
                muted_names.append(name)
    else:
        highlighted_names = entity_names

    draw_order = muted_names + highlighted_names

    for name in draw_order:
        ranks = ranked_data[name]
        color = colors[name]
        is_muted = name in muted_names
        lw = 1.0 if is_muted else LAYOUT.line_width
        zorder = 2 if is_muted else 3

        # Smooth interpolated curve
        x_smooth, y_smooth = _interpolate_curve(x_positions, ranks)
        ax.plot(x_smooth, y_smooth, color=color, linewidth=lw, zorder=zorder)

        # Endpoint dots (6px) at each period position
        dot_size = 36  # matplotlib scatter size is area in points^2; 6px diameter ~ 36
        ax.scatter(
            x_positions,
            ranks,
            s=dot_size,
            color=color,
            zorder=zorder + 1,
            edgecolors="none",
        )


def _nudge_labels(labels: list[dict[str, Any]], min_gap: float) -> None:
    """Greedy vertical nudge to avoid overlapping labels.

    Labels must be pre-sorted top-to-bottom (ascending rank = ascending y
    since rank 1 is at top with inverted axis).
    Modifies label y-positions in place.
    """
    if len(labels) <= 1:
        return

    for i in range(1, len(labels)):
        gap = labels[i]["y"] - labels[i - 1]["y"]
        if gap < min_gap:
            labels[i]["y"] = labels[i - 1]["y"] + min_gap


def _draw_labels(
    ax: plt.Axes,
    ranked_data: dict[str, list[float]],
    x_positions: list[int],
    colors: dict[str, str],
    show_rank: bool,
) -> None:
    """Render right-side labels with optional rank number and collision avoidance."""
    fig = ax.get_figure()
    if fig is None:
        return
    fig.canvas.draw()

    # Estimate minimum gap in rank units
    y_min, y_max = ax.get_ylim()  # inverted: y_min > y_max
    fig_height = fig.get_size_inches()[1] * fig.dpi
    data_range = abs(y_min - y_max)
    min_gap = (TYPOGRAPHY.label_size * 1.8) / fig_height * data_range

    right_x = x_positions[-1]

    # Build label list
    right_labels: list[dict[str, Any]] = []
    for name, ranks in ranked_data.items():
        final_rank = ranks[-1]
        text = f"{name} #{int(final_rank)}" if show_rank else name
        right_labels.append(
            {
                "name": name,
                "y": final_rank,
                "text": text,
                "color": colors[name],
            }
        )

    # Sort by rank (ascending since rank 1 is at top)
    right_labels.sort(key=lambda lb: lb["y"])
    _nudge_labels(right_labels, min_gap)

    for lb in right_labels:
        ax.annotate(
            lb["text"],
            xy=(right_x, lb["y"]),
            xytext=(8, 0),
            textcoords="offset points",
            fontsize=TYPOGRAPHY.label_size,
            color=lb["color"],
            va="center",
            ha="left",
            zorder=5,
        )
