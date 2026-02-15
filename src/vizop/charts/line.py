"""Line chart implementation for vizop."""

import contextlib
import warnings
from typing import Any

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from vizop.core.annotations import (
    Annotation,
    place_annotations,
    render_annotations,
    resolve_annotations,
)
from vizop.core.chart import Chart
from vizop.core.config import get_config
from vizop.core.formatting import auto_detect_format, format_value
from vizop.core.palettes import assign_colors, normalize_highlight
from vizop.core.theme import BACKGROUND_COLORS, LAYOUT, TYPOGRAPHY, apply_theme


def line(
    data: pd.DataFrame,
    *,
    x: str,
    y: str | list[str],
    group: str | None = None,
    title: str | None = None,
    subtitle: str | None = None,
    source: str | None = None,
    note: str | None = None,
    accent_color: str | None = None,
    palette: str = "default",
    highlight: str | list[str] | None = None,
    color_map: dict[str, str] | None = None,
    show_area: bool = False,
    zero_baseline: bool = False,
    show_last_value: bool = False,
    highlight_range: tuple[Any, Any] | None = None,
    highlight_range_label: str | None = None,
    gridlines: bool | None = None,
    size: str | None = None,
    annotate: list[Annotation] | None = None,
) -> Chart:
    """Create a line chart from a DataFrame.

    Args:
        data: Source DataFrame.
        x: Column name for the x-axis.
        y: Column name(s) for y-axis. String for single series, list for wide-format multi-series.
        group: Column to group by (long format). Mutually exclusive with y as list.
        title: Chart title (left-aligned).
        subtitle: Subtitle below the title.
        source: Source attribution below the chart.
        note: Note text below the chart.
        accent_color: Override color for single-series line.
        palette: Color palette name for multi-series.
        highlight: Series name(s) to highlight; others are muted.
        color_map: Dict mapping series names to hex colors. Unmapped series get gray.
        show_area: Fill area under the line (single-series only).
        zero_baseline: Force y-axis to start at 0.
        show_last_value: Show formatted value at the last data point.
        highlight_range: Tuple of (start, end) x-values to shade.
        highlight_range_label: Label for the shaded range.
        gridlines: Show horizontal gridlines. None falls back to config default.
        size: Override figure size preset.

    Returns:
        A Chart object wrapping the matplotlib figure.
    """
    _validate(data, x, y, group)
    config = get_config()

    if size is not None:
        config = config.model_copy(update={"size": size})

    # --- Data preparation ---
    series_data = _prepare_series(data, x, y, group)
    series_names = list(series_data.keys())
    is_multi = len(series_names) > 1
    is_date = _is_datetime(data[x])

    # --- Color assignment ---
    colors = assign_colors(
        series_names,
        accent_color=accent_color,
        palette=palette,
        highlight=highlight,
        color_map=color_map,
        config_accent=config.accent_color,
    )

    # --- Create figure ---
    fig, ax = plt.subplots()

    # --- Highlight range ---
    if highlight_range is not None:
        start, end = highlight_range
        if is_date:
            start = pd.to_datetime(start)
            end = pd.to_datetime(end)
        ax.axvspan(start, end, alpha=0.15, color="#b0b0b0", zorder=0)

    # --- Determine draw order: muted first, highlighted last ---
    highlight_set = normalize_highlight(highlight)
    muted_names = []
    highlighted_names = []
    if highlight_set and is_multi:
        for name in series_names:
            if name in highlight_set:
                highlighted_names.append(name)
            else:
                muted_names.append(name)
    else:
        highlighted_names = series_names

    draw_order = muted_names + highlighted_names

    # --- Draw lines ---
    for name in draw_order:
        x_vals, y_vals = series_data[name]
        color = colors[name]
        is_muted = name in muted_names
        lw = 1.0 if is_muted else LAYOUT.line_width
        ax.plot(x_vals, y_vals, color=color, linewidth=lw, label=name, zorder=2 if is_muted else 3)

    # --- Area fill (single-series only) ---
    if show_area and not is_multi:
        name = series_names[0]
        x_vals, y_vals = series_data[name]
        ax.fill_between(x_vals, y_vals, alpha=0.15, color=colors[name], zorder=1)
    elif show_area and is_multi:
        warnings.warn(
            "show_area is only supported for single-series line charts. Ignored.",
            stacklevel=2,
        )

    # --- Zero baseline ---
    if zero_baseline:
        ax.set_ylim(bottom=0)

    # --- Date formatting ---
    if is_date:
        locator = mdates.AutoDateLocator()
        formatter = mdates.ConciseDateFormatter(locator)
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(formatter)

    # --- Endpoint labels and show_last_value ---
    if is_multi:
        _draw_endpoint_labels(ax, series_data, colors, show_last_value, y)
    elif show_last_value:
        _draw_single_last_value(ax, series_data, colors, y)

    # --- Highlight range label (after data is plotted so ylim is set) ---
    if highlight_range is not None and highlight_range_label:
        start, end = highlight_range
        if is_date:
            start = pd.to_datetime(start)
            end = pd.to_datetime(end)
        mid = start + (end - start) / 2 if is_date else (start + end) / 2
        y_min, y_top = ax.get_ylim()
        y_inset = y_top - (y_top - y_min) * 0.02
        ax.text(
            mid,
            y_inset,
            highlight_range_label,
            ha="center",
            va="top",
            fontsize=TYPOGRAPHY.label_size,
            color=TYPOGRAPHY.label_color,
            zorder=5,
        )

    # --- Apply theme ---
    show_gridlines = gridlines if gridlines is not None else config.gridlines
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

    # --- Annotations ---
    if annotate:
        resolved = resolve_annotations(annotate, series_data, is_date)
        placed = place_annotations(resolved, ax, series_data=series_data)
        bg_color = BACKGROUND_COLORS.get(config.background, "#ffffff")
        render_annotations(placed, ax, bg_color=bg_color)

    return Chart(fig)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _validate(data: pd.DataFrame, x: str, y: str | list[str], group: str | None) -> None:
    """Validate inputs before creating any figure."""
    if data.empty:
        raise ValueError("DataFrame is empty. Cannot create chart.")

    available = list(data.columns)
    available_str = ", ".join(repr(c) for c in available)

    if x not in data.columns:
        raise ValueError(f"Column '{x}' not found in DataFrame. Available: {available_str}")

    y_cols = [y] if isinstance(y, str) else y
    for col in y_cols:
        if col not in data.columns:
            raise ValueError(f"Column '{col}' not found in DataFrame. Available: {available_str}")

    if group is not None:
        if group not in data.columns:
            raise ValueError(f"Column '{group}' not found in DataFrame. Available: {available_str}")
        if isinstance(y, list):
            raise ValueError(
                "Cannot use both y as a list and group. "
                "Use y as a list for wide format, or y as a string with group for long format."
            )


