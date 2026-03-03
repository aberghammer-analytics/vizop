"""Scatter chart implementation for vizop."""

import warnings

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
from vizop.core.palettes import assign_colors, normalize_highlight
from vizop.core.theme import BACKGROUND_COLORS, LAYOUT, TYPOGRAPHY, apply_theme, draw_legend


def scatter(
    data: pd.DataFrame,
    *,
    x: str,
    y: str,
    group: str | None = None,
    size: str | None = None,
    label: str | None = None,
    title: str | None = None,
    subtitle: str | None = None,
    source: str | None = None,
    note: str | None = None,
    accent_color: str | None = None,
    palette: str = "default",
    highlight: str | list[str] | None = None,
    color_map: dict[str, str] | None = None,
    opacity: float = 0.7,
    jitter: bool = False,
    trend: str | None = None,
    log_x: bool = False,
    log_y: bool = False,
    zero_baseline: bool = False,
    gridlines: bool | None = None,
    figure_size: str | None = None,
    annotate: list[Annotation] | None = None,
    legend: str | bool | None = "top",
    max_groups: int = 6,
) -> Chart:
    """Create a scatter chart from a DataFrame.

    Args:
        data: Source DataFrame.
        x: Column name for the x-axis.
        y: Column name for the y-axis.
        group: Column to group by (produces colored point groups).
        size: Column for size encoding (bubble chart). Values normalized to [20, 200].
        label: Column for point labels. Auto-labels if <=20 points; warns and skips otherwise.
        title: Chart title (left-aligned).
        subtitle: Subtitle below the title.
        source: Source attribution below the chart.
        note: Note text below the chart.
        accent_color: Override color for single-series points.
        palette: Color palette name for grouped scatter.
        highlight: Group name(s) to highlight; others are muted.
        color_map: Dict mapping group names to hex colors.
        opacity: Point opacity (default 0.7).
        jitter: Add small random noise to both axes for overplotting.
        trend: Trend line type: "linear", "lowess", or None.
        log_x: Set x-axis to logarithmic scale.
        log_y: Set y-axis to logarithmic scale.
        zero_baseline: Force y-axis to start at 0.
        gridlines: Show gridlines on both axes. None falls back to config default.
        figure_size: Override figure size preset (uses "figure_size" to avoid
            collision with the size column parameter).
        annotate: List of Annotation objects to place on the chart.
        legend: Legend placement for grouped scatter. "top" (default), "bottom",
            "right", False, or None. Silently ignored for single-group.
        max_groups: Maximum number of distinct group values (default 6).

    Returns:
        A Chart object wrapping the matplotlib figure.
    """
    _validate(data, x, y, group, size, label, trend, legend, max_groups)
    config = get_config()

    if figure_size is not None:
        config = config.model_copy(update={"size": figure_size})

    # --- Data preparation ---
    series_data, size_data = _prepare_scatter_data(data, x, y, group, size, jitter)
    group_names = list(series_data.keys())
    is_multi = len(group_names) > 1

    # --- Color assignment ---
    colors = assign_colors(
        group_names,
        accent_color=accent_color,
        palette=palette,
        highlight=highlight,
        color_map=color_map,
        config_accent=config.accent_color,
    )

    # --- Create figure ---
    fig, ax = plt.subplots()

    # --- Log scales (set before plotting so data transforms correctly) ---
    if log_x:
        ax.set_xscale("log")
    if log_y:
        ax.set_yscale("log")

    # --- Determine draw order: muted first, highlighted last ---
    highlight_set = normalize_highlight(highlight)
    muted_names = []
    highlighted_names = []
    if highlight_set and is_multi:
        for name in group_names:
            if name in highlight_set:
                highlighted_names.append(name)
            else:
                muted_names.append(name)
    else:
        highlighted_names = group_names

    draw_order = muted_names + highlighted_names

    # --- Draw points ---
    for name in draw_order:
        x_vals, y_vals = series_data[name]
        color = colors[name]
        is_muted = name in muted_names
        point_alpha = 0.3 if is_muted else opacity
        zorder = 1 if is_muted else 3

        point_sizes = size_data.get(name) if size_data else None
        s = point_sizes if point_sizes is not None else LAYOUT.point_size

        ax.scatter(
            x_vals,
            y_vals,
            s=s,
            c=color,
            alpha=point_alpha,
            edgecolors="none",
            marker="o",
            label=name if is_multi else None,
            zorder=zorder,
        )

    # --- Trend line ---
    if trend is not None:
        _draw_trend_line(ax, series_data, trend)

    # --- Point labels ---
    if label is not None:
        _draw_point_labels(ax, data, x, y, label, jitter, series_data)

    # --- Zero baseline ---
    if zero_baseline:
        ax.set_ylim(bottom=0)

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

    # --- Scatter gridline exception: add vertical gridlines ---
    if show_gridlines:
        ax.xaxis.grid(
            True,
            color=LAYOUT.gridline_color,
            alpha=LAYOUT.gridline_alpha,
            linewidth=LAYOUT.gridline_linewidth,
        )

    # --- Legend for grouped scatter ---
    if is_multi:
        draw_legend(fig, ax, group_names, legend)

    # --- Annotations ---
    if annotate:
        resolved = resolve_annotations(annotate, series_data, is_date=False)
        placed = place_annotations(resolved, ax, series_data=series_data)
        bg_color = BACKGROUND_COLORS.get(config.background, "#ffffff")
        render_annotations(placed, ax, bg_color=bg_color)

    return Chart(fig)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _validate(
    data: pd.DataFrame,
    x: str,
    y: str,
    group: str | None,
    size: str | None,
    label: str | None,
    trend: str | None,
    legend: str | bool | None,
    max_groups: int,
) -> None:
    """Validate inputs before creating any figure."""
    if data.empty:
        raise ValueError("DataFrame is empty. Cannot create chart.")

    available = list(data.columns)
    available_str = ", ".join(repr(c) for c in available)

    if x not in data.columns:
        raise ValueError(f"Column '{x}' not found in DataFrame. Available: {available_str}")

    if y not in data.columns:
        raise ValueError(f"Column '{y}' not found in DataFrame. Available: {available_str}")

    if group is not None and group not in data.columns:
        raise ValueError(f"Column '{group}' not found in DataFrame. Available: {available_str}")

    if size is not None and size not in data.columns:
        raise ValueError(f"Column '{size}' not found in DataFrame. Available: {available_str}")

    if label is not None and label not in data.columns:
        raise ValueError(f"Column '{label}' not found in DataFrame. Available: {available_str}")

    if trend is not None and trend not in ("linear", "lowess"):
        raise ValueError(f"Invalid trend '{trend}'. Must be None, 'linear', or 'lowess'.")

    if legend is not None and legend is not False and legend not in ("top", "bottom", "right"):
        raise ValueError(
            f"Invalid legend '{legend}'. Must be 'top', 'bottom', 'right', False, or None."
        )

    if group is not None:
        n_groups = data[group].nunique()
        if n_groups > max_groups:
            raise ValueError(
                f"Too many groups: {n_groups} (max_groups={max_groups}). "
                f"Reduce groups or increase max_groups."
            )


