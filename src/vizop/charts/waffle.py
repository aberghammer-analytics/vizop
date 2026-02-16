"""Waffle chart implementation for vizop."""

import math
import warnings

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.path import Path as MplPath
from matplotlib.transforms import Affine2D

from vizop.core.annotations import Annotation
from vizop.core.chart import Chart
from vizop.core.config import get_config
from vizop.core.icons import get_icon
from vizop.core.palettes import assign_colors, normalize_highlight
from vizop.core.theme import LAYOUT, apply_theme, draw_legend

_MAX_CATEGORIES = 7
_CELL_GAP = 0.08
_SQUARE_ROUNDING = 0.05


def waffle(
    data: pd.DataFrame | None = None,
    *,
    category: str | None = None,
    value: str | None = None,
    values: dict[str, float] | None = None,
    style: str = "square",
    icon: str | MplPath | None = None,
    grid_size: int = 10,
    title: str | None = None,
    subtitle: str | None = None,
    source: str | None = None,
    note: str | None = None,
    accent_color: str | None = None,
    palette: str = "default",
    highlight: str | list[str] | None = None,
    color_map: dict[str, str] | None = None,
    size: str | None = None,
    annotate: list[Annotation] | None = None,
    legend: str | bool | None = "top",
) -> Chart:
    """Create a waffle chart.

    Two input modes (mutually exclusive):
    - DataFrame mode: ``waffle(data, category="col", value="col")``
    - Dict mode: ``waffle(values={"A": 65, "B": 35})``

    Args:
        data: Source DataFrame (DataFrame mode).
        category: Column name for category labels (DataFrame mode).
        value: Column name for numeric values (DataFrame mode).
        values: Dict of category names to numeric values (dict mode).
        style: Cell style — "square", "circle", or "icon".
        icon: Built-in icon name or matplotlib Path (required when style="icon").
        grid_size: Number of cells per row/column (default 10, producing 100 cells).
        title: Chart title (left-aligned).
        subtitle: Subtitle below the title.
        source: Source attribution below the chart.
        note: Note text below the chart.
        accent_color: Override color for single-category charts.
        palette: Color palette name.
        highlight: Category name(s) to highlight; others are muted.
        color_map: Dict mapping category names to hex colors.
        size: Override figure size preset.
        annotate: List of Annotation objects.
        legend: Legend placement — "bottom" (default), "top", "right", False, or None.

    Returns:
        A Chart object wrapping the matplotlib figure.
    """
    # --- Validation (before figure creation) ---
    _validate(data, category, value, values, style, icon, legend)
    config = get_config()

    if size is None:
        size = "square"
    config = config.model_copy(update={"size": size})

    # --- Prepare category data ---
    cat_values = _prepare_data(data, category, value, values)

    # --- Merge excess categories ---
    cat_values = _merge_categories(cat_values)

    # --- Normalize to grid cells ---
    total_cells = grid_size ** 2
    cell_counts = _normalize_largest_remainder(cat_values, total_cells)

    # --- Color assignment ---
    cat_names = list(cat_values.keys())
    colors = assign_colors(
        cat_names,
        accent_color=accent_color,
        palette=palette,
        highlight=highlight,
        color_map=color_map,
        config_accent=config.accent_color,
    )

    # --- Highlight alpha ---
    highlight_set = normalize_highlight(highlight)

    # --- Build cell grid (left-to-right, top-to-bottom, grouped by category) ---
    cell_categories = _build_cell_list(cat_names, cell_counts)

    # --- Create figure ---
    fig, ax = plt.subplots()

    # --- Draw cells ---
    icon_path = get_icon(icon) if style == "icon" else None

    for idx, cat_name in enumerate(cell_categories):
        row = idx // grid_size
        col = idx % grid_size
        x = col
        y = (grid_size - 1) - row  # row 0 = top

        color = colors[cat_name]
        alpha = 0.3 if (highlight_set and cat_name not in highlight_set) else 1.0

        if style == "square":
            _draw_square(ax, x, y, color, alpha)
        elif style == "circle":
            _draw_circle(ax, x, y, color, alpha)
        elif style == "icon":
            assert icon_path is not None
            _draw_icon(ax, x, y, icon_path, color, alpha)

    # --- Configure axes ---
    ax.set_xlim(-0.5, grid_size - 0.5)
    ax.set_ylim(-0.5, grid_size - 0.5)
    ax.set_aspect("equal")
    ax.axis("off")

    # --- Apply theme (title/subtitle/source/background) ---
    apply_theme(
        fig,
        ax,
        config=config,
        title=title,
        subtitle=subtitle,
        source=source,
        note=note,
        gridlines=False,
    )

    # Re-hide axes after apply_theme (it may configure spines/ticks)
    ax.axis("off")

    # --- Left-align the waffle grid with title/subtitle text ---
    # Must happen BEFORE draw_legend so legend x-position is computed from final axes position.
    pos = ax.get_position()
    ax.set_position([LAYOUT.figure_margin, pos.y0, pos.width, pos.height])

    # --- Legend ---
    if legend is not False and legend is not None and len(cat_names) > 1:
        # Create proxy artists for legend
        for name in cat_names:
            ax.plot([], [], "s", color=colors[name], label=name, markersize=8)
        draw_legend(fig, ax, cat_names, legend)

    return Chart(fig)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _validate(
    data: pd.DataFrame | None,
    category: str | None,
    value: str | None,
    values: dict[str, float] | None,
    style: str,
    icon: str | MplPath | None,
    legend: str | bool | None,
) -> None:
    """Validate inputs before creating any figure."""
    has_df = data is not None
    has_dict = values is not None

    if has_df and has_dict:
        raise ValueError(
            "Cannot use both DataFrame (data/category/value) and dict (values) inputs. "
            "Provide one or the other."
        )

    if not has_df and not has_dict:
        raise ValueError(
            "Must provide either DataFrame (data, category, value) or dict (values) input."
        )

    if has_df:
        if data.empty:
            raise ValueError("DataFrame is empty. Cannot create chart.")
        available = list(data.columns)
        available_str = ", ".join(repr(c) for c in available)
        if category is None:
            raise ValueError("Must provide 'category' column name with DataFrame input.")
        if value is None:
            raise ValueError("Must provide 'value' column name with DataFrame input.")
        if category not in data.columns:
            raise ValueError(
                f"Column '{category}' not found in DataFrame. Available: {available_str}"
            )
        if value not in data.columns:
            raise ValueError(
                f"Column '{value}' not found in DataFrame. Available: {available_str}"
            )

    if has_dict:
        if not values:
            raise ValueError("values dict is empty. Cannot create chart.")
        if any(v < 0 for v in values.values()):
            raise ValueError("All values must be >= 0.")

    if style not in ("square", "circle", "icon"):
        raise ValueError(f"Invalid style '{style}'. Must be 'square', 'circle', or 'icon'.")

    if style == "icon" and icon is None:
        raise ValueError("Must provide 'icon' when style='icon'.")

    if legend is not None and legend is not False and legend not in ("top", "bottom", "right"):
        raise ValueError(
            f"Invalid legend '{legend}'. Must be 'top', 'bottom', 'right', False, or None."
        )


