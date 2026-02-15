"""Bar chart implementation for vizop."""

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
from vizop.core.formatting import auto_detect_format, format_value
from vizop.core.palettes import assign_colors, normalize_highlight
from vizop.core.theme import BACKGROUND_COLORS, LAYOUT, TYPOGRAPHY, apply_theme, draw_legend


def bar(
    data: pd.DataFrame,
    *,
    x: str,
    y: str | list[str],
    group: str | None = None,
    orientation: str = "horizontal",
    mode: str = "grouped",
    sort: str | None = "descending",
    limit: int | None = None,
    show_values: str | None = None,
    reference_line: float | None = None,
    reference_line_label: str | None = None,
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
    legend: str | bool | None = "top",
) -> Chart:
    """Create a bar chart from a DataFrame.

    Args:
        data: Source DataFrame.
        x: Category column name (always the categorical axis).
        y: Value column(s). String for single series, list for wide-format multi-series.
        group: Column to group by (long format). Mutually exclusive with y as list.
        orientation: "horizontal" (default) or "vertical".
        mode: "grouped" or "stacked" for multi-series.
        sort: "descending" (default), "ascending", or None to preserve DataFrame order.
        limit: Show only the top N categories after sorting.
        show_values: None (off), "inside", "inside_end", or "outside" — formatted value labels
            on bars. "inside_end" places labels near the tip of the bar, inside.
        reference_line: Draw a dashed reference line at this value.
        reference_line_label: Label for the reference line.
        title: Chart title (left-aligned).
        subtitle: Subtitle below the title.
        source: Source attribution below the chart.
        note: Note text below the chart.
        accent_color: Override color for single-series bars.
        palette: Color palette name for multi-series.
        highlight: Category/group name(s) to highlight; others are muted.
        color_map: Dict mapping names to hex colors. Unmapped names get gray.
        gridlines: Show gridlines on the value axis. None falls back to config default.
        size: Override figure size preset.
        annotate: List of Annotation objects to place on the chart.
        legend: Legend placement for multi-series charts. "top" (default), "bottom",
            "right", False, or None. Silently ignored for single-series.

    Returns:
        A Chart object wrapping the matplotlib figure.
    """
    _validate(data, x, y, group, orientation, mode, sort, show_values, legend)
    config = get_config()

    if size is not None:
        config = config.model_copy(update={"size": size})

    # --- Data preparation ---
    categories, series_data = _prepare_bar_data(data, x, y, group)
    series_names = list(series_data.keys())
    is_multi = len(series_names) > 1
    is_horizontal = orientation == "horizontal"

    # --- Validate grouped mode limit ---
    if is_multi and mode == "grouped" and len(series_names) > 4:
        raise ValueError(
            f"Grouped bar charts support at most 4 groups, got {len(series_names)}. "
            f"Use mode='stacked' for more groups."
        )

    # --- Sort and limit ---
    categories, series_data = _compute_sort_order(categories, series_data, sort, limit)

    # --- Color assignment ---
    if is_multi:
        # Multi-series: colors map to series/group names
        colors = assign_colors(
            series_names,
            accent_color=accent_color,
            palette=palette,
            highlight=highlight,
            color_map=color_map,
            config_accent=config.accent_color,
        )
    else:
        # Single-series: highlight targets categories
        highlight_set = normalize_highlight(highlight)
        if highlight_set or color_map:
            colors = _assign_category_colors(
                categories,
                accent_color=accent_color,
                palette=palette,
                highlight=highlight,
                color_map=color_map,
                config_accent=config.accent_color,
            )
        else:
            single_color = accent_color or config.accent_color
            colors = {cat: single_color for cat in categories}

    # --- Create figure ---
    fig, ax = plt.subplots()

    # --- Draw bars ---
    bar_containers = _draw_bars(ax, categories, series_data, colors, is_horizontal, mode, is_multi)

    # --- Set category labels before apply_theme so tight_layout accounts for their width ---
    positions = np.arange(len(categories))
    if is_horizontal:
        ax.set_yticks(positions)
        ax.set_yticklabels(categories)
    else:
        ax.set_xticks(positions)
        ax.set_xticklabels(categories)

    # --- Reference line ---
    if reference_line is not None:
        _draw_reference_line(ax, reference_line, reference_line_label, is_horizontal)

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

    # Push axes right so category labels don't overlap with the title at the figure margin
    if is_horizontal:
        fig.subplots_adjust(left=fig.subplotpars.left + 4 * LAYOUT.figure_margin)

    # --- Fix gridlines for bar charts ---
    # apply_theme puts gridlines on y-axis only. For horizontal bars, we need x-axis grid.
    if show_gridlines and is_horizontal:
        ax.yaxis.grid(False)
        ax.xaxis.grid(
            True,
            color=LAYOUT.gridline_color,
            alpha=LAYOUT.gridline_alpha,
            linewidth=LAYOUT.gridline_linewidth,
        )

    # --- Re-apply categorical ticks (MaxNLocator in apply_theme clobbers them) ---
    positions = np.arange(len(categories))
    if is_horizontal:
        ax.set_yticks(positions)
        ax.set_yticklabels(categories)
    else:
        ax.set_xticks(positions)
        ax.set_xticklabels(categories)

    # --- Value labels (after theme so figure layout is settled for pixel measurements) ---
    if show_values is not None:
        _draw_value_labels(ax, bar_containers, series_data, is_horizontal, show_values, y)

    # --- Legend for multi-series ---
    if is_multi:
        draw_legend(fig, ax, series_names, legend)

    # --- Annotations ---
    if annotate:
        # Build series_data in the format annotations expect: {name: (x_array, y_array)}
        # For bar charts, x-positions are integer indices of categories
        ann_series_data = _build_annotation_series(categories, series_data)
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
    x: str,
    y: str | list[str],
    group: str | None,
    orientation: str,
    mode: str,
    sort: str | None,
    show_values: str | None,
    legend: str | bool | None,
) -> None:
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

    if orientation not in ("horizontal", "vertical"):
        raise ValueError(
            f"Invalid orientation '{orientation}'. Must be 'horizontal' or 'vertical'."
        )

    if mode not in ("grouped", "stacked"):
        raise ValueError(f"Invalid mode '{mode}'. Must be 'grouped' or 'stacked'.")

    if sort not in ("descending", "ascending", None):
        raise ValueError(f"Invalid sort '{sort}'. Must be 'descending', 'ascending', or None.")

    if show_values not in (None, "inside", "inside_end", "outside"):
        raise ValueError(
            f"Invalid show_values '{show_values}'. "
            f"Must be None, 'inside', 'inside_end', or 'outside'."
        )

    if legend is not None and legend is not False and legend not in ("top", "bottom", "right"):
        raise ValueError(
            f"Invalid legend '{legend}'. Must be 'top', 'bottom', 'right', False, or None."
        )