def _prepare_scatter_data(
    data: pd.DataFrame,
    x: str,
    y: str,
    group: str | None,
    size: str | None,
    jitter: bool,
) -> tuple[dict[str, tuple[np.ndarray, np.ndarray]], dict[str, np.ndarray] | None]:
    """Prepare scatter data as {group: (x_array, y_array)} and optional size arrays.

    Returns:
        (series_data, size_data) where size_data is None if no size column.
    """
    df = data.copy()
    rng = np.random.default_rng(42)

    series_data: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    size_data: dict[str, np.ndarray] | None = None

    if group is not None:
        for group_val in sorted(df[group].unique(), key=str):
            subset = df[df[group] == group_val]
            x_vals = subset[x].to_numpy(dtype=float)
            y_vals = subset[y].to_numpy(dtype=float)
            series_data[str(group_val)] = (x_vals, y_vals)
    else:
        x_vals = df[x].to_numpy(dtype=float)
        y_vals = df[y].to_numpy(dtype=float)
        series_data["__single__"] = (x_vals, y_vals)

    # --- Jitter ---
    if jitter:
        all_x = np.concatenate([xv for xv, _ in series_data.values()])
        all_y = np.concatenate([yv for _, yv in series_data.values()])
        x_range = float(np.ptp(all_x)) if len(all_x) > 1 else 1.0
        y_range = float(np.ptp(all_y)) if len(all_y) > 1 else 1.0

        for name, (xv, yv) in series_data.items():
            x_noise = rng.normal(0, x_range * 0.01, size=len(xv))
            y_noise = rng.normal(0, y_range * 0.01, size=len(yv))
            series_data[name] = (xv + x_noise, yv + y_noise)

    # --- Size encoding ---
    if size is not None:
        size_data = {}
        if group is not None:
            for group_val in sorted(df[group].unique(), key=str):
                subset = df[df[group] == group_val]
                raw = subset[size].to_numpy(dtype=float)
                size_data[str(group_val)] = _normalize_sizes(raw)
        else:
            raw = df[size].to_numpy(dtype=float)
            size_data["__single__"] = _normalize_sizes(raw)

    return series_data, size_data