# ---------------------------------------------------------------------------
# Data preparation
# ---------------------------------------------------------------------------


def _prepare_data(
    data: pd.DataFrame | None,
    category: str | None,
    value: str | None,
    values: dict[str, float] | None,
) -> dict[str, float]:
    """Convert inputs to a {category: value} dict."""
    if values is not None:
        return dict(values)

    assert data is not None and category is not None and value is not None
    grouped = data.groupby(category, sort=False)[value].sum()
    return {str(k): float(v) for k, v in grouped.items()}


def _merge_categories(cat_values: dict[str, float]) -> dict[str, float]:
    """Merge excess categories into 'Other' if more than _MAX_CATEGORIES."""
    if len(cat_values) <= _MAX_CATEGORIES:
        return cat_values

    warnings.warn(
        f"Waffle chart has {len(cat_values)} categories; merging smallest into 'Other' "
        f"(max {_MAX_CATEGORIES}).",
        stacklevel=3,
    )

    sorted_items = sorted(cat_values.items(), key=lambda kv: kv[1], reverse=True)
    keep = _MAX_CATEGORIES - 1  # reserve one slot for "Other"
    result = dict(sorted_items[:keep])
    other_total = sum(v for _, v in sorted_items[keep:])
    result["Other"] = other_total
    return result


def _normalize_largest_remainder(
    cat_values: dict[str, float], total_cells: int
) -> dict[str, int]:
    """Allocate cells to categories using the largest remainder method.

    Guarantees the sum of allocated cells equals total_cells exactly.
    """
    total = sum(cat_values.values())
    if total == 0:
        # All zeros: distribute evenly
        n = len(cat_values)
        base = total_cells // n
        remainder = total_cells % n
        result = {}
        for i, name in enumerate(cat_values):
            result[name] = base + (1 if i < remainder else 0)
        return result

    # Compute exact proportions and floor
    proportions = {name: (val / total) * total_cells for name, val in cat_values.items()}
    floored = {name: math.floor(p) for name, p in proportions.items()}
    remainders = {name: proportions[name] - floored[name] for name in proportions}

    allocated = sum(floored.values())
    deficit = total_cells - allocated

    # Distribute deficit to categories with largest fractional remainders
    sorted_by_remainder = sorted(remainders, key=lambda n: remainders[n], reverse=True)
    for i in range(deficit):
        floored[sorted_by_remainder[i]] += 1

    return floored


# ---------------------------------------------------------------------------
# Grid building
# ---------------------------------------------------------------------------


def _build_cell_list(cat_names: list[str], cell_counts: dict[str, int]) -> list[str]:
    """Build a flat list of category names, one per cell, grouped by category."""
    cells: list[str] = []
    for name in cat_names:
        cells.extend([name] * cell_counts[name])
    return cells


# ---------------------------------------------------------------------------
# Cell renderers
# ---------------------------------------------------------------------------


def _draw_square(ax: plt.Axes, x: float, y: float, color: str, alpha: float) -> None:
    """Draw a rounded square cell."""
    gap = _CELL_GAP
    size = 1.0 - gap
    patch = mpatches.FancyBboxPatch(
        (x - size / 2, y - size / 2),
        size,
        size,
        boxstyle=f"round,pad=0,rounding_size={_SQUARE_ROUNDING}",
        facecolor=color,
        edgecolor="none",
        alpha=alpha,
    )
    ax.add_patch(patch)


def _draw_circle(ax: plt.Axes, x: float, y: float, color: str, alpha: float) -> None:
    """Draw a circle cell."""
    patch = mpatches.Circle(
        (x, y),
        radius=0.4,
        facecolor=color,
        edgecolor="none",
        alpha=alpha,
    )
    ax.add_patch(patch)


def _draw_icon(
    ax: plt.Axes, x: float, y: float, icon_path: MplPath, color: str, alpha: float
) -> None:
    """Draw a scaled icon cell from a unit-square Path."""
    scale = 0.8  # slightly smaller than cell to leave visual gap
    transform = Affine2D().scale(scale).translate(x - scale / 2, y - scale / 2)
    transformed_path = icon_path.transformed(transform)
    patch = mpatches.PathPatch(
        transformed_path,
        facecolor=color,
        edgecolor="none",
        alpha=alpha,
    )
    ax.add_patch(patch)
