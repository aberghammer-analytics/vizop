"""Raincloud plot implementation for vizop."""

import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import gaussian_kde

from vizop.core.annotations import (
    Annotation,
    place_annotations,
    render_annotations,
    resolve_annotations,
)
from vizop.core.chart import Chart
from vizop.core.config import get_config
from vizop.core.palettes import assign_colors
from vizop.core.theme import BACKGROUND_COLORS, LAYOUT, apply_theme


def raincloud(
    data: pd.DataFrame,
    *,
    value: str | list[str],
    group: str | None = None,
    # Layer toggles
    show_density: bool = True,
    show_box: bool = True,
    show_points: bool = True,
    # Density tuning
    bandwidth: float | None = None,
    # Point tuning
    point_size: float = 12.0,
    jitter_width: float = 0.15,
    # Standard vizop params
    title: str | None = None,
    subtitle: str | None = None,
    source: str | None = None,
    note: str | None = None,
    accent_color: str | None = None,
    palette: str = "default",
    highlight: str | list[str] | None = None,
    color_map: dict[str, str] | None = None,
    gridlines: bool | None = None,
    size: str | None = None,
    annotate: list[Annotation] | None = None,
) -> Chart:
    """Create a horizontal raincloud plot from a DataFrame.

    Combines half-violin density, minimal box plot, and jittered strip plot
    for each group. Horizontal only — groups stacked vertically.

    Args:
        data: Source DataFrame.
        value: Value column name (long format) or list of column names (wide format).
        group: Column to group by (long format). Mutually exclusive with value as list.
        show_density: Show half-violin density curve. Default True.
        show_box: Show box plot (Q1-Q3, median, whiskers). Default True.
        show_points: Show jittered strip points. Default True.
        bandwidth: KDE bandwidth. None uses scipy default (Scott's rule).
        point_size: Point size in typographic points. Default 12.
        jitter_width: Vertical jitter range as fraction of lane height. Default 0.15.
        title: Chart title (left-aligned).
        subtitle: Subtitle below the title.
        source: Source attribution below the chart.
        note: Note text below the chart.
        accent_color: Override color for single-group charts.
        palette: Color palette name for multi-group.
        highlight: Group name(s) to highlight; others are muted.
        color_map: Dict mapping group names to hex colors.
        gridlines: Show gridlines on the value axis. None falls back to config default.
        size: Override figure size preset.
        annotate: List of Annotation objects to place on the chart.

    Returns:
        A Chart object wrapping the matplotlib figure.
    """
    _validate(data, value, group)
    config = get_config()

    if size is not None:
        config = config.model_copy(update={"size": size})

    # --- Data preparation ---
    group_data = _prepare_raincloud_data(data, value, group)
    group_names = list(group_data.keys())

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

    # --- Draw each group ---
    for i, name in enumerate(group_names):
        values = group_data[name]
        color = colors[name]
        y_center = i

        if show_density and len(values) >= 2:
            _draw_density(ax, values, y_center, color, bandwidth)
        if show_box:
            _draw_box(ax, values, y_center, color)
        if show_points:
            _draw_points(ax, values, y_center, color, point_size, jitter_width)

    # --- Set category labels on y-axis before apply_theme ---
    positions = np.arange(len(group_names))
    ax.set_yticks(positions)
    ax.set_yticklabels(group_names)

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
        skip_y_locator=True,
    )

    # --- Fix gridlines: value axis is x-axis (horizontal layout) ---
    if show_gridlines:
        ax.yaxis.grid(False)
        ax.xaxis.grid(
            True,
            color=LAYOUT.gridline_color,
            alpha=LAYOUT.gridline_alpha,
            linewidth=LAYOUT.gridline_linewidth,
        )

    # --- Add y-axis padding so density curves don't clip ---
    ax.set_ylim(-0.5, len(group_names) - 0.5)

    # --- Annotations ---
    if annotate:
        ann_series_data = _build_annotation_series(group_data)
        resolved = resolve_annotations(annotate, ann_series_data, is_date=False)
        placed = place_annotations(resolved, ax, series_data=ann_series_data)
        bg_color = BACKGROUND_COLORS.get(config.background, "#ffffff")
        render_annotations(placed, ax, bg_color=bg_color)

    return Chart(fig)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _validate(
    data: pd.DataFrame,
    value: str | list[str],
    group: str | None,
) -> None:
    """Validate inputs before creating any figure."""
    if data.empty:
        raise ValueError("DataFrame is empty. Cannot create chart.")

    available = list(data.columns)
    available_str = ", ".join(repr(c) for c in available)

    value_cols = [value] if isinstance(value, str) else value
    for col in value_cols:
        if col not in data.columns:
            raise ValueError(
                f"Column '{col}' not found in DataFrame. Available: {available_str}"
            )

    if group is not None:
        if group not in data.columns:
            raise ValueError(
                f"Column '{group}' not found in DataFrame. Available: {available_str}"
            )
        if isinstance(value, list):
            raise ValueError(
                "Cannot use both value as a list and group. "
                "Use value as a list for wide format, or value as a string with group "
                "for long format."
            )