def _normalize_sizes(raw: np.ndarray) -> np.ndarray:
    """Normalize size values to range [20, 200] using min-max scaling."""
    min_val = float(np.nanmin(raw))
    max_val = float(np.nanmax(raw))
    if max_val == min_val:
        return np.full_like(raw, 110.0, dtype=float)  # midpoint
    normalized = (raw - min_val) / (max_val - min_val)
    return 20.0 + normalized * 180.0


def _draw_trend_line(
    ax: plt.Axes,
    series_data: dict[str, tuple[np.ndarray, np.ndarray]],
    trend: str,
) -> None:
    """Draw a trend line across all scatter data."""
    # Combine all points for the trend line
    all_x = np.concatenate([xv for xv, _ in series_data.values()])
    all_y = np.concatenate([yv for _, yv in series_data.values()])

    # Sort by x for clean line drawing
    sort_idx = np.argsort(all_x)
    all_x = all_x[sort_idx]
    all_y = all_y[sort_idx]

    trend_kwargs = {
        "linestyle": "--",
        "linewidth": 1.5,
        "color": "#888888",
        "zorder": 1,
    }

    if trend == "linear":
        coeffs = np.polyfit(all_x, all_y, 1)
        x_line = np.linspace(all_x.min(), all_x.max(), 100)
        y_line = np.polyval(coeffs, x_line)
        ax.plot(x_line, y_line, **trend_kwargs)
    elif trend == "lowess":
        try:
            from statsmodels.nonparametric.smoothers_lowess import lowess

            result = lowess(all_y, all_x, frac=0.3)
            ax.plot(result[:, 0], result[:, 1], **trend_kwargs)
        except ImportError:
            warnings.warn(
                "LOWESS trend requires statsmodels. Install with: pip install statsmodels. "
                "Falling back to linear trend.",
                stacklevel=3,
            )
            coeffs = np.polyfit(all_x, all_y, 1)
            x_line = np.linspace(all_x.min(), all_x.max(), 100)
            y_line = np.polyval(coeffs, x_line)
            ax.plot(x_line, y_line, **trend_kwargs)


def _draw_point_labels(
    ax: plt.Axes,
    data: pd.DataFrame,
    x: str,
    y: str,
    label_col: str,
    jitter: bool,
    series_data: dict[str, tuple[np.ndarray, np.ndarray]],
) -> None:
    """Draw text labels next to each point."""
    n_points = len(data)
    if n_points > 20:
        warnings.warn(
            f"Too many points ({n_points}) for labels. Skipping labels (max 20).",
            stacklevel=3,
        )
        return

    # Use the actual plotted positions (which may include jitter)
    # For ungrouped data, series_data has one key "__single__"
    if "__single__" in series_data:
        x_vals, y_vals = series_data["__single__"]
    else:
        # For grouped data, concatenate all series in original order
        x_vals = np.concatenate([xv for xv, _ in series_data.values()])
        y_vals = np.concatenate([yv for _, yv in series_data.values()])

    labels = data[label_col].tolist()

    for i, lbl in enumerate(labels):
        if i < len(x_vals):
            ax.annotate(
                str(lbl),
                xy=(x_vals[i], y_vals[i]),
                xytext=(5, 3),
                textcoords="offset points",
                fontsize=TYPOGRAPHY.label_size,
                color=TYPOGRAPHY.label_color,
                zorder=5,
            )