def _prepare_bar_data(
    data: pd.DataFrame,
    x: str,
    y: str | list[str],
    group: str | None,
) -> tuple[list[str], dict[str, list[float]]]:
    """Prepare bar chart data.

    Returns:
        (categories, series_data) where series_data maps series names to value lists
        aligned with categories.
    """
    df = data.copy()

    if group is not None:
        # Long format: pivot to get categories × groups
        assert isinstance(y, str)
        pivot = df.pivot_table(index=x, columns=group, values=y, aggfunc="sum").fillna(0)
        categories = [str(c) for c in pivot.index.tolist()]
        series_data = {str(col): pivot[col].tolist() for col in pivot.columns}
    elif isinstance(y, list):
        # Wide format: each y column is a series
        grouped = df.groupby(x, sort=False)[y].sum()
        categories = [str(c) for c in grouped.index.tolist()]
        series_data = {col: grouped[col].tolist() for col in y}
    else:
        # Single series
        grouped = df.groupby(x, sort=False)[y].sum()
        categories = [str(c) for c in grouped.index.tolist()]
        series_data = {y: grouped.tolist()}

    return categories, series_data


def _compute_sort_order(
    categories: list[str],
    series_data: dict[str, list[float]],
    sort: str | None,
    limit: int | None,
) -> tuple[list[str], dict[str, list[float]]]:
    """Sort categories by total value across series and apply limit."""
    if sort is None and limit is None:
        return categories, series_data

    # Compute totals per category
    totals = [sum(series_data[s][i] for s in series_data) for i in range(len(categories))]
    indices = list(range(len(categories)))

    if sort == "descending":
        indices.sort(key=lambda i: totals[i], reverse=True)
    elif sort == "ascending":
        indices.sort(key=lambda i: totals[i])

    if limit is not None:
        indices = indices[:limit]

    sorted_categories = [categories[i] for i in indices]
    sorted_series = {name: [values[i] for i in indices] for name, values in series_data.items()}

    return sorted_categories, sorted_series


