"""Slope chart implementation for vizop."""

import warnings
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd

from vizop.core.annotations import Annotation
from vizop.core.chart import Chart
from vizop.core.config import get_config
from vizop.core.fonts import get_font_family
from vizop.core.formatting import auto_detect_format, format_value
from vizop.core.palettes import assign_colors, normalize_highlight
from vizop.core.theme import LAYOUT, TYPOGRAPHY, apply_theme

# Default direction colors (Tableau blue/red)
_DIRECTION_UP = "#4E79A7"
_DIRECTION_DOWN = "#E15759"

# Span presets: control figure width (axes proximity)
_SPAN_WIDTHS: dict[str, float] = {
    "narrow": 4.5,
    "medium": 6.0,
    "wide": 8.0,
}


def slope(
    data: pd.DataFrame,
    *,
    # Wide format
    label: str | None = None,
    left: str | None = None,
    right: str | None = None,
    # Long format
    x: str | None = None,
    y: str | None = None,
    group: str | None = None,
    # Appearance
    title: str | None = None,
    subtitle: str | None = None,
    source: str | None = None,
    note: str | None = None,
    accent_color: str | None = None,
    palette: str = "default",
    highlight: str | list[str] | None = None,
    color_map: dict[str, str] | None = None,
    color_by_direction: bool | dict[str, str] = False,
    # Data options
    show_change: bool = False,
    show_axes: bool = True,
    show_verticals: bool = False,
    sort: str | None = None,
    limit: int | None = None,
    # Theme
    gridlines: bool = False,
    size: str | None = None,
    span: str | None = None,
    annotate: list[Annotation] | None = None,
) -> Chart:
    """Create a slope chart from a DataFrame.

    Supports two input formats (mutually exclusive):

    **Wide format** — each row is an entity:
        label, left, right columns required together.

    **Long format** — two rows per entity:
        x, y, group columns required together. x must have exactly 2 unique values.

    Args:
        data: Source DataFrame.
        label: Column with entity names (wide format).
        left: Column with left/start values (wide format).
        right: Column with right/end values (wide format).
        x: Column distinguishing two time points (long format).
        y: Column with numeric values (long format).
        group: Column identifying entities (long format).
        title: Chart title (left-aligned).
        subtitle: Subtitle below the title.
        source: Source attribution below the chart.
        note: Note text below the chart.
        accent_color: Override color for single-color slopes.
        palette: Color palette name.
        highlight: Entity name(s) to highlight; others are muted.
        color_map: Dict mapping entity names to hex colors.
        color_by_direction: Color by value change direction. True for defaults,
            or dict with "up"/"down" keys for custom colors.
        show_change: Append formatted delta to right-side labels.
        show_axes: Show column header labels below the axes (default True).
        show_verticals: Show vertical reference lines at each column (default False).
        sort: "ascending" or "descending" by left value, or None to preserve order.
        limit: Show only top N entities after sorting.
        gridlines: Show horizontal gridlines (default False).
        size: Override figure size preset.
        span: Distance between axes — "narrow" (4.5"), "medium" (6.0"),
            or "wide" (8.0"). Defaults to "medium" unless size is set.
            Overrides figure width only; height from size preset.
        annotate: List of Annotation objects.

    Returns:
        A Chart object wrapping the matplotlib figure.
    """
    _validate(data, label, left, right, x, y, group, sort, span)
    config = get_config()

    if size is not None:
        config = config.model_copy(update={"size": size})

    # --- Determine format and prepare data ---
    is_wide = label is not None
    slope_data, left_header, right_header = _prepare_slope_data(
        data, label, left, right, x, y, group, is_wide
    )

    # --- Sort and limit ---
    entity_names = list(slope_data.keys())

    if sort == "ascending":
        entity_names.sort(key=lambda n: slope_data[n][0])
    elif sort == "descending":
        entity_names.sort(key=lambda n: slope_data[n][0], reverse=True)

    if limit is not None:
        entity_names = entity_names[:limit]

    if len(entity_names) > 15 and limit is None:
        warnings.warn(
            f"Slope chart has {len(entity_names)} entities. "
            f"Consider using limit= to reduce clutter.",
            stacklevel=2,
        )

    # Rebuild ordered slope_data
    slope_data = {n: slope_data[n] for n in entity_names}

    # --- Color assignment ---
    colors = _assign_slope_colors(
        entity_names,
        slope_data,
        accent_color=accent_color,
        palette=palette,
        highlight=highlight,
        color_map=color_map,
        color_by_direction=color_by_direction,
        config_accent=config.accent_color,
    )

    # --- Create figure ---
    fig, ax = plt.subplots()

    # --- Draw slope lines and dots ---
    _draw_slope_lines(ax, slope_data, colors, highlight)

    # --- Apply theme, then customize for slope layout ---
    show_gridlines = gridlines
    apply_theme(
        fig,
        ax,
        config=config,
        title=title,
        subtitle=subtitle,
        source=source,
        note=note,
        gridlines=show_gridlines,
    )

    # --- Apply span width override (after theme sets initial size) ---
    # Default to "medium" when neither span nor size is explicitly set.
    effective_span = span if span is not None else ("medium" if size is None else None)
    if effective_span is not None:
        _, fig_height = fig.get_size_inches()
        fig.set_size_inches(_SPAN_WIDTHS[effective_span], fig_height)

    # --- Slope-specific axis customization ---
    # Hide y-axis ticks and labels (values shown as endpoint labels)
    ax.set_yticks([])
    ax.set_yticklabels([])

    # X-axis: show column headers below the vertical spines, or hide
    if show_axes:
        font_family = get_font_family(config)
        ax.set_xticks([0, 1])
        ax.set_xticklabels([str(left_header), str(right_header)])
        ax.tick_params(axis="x", length=0, pad=8)
        for tick_label in ax.get_xticklabels():
            tick_label.set_fontweight("bold")
            tick_label.set_fontsize(TYPOGRAPHY.label_size)
            tick_label.set_color(TYPOGRAPHY.label_color)
            tick_label.set_fontfamily(font_family)
    else:
        ax.set_xticks([])
        ax.set_xticklabels([])

    # Hide default spines (we draw custom vertical column spines)
    for spine in ax.spines.values():
        spine.set_visible(False)

    # Draw thin vertical spines at left and right positions
    all_vals = [v for lv, rv in slope_data.values() for v in (lv, rv)]
    y_min, y_max = min(all_vals), max(all_vals)
    y_pad = (y_max - y_min) * 0.08 if y_max != y_min else 1.0
    ax.set_ylim(y_min - y_pad, y_max + y_pad)
    ax.set_xlim(-0.3, 1.3)

    if show_verticals:
        ax.plot(
            [0, 0],
            [y_min - y_pad, y_max + y_pad],
            color=LAYOUT.spine_color,
            linewidth=LAYOUT.spine_linewidth,
            zorder=1,
        )
        ax.plot(
            [1, 1],
            [y_min - y_pad, y_max + y_pad],
            color=LAYOUT.spine_color,
            linewidth=LAYOUT.spine_linewidth,
            zorder=1,
        )

    # --- Draw labels with collision avoidance ---
    _draw_labels(ax, slope_data, colors, show_change, left, right, y, is_wide)

    return Chart(fig)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _validate(
    data: pd.DataFrame,
    label: str | None,
    left: str | None,
    right: str | None,
    x: str | None,
    y: str | None,
    group: str | None,
    sort: str | None,
    span: str | None,
) -> None:
    """Validate inputs before creating any figure."""
    if data.empty:
        raise ValueError("DataFrame is empty. Cannot create chart.")

    available = list(data.columns)
    available_str = ", ".join(repr(c) for c in available)

    wide_params = (label, left, right)
    long_params = (x, y, group)
    has_wide = any(p is not None for p in wide_params)
    has_long = any(p is not None for p in long_params)

    # Must provide exactly one format
    if has_wide and has_long:
        raise ValueError(
            "Cannot mix wide format (label/left/right) and long format (x/y/group). "
            "Use one or the other."
        )

    if not has_wide and not has_long:
        raise ValueError(
            "Must provide either wide format (label, left, right) or "
            "long format (x, y, group) parameters."
        )

    if has_wide:
        if not all(p is not None for p in wide_params):
            raise ValueError("Wide format requires all three: label, left, and right.")
        for _col_name, col_val in [("label", label), ("left", left), ("right", right)]:
            if col_val not in data.columns:
                raise ValueError(
                    f"Column '{col_val}' not found in DataFrame. Available: {available_str}"
                )

    if has_long:
        if not all(p is not None for p in long_params):
            raise ValueError("Long format requires all three: x, y, and group.")
        for _col_name, col_val in [("x", x), ("y", y), ("group", group)]:
            if col_val not in data.columns:
                raise ValueError(
                    f"Column '{col_val}' not found in DataFrame. Available: {available_str}"
                )
        # Long format must have exactly 2 unique x-values
        assert x is not None
        n_unique = data[x].nunique()
        if n_unique != 2:
            raise ValueError(
                f"Long format requires exactly 2 unique x-values, got {n_unique}. "
                f"Unique values: {sorted(data[x].unique().tolist())}"
            )

    if sort is not None and sort not in ("ascending", "descending"):
        raise ValueError(f"Invalid sort '{sort}'. Must be 'ascending', 'descending', or None.")

    if span is not None and span not in _SPAN_WIDTHS:
        valid = ", ".join(repr(k) for k in _SPAN_WIDTHS)
        raise ValueError(f"Invalid span '{span}'. Must be one of: {valid}.")