def _prepare_series(
    data: pd.DataFrame, x: str, y: str | list[str], group: str | None
) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """Prepare named series as {name: (x_values, y_values)}."""
    df = data.copy()

    # Convert x to datetime if parseable
    if not pd.api.types.is_datetime64_any_dtype(df[x]):
        with contextlib.suppress(ValueError, TypeError):
            df[x] = pd.to_datetime(df[x])

    result: dict[str, tuple[np.ndarray, np.ndarray]] = {}

    if group is not None:
        # Long format
        for group_val in sorted(df[group].unique()):
            subset = df[df[group] == group_val].sort_values(x)
            assert isinstance(y, str)
            result[str(group_val)] = (subset[x].to_numpy(), subset[y].to_numpy(dtype=float))
    elif isinstance(y, list):
        # Wide format
        sorted_df = df.sort_values(x)
        x_vals = sorted_df[x].to_numpy()
        for col in y:
            result[col] = (x_vals, sorted_df[col].to_numpy(dtype=float))
    else:
        # Single series
        sorted_df = df.sort_values(x)
        result[y] = (sorted_df[x].to_numpy(), sorted_df[y].to_numpy(dtype=float))

    return result


def _is_datetime(series: pd.Series) -> bool:
    """Check if a Series contains datetime values."""
    if pd.api.types.is_datetime64_any_dtype(series):
        return True
    try:
        pd.to_datetime(series)
        return True
    except (ValueError, TypeError):
        return False


def _draw_endpoint_labels(
    ax: plt.Axes,
    series_data: dict[str, tuple[np.ndarray, np.ndarray]],
    colors: dict[str, str],
    show_last_value: bool,
    y: str | list[str],
) -> None:
    """Draw direct labels at the rightmost point of each series."""
    labels: list[dict[str, Any]] = []

    for name, (x_vals, y_vals) in series_data.items():
        last_x = x_vals[-1]
        last_y = float(y_vals[-1])

        text = name
        if show_last_value:
            y_col = y if isinstance(y, str) else name
            fmt = auto_detect_format(y_col, pd.Series(y_vals))
            text = f"{name} {format_value(last_y, fmt)}"

        labels.append(
            {
                "name": name,
                "x": last_x,
                "y": last_y,
                "text": text,
                "color": colors[name],
            }
        )

    # Collision avoidance: greedy vertical nudge
    labels.sort(key=lambda lb: -lb["y"])  # top to bottom
    _nudge_labels(ax, labels)

    for lb in labels:
        ax.annotate(
            lb["text"],
            xy=(lb["x"], lb["y"]),
            xytext=(8, 0),
            textcoords="offset points",
            fontsize=TYPOGRAPHY.label_size,
            color=lb["color"],
            va="center",
            ha="left",
            zorder=5,
        )


def _nudge_labels(ax: plt.Axes, labels: list[dict[str, Any]]) -> None:
    """Greedy vertical nudge to avoid overlapping endpoint labels.

    Labels must be pre-sorted top-to-bottom (descending y).
    Modifies label y-positions in place.
    """
    if len(labels) <= 1:
        return

    # Estimate minimum gap in data coordinates from font size
    fig = ax.get_figure()
    if fig is None:
        return
    fig.canvas.draw()
    # Convert label font size (points) to data coordinates
    y_min, y_max = ax.get_ylim()
    fig_height = fig.get_size_inches()[1] * fig.dpi
    data_range = y_max - y_min
    min_gap = (TYPOGRAPHY.label_size * 1.8) / fig_height * data_range

    for i in range(1, len(labels)):
        gap = labels[i - 1]["y"] - labels[i]["y"]
        if gap < min_gap:
            labels[i]["y"] = labels[i - 1]["y"] - min_gap


def _draw_single_last_value(
    ax: plt.Axes,
    series_data: dict[str, tuple[np.ndarray, np.ndarray]],
    colors: dict[str, str],
    y: str | list[str],
) -> None:
    """Draw a formatted value label at the last point (single-series)."""
    name = next(iter(series_data))
    x_vals, y_vals = series_data[name]
    last_x = x_vals[-1]
    last_y = float(y_vals[-1])

    y_col = y if isinstance(y, str) else name
    fmt = auto_detect_format(y_col, pd.Series(y_vals))
    text = format_value(last_y, fmt)

    ax.annotate(
        text,
        xy=(last_x, last_y),
        xytext=(8, 0),
        textcoords="offset points",
        fontsize=TYPOGRAPHY.label_size,
        color=colors[name],
        va="center",
        ha="left",
        fontweight="bold",
        zorder=5,
    )