def _prepare_raincloud_data(
    data: pd.DataFrame,
    value: str | list[str],
    group: str | None,
) -> dict[str, np.ndarray]:
    """Prepare raincloud data as {group_name: values_array}.

    Returns:
        Ordered dict mapping group names to numpy arrays of observations.
    """
    if group is not None:
        assert isinstance(value, str)
        result: dict[str, np.ndarray] = {}
        for name, sub_df in data.groupby(group, sort=True):
            vals = sub_df[value].dropna().to_numpy(dtype=float)
            if len(vals) > 0:
                result[str(name)] = vals
            else:
                warnings.warn(
                    f"Group '{name}' has no non-null values in column '{value}'.",
                    stacklevel=3,
                )
        return result

    if isinstance(value, list):
        # Wide format: each column becomes a group
        result = {}
        for col in value:
            vals = data[col].dropna().to_numpy(dtype=float)
            if len(vals) > 0:
                result[col] = vals
            else:
                warnings.warn(
                    f"Column '{col}' has no non-null values.",
                    stacklevel=3,
                )
        return result

    # Single value column, no group — one raincloud
    vals = data[value].dropna().to_numpy(dtype=float)
    return {value: vals}


def _compute_kde(
    values: np.ndarray,
    bandwidth: float | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Compute KDE for a single group.

    Returns:
        (x_grid, density) arrays where density is normalized to a max of ~0.4
        (half lane height) for visual proportion.
    """
    if bandwidth is not None:
        kde = gaussian_kde(values, bw_method=bandwidth)
    else:
        kde = gaussian_kde(values)

    x_min = values.min()
    x_max = values.max()
    padding = (x_max - x_min) * 0.05
    x_grid = np.linspace(x_min - padding, x_max + padding, 200)
    density = kde(x_grid)

    # Normalize so max density maps to ~0.4 of lane height (upper half only)
    max_density = density.max()
    if max_density > 0:
        density = density / max_density * 0.4

    return x_grid, density


def _draw_density(
    ax: plt.Axes,
    values: np.ndarray,
    y_center: float,
    color: str,
    bandwidth: float | None,
) -> None:
    """Render half-violin (density curve) for one group, extending upward."""
    x_grid, density = _compute_kde(values, bandwidth)

    # Upper half: density extends above the y_center
    ax.fill_between(
        x_grid,
        y_center,
        y_center + density,
        alpha=0.3,
        color=color,
        linewidth=0,
    )
    ax.plot(
        x_grid,
        y_center + density,
        color=color,
        linewidth=1.5,
    )


def _draw_box(
    ax: plt.Axes,
    values: np.ndarray,
    y_center: float,
    color: str,
) -> None:
    """Render box plot (Q1-Q3, median, whiskers) for one group."""
    q1 = np.percentile(values, 25)
    median = np.median(values)
    q3 = np.percentile(values, 75)
    iqr = q3 - q1

    # Whiskers: 1.5x IQR or data min/max if closer
    whisker_low = max(values.min(), q1 - 1.5 * iqr)
    whisker_high = min(values.max(), q3 + 1.5 * iqr)

    box_height = 0.08  # Half-height of box in lane units

    # Box outline (Q1 to Q3)
    box_rect = plt.Rectangle(
        (q1, y_center - box_height),
        q3 - q1,
        box_height * 2,
        linewidth=1.0,
        edgecolor=color,
        facecolor="none",
        zorder=3,
    )
    ax.add_patch(box_rect)

    # Median line (bold)
    ax.plot(
        [median, median],
        [y_center - box_height, y_center + box_height],
        color=color,
        linewidth=2.0,
        zorder=4,
    )

    # Whisker lines
    whisker_alpha = 0.6
    # Left whisker
    ax.plot(
        [whisker_low, q1],
        [y_center, y_center],
        color=color,
        linewidth=1.0,
        alpha=whisker_alpha,
        zorder=2,
    )
    # Right whisker
    ax.plot(
        [q3, whisker_high],
        [y_center, y_center],
        color=color,
        linewidth=1.0,
        alpha=whisker_alpha,
        zorder=2,
    )


def _draw_points(
    ax: plt.Axes,
    values: np.ndarray,
    y_center: float,
    color: str,
    point_size: float,
    jitter_width: float,
) -> None:
    """Render jittered strip plot below the lane baseline."""
    rng = np.random.default_rng(seed=42)
    jitter = rng.uniform(-jitter_width, 0, size=len(values))

    ax.scatter(
        values,
        y_center + jitter,
        s=point_size,
        color=color,
        alpha=0.6,
        edgecolors="none",
        zorder=2,
    )


def _build_annotation_series(
    group_data: dict[str, np.ndarray],
) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """Build series data for the annotation engine.

    Each group's values become x-coordinates; y-coordinates are the group's
    lane position repeated.
    """
    result: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for i, (name, values) in enumerate(group_data.items()):
        y_positions = np.full(len(values), float(i))
        result[name] = (values, y_positions)
    return result