def _prepare_slope_data(
    data: pd.DataFrame,
    label: str | None,
    left: str | None,
    right: str | None,
    x: str | None,
    y: str | None,
    group: str | None,
    is_wide: bool,
) -> tuple[dict[str, tuple[float, float]], str, str]:
    """Normalize both formats into {entity_name: (left_val, right_val)}.

    Returns:
        (slope_data, left_header, right_header)
    """
    if is_wide:
        assert label is not None and left is not None and right is not None
        result: dict[str, tuple[float, float]] = {}
        for _, row in data.iterrows():
            name = str(row[label])
            result[name] = (float(row[left]), float(row[right]))
        return result, left, right
    else:
        assert x is not None and y is not None and group is not None
        x_vals = sorted(data[x].unique().tolist(), key=str)
        left_header, right_header = str(x_vals[0]), str(x_vals[1])

        result = {}
        for grp_val in data[group].unique():
            subset = data[data[group] == grp_val]
            left_row = subset[subset[x] == x_vals[0]]
            right_row = subset[subset[x] == x_vals[1]]
            if not left_row.empty and not right_row.empty:
                result[str(grp_val)] = (
                    float(left_row[y].iloc[0]),
                    float(right_row[y].iloc[0]),
                )
        return result, left_header, right_header


def _assign_slope_colors(
    entity_names: list[str],
    slope_data: dict[str, tuple[float, float]],
    *,
    accent_color: str | None,
    palette: str,
    highlight: str | list[str] | None,
    color_map: dict[str, str] | None,
    color_by_direction: bool | dict[str, str],
    config_accent: str,
) -> dict[str, str]:
    """Assign colors following priority: color_map > highlight > color_by_direction > palette."""
    # color_map takes top priority
    if color_map:
        return assign_colors(
            entity_names,
            accent_color=accent_color,
            palette=palette,
            highlight=highlight,
            color_map=color_map,
            config_accent=config_accent,
        )

    # highlight takes second priority
    if highlight:
        return assign_colors(
            entity_names,
            accent_color=accent_color,
            palette=palette,
            highlight=highlight,
            config_accent=config_accent,
        )

    # color_by_direction
    if color_by_direction is not False:
        if isinstance(color_by_direction, dict):
            up_color = color_by_direction.get("up", _DIRECTION_UP)
            down_color = color_by_direction.get("down", _DIRECTION_DOWN)
        else:
            up_color = _DIRECTION_UP
            down_color = _DIRECTION_DOWN

        return {
            name: up_color if slope_data[name][1] >= slope_data[name][0] else down_color
            for name in entity_names
        }

    # Default: palette / accent
    return assign_colors(
        entity_names,
        accent_color=accent_color,
        palette=palette,
        highlight=None,
        config_accent=config_accent,
    )