def _assign_category_colors(
    categories: list[str],
    *,
    accent_color: str | None,
    palette: str,
    highlight: str | list[str] | None,
    color_map: dict[str, str] | None,
    config_accent: str,
) -> dict[str, str]:
    """Assign colors to individual categories (single-series highlight/color_map)."""
    from vizop.core.palettes import HIGHLIGHT_MUTED_COLOR, get_colors

    if color_map:
        unknown = set(color_map) - set(categories)
        if unknown:
            warnings.warn(
                f"color_map contains keys not found in categories: {sorted(unknown)}",
                stacklevel=3,
            )

    # color_map takes priority
    if color_map is not None:
        base_color = accent_color or config_accent
        return {cat: color_map.get(cat, base_color) for cat in categories}

    # Highlight: highlighted categories get palette colors, rest are muted
    highlight_set = normalize_highlight(highlight)
    if highlight_set:
        highlighted = [c for c in categories if c in highlight_set]
        palette_colors = get_colors(len(highlighted), palette=palette, accent_color=accent_color)
        result: dict[str, str] = {}
        color_idx = 0
        for cat in categories:
            if cat in highlight_set:
                result[cat] = palette_colors[color_idx]
                color_idx += 1
            else:
                result[cat] = HIGHLIGHT_MUTED_COLOR
        return result

    # Fallback: all same color
    color = accent_color or config_accent
    return {cat: color for cat in categories}


def _draw_bars(
    ax: plt.Axes,
    categories: list[str],
    series_data: dict[str, list[float]],
    colors: dict[str, str],
    is_horizontal: bool,
    mode: str,
    is_multi: bool,
) -> list[plt.bar_label]:
    """Draw bars and return bar containers for value labeling.

    Returns a flat list of BarContainer objects.
    """
    positions = np.arange(len(categories))
    series_names = list(series_data.keys())
    n_series = len(series_names)
    bar_width = LAYOUT.bar_width
    containers = []

    if is_horizontal:
        # Reverse so largest (first after descending sort) appears at top
        positions = positions[::-1]

    if not is_multi:
        # Single-series: per-category colors
        name = series_names[0]
        values = series_data[name]
        bar_colors = [colors[cat] for cat in categories]
        if is_horizontal:
            container = ax.barh(
                positions, values, height=bar_width, color=bar_colors, edgecolor="none"
            )
        else:
            container = ax.bar(
                positions, values, width=bar_width, color=bar_colors, edgecolor="none"
            )
        containers.append(container)
    elif mode == "grouped":
        group_width = bar_width / n_series
        offsets = np.linspace(
            -(bar_width - group_width) / 2,
            (bar_width - group_width) / 2,
            n_series,
        )
        for idx, name in enumerate(series_names):
            values = series_data[name]
            if is_horizontal:
                container = ax.barh(
                    positions + offsets[idx],
                    values,
                    height=group_width * 0.9,
                    color=colors[name],
                    edgecolor="none",
                    label=name,
                )
            else:
                container = ax.bar(
                    positions + offsets[idx],
                    values,
                    width=group_width * 0.9,
                    color=colors[name],
                    edgecolor="none",
                    label=name,
                )
            containers.append(container)
    else:
        # Stacked
        cumulative = np.zeros(len(categories))
        for name in series_names:
            values = np.array(series_data[name])
            if is_horizontal:
                container = ax.barh(
                    positions,
                    values,
                    left=cumulative,
                    height=bar_width,
                    color=colors[name],
                    edgecolor="none",
                    label=name,
                )
            else:
                container = ax.bar(
                    positions,
                    values,
                    bottom=cumulative,
                    width=bar_width,
                    color=colors[name],
                    edgecolor="none",
                    label=name,
                )
            containers.append(container)
            cumulative += values

    return containers