def _draw_slope_lines(
    ax: plt.Axes,
    slope_data: dict[str, tuple[float, float]],
    colors: dict[str, str],
    highlight: str | list[str] | None,
) -> None:
    """Render slope lines and endpoint dots, muted-first draw order."""
    highlight_set = normalize_highlight(highlight)
    entity_names = list(slope_data.keys())

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
        left_val, right_val = slope_data[name]
        color = colors[name]
        is_muted = name in muted_names
        lw = 1.0 if is_muted else LAYOUT.line_width
        zorder = 2 if is_muted else 3

        # Line
        ax.plot([0, 1], [left_val, right_val], color=color, linewidth=lw, zorder=zorder)

        # Endpoint dots (6px)
        dot_size = 36  # matplotlib scatter size is area in points^2; 6px diameter ~ 36
        ax.scatter([0], [left_val], s=dot_size, color=color, zorder=zorder + 1, edgecolors="none")
        ax.scatter([1], [right_val], s=dot_size, color=color, zorder=zorder + 1, edgecolors="none")


def _nudge_labels(labels: list[dict[str, Any]], min_gap: float) -> None:
    """Greedy vertical nudge to avoid overlapping labels.

    Labels must be pre-sorted top-to-bottom (descending y).
    Modifies label y-positions in place.
    """
    if len(labels) <= 1:
        return

    for i in range(1, len(labels)):
        gap = labels[i - 1]["y"] - labels[i]["y"]
        if gap < min_gap:
            labels[i]["y"] = labels[i - 1]["y"] - min_gap