def _draw_value_labels(
    ax: plt.Axes,
    containers: list,
    series_data: dict[str, list[float]],
    is_horizontal: bool,
    placement: str,
    y: str | list[str],
) -> None:
    """Draw formatted value labels on bars.

    Must be called AFTER apply_theme so the figure layout is settled and
    transData transforms return accurate pixel coordinates.
    """
    fig = ax.get_figure()
    if fig is None:
        return

    # Initialize transforms so pixel measurements are accurate
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()

    # Detect format from the first series
    first_name = next(iter(series_data))
    y_col = y if isinstance(y, str) else first_name
    fmt = auto_detect_format(y_col, pd.Series(series_data[first_name]))

    # Fixed offset in typographic points (1/72 inch) — independent of data scale
    label_offset_pts = 4

    has_outside_label = False

    for container in containers:
        for rect in container:
            value = rect.get_width() if is_horizontal else rect.get_height()

            if abs(value) == 0:
                continue

            text = format_value(value, fmt)

            # Measure text size in pixels to check if it fits inside the bar
            temp = ax.text(0, 0, text, fontsize=TYPOGRAPHY.label_size)
            text_bbox = temp.get_window_extent(renderer=renderer)
            temp.remove()

            if is_horizontal:
                bar_px = abs(
                    ax.transData.transform((value, 0))[0]
                    - ax.transData.transform((0, 0))[0]
                )
                fits_inside = bar_px > text_bbox.width * 1.5
                bar_center = (
                    rect.get_x() + rect.get_width() / 2,
                    rect.get_y() + rect.get_height() / 2,
                )
                bar_end = (
                    rect.get_x() + rect.get_width(),
                    rect.get_y() + rect.get_height() / 2,
                )

                if placement == "inside" and fits_inside:
                    ax.annotate(
                        text,
                        xy=bar_center,
                        ha="center",
                        va="center",
                        fontsize=TYPOGRAPHY.label_size,
                        color="white",
                        fontweight="bold",
                        zorder=4,
                    )
                elif placement == "inside_end" and fits_inside:
                    ax.annotate(
                        text,
                        xy=bar_end,
                        xytext=(-label_offset_pts, 0),
                        textcoords="offset points",
                        ha="right",
                        va="center",
                        fontsize=TYPOGRAPHY.label_size,
                        color="white",
                        fontweight="bold",
                        zorder=4,
                    )
                else:
                    has_outside_label = True
                    ax.annotate(
                        text,
                        xy=bar_end,
                        xytext=(label_offset_pts, 0),
                        textcoords="offset points",
                        ha="left",
                        va="center",
                        fontsize=TYPOGRAPHY.label_size,
                        color=TYPOGRAPHY.label_color,
                        zorder=4,
                    )
            else:
                bar_px = abs(
                    ax.transData.transform((0, value))[1]
                    - ax.transData.transform((0, 0))[1]
                )
                fits_inside = bar_px > text_bbox.height * 1.5
                bar_center = (
                    rect.get_x() + rect.get_width() / 2,
                    rect.get_y() + rect.get_height() / 2,
                )
                bar_top = (
                    rect.get_x() + rect.get_width() / 2,
                    rect.get_y() + rect.get_height(),
                )

                if placement == "inside" and fits_inside:
                    ax.annotate(
                        text,
                        xy=bar_center,
                        ha="center",
                        va="center",
                        fontsize=TYPOGRAPHY.label_size,
                        color="white",
                        fontweight="bold",
                        zorder=4,
                    )
                elif placement == "inside_end" and fits_inside:
                    ax.annotate(
                        text,
                        xy=bar_top,
                        xytext=(0, -label_offset_pts),
                        textcoords="offset points",
                        ha="center",
                        va="top",
                        fontsize=TYPOGRAPHY.label_size,
                        color="white",
                        fontweight="bold",
                        zorder=4,
                    )
                else:
                    has_outside_label = True
                    ax.annotate(
                        text,
                        xy=bar_top,
                        xytext=(0, label_offset_pts),
                        textcoords="offset points",
                        ha="center",
                        va="bottom",
                        fontsize=TYPOGRAPHY.label_size,
                        color=TYPOGRAPHY.label_color,
                        zorder=4,
                    )

    # Expand value axis so outside labels aren't clipped against the axis edge
    if has_outside_label:
        _add_value_axis_margin(ax, is_horizontal)


def _add_value_axis_margin(ax: plt.Axes, is_horizontal: bool) -> None:
    """Add margin to the value axis to accommodate outside labels."""
    if is_horizontal:
        x_min, x_max = ax.get_xlim()
        ax.set_xlim(x_min, x_max + (x_max - x_min) * 0.06)
    else:
        y_min, y_max = ax.get_ylim()
        ax.set_ylim(y_min, y_max + (y_max - y_min) * 0.06)


def _draw_reference_line(
    ax: plt.Axes,
    value: float,
    label: str | None,
    is_horizontal: bool,
) -> None:
    """Draw a dashed reference line with optional label."""
    line_kwargs = {
        "color": TYPOGRAPHY.label_color,
        "linestyle": "--",
        "linewidth": 1.0,
        "zorder": 3,
    }
    if is_horizontal:
        ax.axvline(value, **line_kwargs)
    else:
        ax.axhline(value, **line_kwargs)

    if label:
        if is_horizontal:
            ax.text(
                value,
                1.02,
                label,
                transform=ax.get_xaxis_transform(),
                ha="center",
                va="bottom",
                fontsize=TYPOGRAPHY.label_size,
                color=TYPOGRAPHY.label_color,
            )
        else:
            ax.text(
                1.02,
                value,
                label,
                transform=ax.get_yaxis_transform(),
                ha="left",
                va="center",
                fontsize=TYPOGRAPHY.label_size,
                color=TYPOGRAPHY.label_color,
            )


def _build_annotation_series(
    categories: list[str],
    series_data: dict[str, list[float]],
) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """Build series_data in the format the annotation engine expects.

    Categories are mapped to integer positions so the annotation snap/lookup works.
    """
    positions = np.arange(len(categories), dtype=float)
    result: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for name, values in series_data.items():
        result[name] = (positions, np.array(values, dtype=float))
    return result