def _draw_labels(
    ax: plt.Axes,
    slope_data: dict[str, tuple[float, float]],
    colors: dict[str, str],
    show_change: bool,
    left_col: str | None,
    right_col: str | None,
    y_col: str | None,
    is_wide: bool,
) -> None:
    """Render left/right labels with optional delta text and collision avoidance."""
    fig = ax.get_figure()
    if fig is None:
        return
    fig.canvas.draw()

    # Estimate minimum gap in data coordinates
    y_min, y_max = ax.get_ylim()
    fig_height = fig.get_size_inches()[1] * fig.dpi
    data_range = y_max - y_min
    min_gap = (TYPOGRAPHY.label_size * 1.8) / fig_height * data_range

    # Detect format for value formatting
    all_left = [lv for lv, _ in slope_data.values()]
    all_right = [rv for _, rv in slope_data.values()]

    if is_wide:
        assert left_col is not None and right_col is not None
        left_fmt = auto_detect_format(left_col, pd.Series(all_left))
        right_fmt = auto_detect_format(right_col, pd.Series(all_right))
    else:
        assert y_col is not None
        all_vals = all_left + all_right
        left_fmt = auto_detect_format(y_col, pd.Series(all_vals))
        right_fmt = left_fmt

    # --- Left labels ---
    left_labels: list[dict[str, Any]] = []
    for name, (left_val, _) in slope_data.items():
        text = f"{name} {format_value(left_val, left_fmt)}"
        left_labels.append({"name": name, "y": left_val, "text": text, "color": colors[name]})

    left_labels.sort(key=lambda lb: -lb["y"])
    _nudge_labels(left_labels, min_gap)

    for lb in left_labels:
        ax.annotate(
            lb["text"],
            xy=(0, lb["y"]),
            xytext=(-8, 0),
            textcoords="offset points",
            fontsize=TYPOGRAPHY.label_size,
            color=lb["color"],
            va="center",
            ha="right",
            zorder=5,
        )

    # --- Right labels ---
    right_labels: list[dict[str, Any]] = []
    for name, (left_val, right_val) in slope_data.items():
        text = f"{name} {format_value(right_val, right_fmt)}"
        if show_change:
            delta = right_val - left_val
            delta_fmt = right_fmt
            prefix = "+" if delta >= 0 else ""
            delta_text = f"({prefix}{format_value(delta, delta_fmt)})"
            text = f"{text} {delta_text}"
        right_labels.append({"name": name, "y": right_val, "text": text, "color": colors[name]})

    right_labels.sort(key=lambda lb: -lb["y"])
    _nudge_labels(right_labels, min_gap)

    for lb in right_labels:
        ax.annotate(
            lb["text"],
            xy=(1, lb["y"]),
            xytext=(8, 0),
            textcoords="offset points",
            fontsize=TYPOGRAPHY.label_size,
            color=lb["color"],
            va="center",
            ha="left",
            zorder=5,
        )
