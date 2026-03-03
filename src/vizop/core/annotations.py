"""Annotation model, placement, and rendering for vizop charts."""

import warnings
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pydantic import BaseModel

from vizop.core.theme import TYPOGRAPHY


class Annotation(BaseModel):
    """A text annotation placed near a data point on a chart.

    Attributes:
        x: x-value to annotate (date, number, or string).
        label: Text to display.
        y: y-value at the annotation point. Auto-looked-up from data if None.
        series: Which series to annotate (required for multi-series if ambiguous).
        connector: Draw a connector line from label to point.
            None = automatic (draw if label was nudged away),
            True = always draw, False = never draw.
    """

    x: Any
    label: str
    y: float | None = None
    series: str | None = None
    connector: bool | None = None


# ---------------------------------------------------------------------------
# Resolved annotation (internal, post-lookup)
# ---------------------------------------------------------------------------


class _ResolvedAnnotation(BaseModel):
    """Internal model after y-lookup and validation."""

    data_x: Any  # actual x-value in data coordinates
    data_y: float  # resolved y-value
    label: str
    connector: bool | None  # user preference (None=auto)
    series_name: str = ""  # which series this annotation belongs to


# ---------------------------------------------------------------------------
# Resolution: auto Y-lookup + validation
# ---------------------------------------------------------------------------

_SNAP_TOLERANCE = 0.05  # 5% of x-axis range


def resolve_annotations(
    annotations: list[Annotation],
    series_data: dict[str, tuple[np.ndarray, np.ndarray]],
    is_date: bool,
) -> list[_ResolvedAnnotation]:
    """Resolve annotation y-values and validate against series data.

    Args:
        annotations: User-provided annotations.
        series_data: {series_name: (x_array, y_array)} from _prepare_series.
        is_date: Whether the x-axis is datetime.

    Returns:
        List of resolved annotations ready for placement.

    Raises:
        ValueError: If series not found or x-value can't be snapped.
    """
    series_names = list(series_data.keys())
    is_multi = len(series_names) > 1
    resolved: list[_ResolvedAnnotation] = []

    for ann in annotations:
        # --- Determine target series ---
        if ann.series is not None:
            if ann.series not in series_names:
                available = ", ".join(repr(s) for s in series_names)
                raise ValueError(
                    f"Annotation series '{ann.series}' not found. Available: {available}"
                )
            target_series = ann.series
        elif is_multi:
            target_series = series_names[0]
            warnings.warn(
                f"Annotation at x={ann.x!r} has no series specified in a multi-series chart. "
                f"Defaulting to '{target_series}'.",
                stacklevel=2,
            )
        else:
            target_series = series_names[0]

        x_vals, y_vals = series_data[target_series]

        # --- Resolve y-value ---
        if ann.y is not None:
            # User provided explicit y — just resolve the x for positioning
            data_x = _snap_x(ann.x, x_vals, is_date)
            resolved.append(
                _ResolvedAnnotation(
                    data_x=data_x,
                    data_y=ann.y,
                    label=ann.label,
                    connector=ann.connector,
                    series_name=target_series,
                )
            )
        else:
            # Auto-lookup y from the series
            data_x, data_y = _lookup_y(ann.x, x_vals, y_vals, is_date)
            resolved.append(
                _ResolvedAnnotation(
                    data_x=data_x,
                    data_y=data_y,
                    label=ann.label,
                    connector=ann.connector,
                    series_name=target_series,
                )
            )

    return resolved


def _snap_x(
    target_x: Any,
    x_vals: np.ndarray,
    is_date: bool,
) -> Any:
    """Find the nearest x-value in the data, within snap tolerance.

    Returns the snapped data x-value.
    """
    if is_date:
        target_x = pd.to_datetime(target_x)

    numeric_x = _to_numeric(x_vals, is_date)
    target_num = _to_numeric(np.array([target_x]), is_date)[0]

    x_range = float(numeric_x.max() - numeric_x.min()) if len(numeric_x) > 1 else 1.0
    distances = np.abs(numeric_x - target_num)
    best_idx = int(np.argmin(distances))
    best_dist = distances[best_idx]

    if x_range > 0 and best_dist / x_range > _SNAP_TOLERANCE:
        raise ValueError(
            f"Annotation x={target_x!r} is too far from any data point "
            f"(nearest is {x_vals[best_idx]!r}, distance {best_dist / x_range:.1%} of range). "
            f"Snap tolerance is {_SNAP_TOLERANCE:.0%}."
        )

    return x_vals[best_idx]


def _lookup_y(
    target_x: Any,
    x_vals: np.ndarray,
    y_vals: np.ndarray,
    is_date: bool,
) -> tuple[Any, float]:
    """Look up the y-value for the nearest x-value."""
    snapped_x = _snap_x(target_x, x_vals, is_date)
    # Find the index of the snapped x
    if is_date:
        mask = x_vals == snapped_x
    else:
        mask = np.isclose(
            _to_numeric(x_vals, is_date),
            _to_numeric(np.array([snapped_x]), is_date)[0],
        )
    idx = int(np.argmax(mask))
    return snapped_x, float(y_vals[idx])


def _to_numeric(arr: np.ndarray, is_date: bool) -> np.ndarray:
    """Convert array to numeric values for distance calculations."""
    if is_date:
        return pd.to_datetime(arr).values.astype(np.float64)
    return arr.astype(np.float64)


# ---------------------------------------------------------------------------
# Direction constants for preferred annotation placement
# ---------------------------------------------------------------------------

_DEFAULT_OFFSET_PT = 20.0  # default vertical offset in points

_ABOVE = (0.0, _DEFAULT_OFFSET_PT)
_BELOW = (0.0, -_DEFAULT_OFFSET_PT)
_ABOVE_LEFT = (-40.0, _DEFAULT_OFFSET_PT)
_ABOVE_RIGHT = (40.0, _DEFAULT_OFFSET_PT)
_FAR_ABOVE = (0.0, _DEFAULT_OFFSET_PT * 2)
_FAR_BELOW = (0.0, -_DEFAULT_OFFSET_PT * 2)

_BASE_CANDIDATES = [_ABOVE, _FAR_ABOVE, _BELOW, _ABOVE_LEFT, _ABOVE_RIGHT, _FAR_BELOW]


def _find_point_index(
    data_x: Any,
    data_y: float,
    x_vals: np.ndarray,
    y_vals: np.ndarray,
) -> int:
    """Find the index of a data point in the series arrays."""
    for i, (xv, yv) in enumerate(zip(x_vals, y_vals, strict=True)):
        if not np.isclose(float(yv), data_y, rtol=1e-9):
            continue
        if isinstance(data_x, (pd.Timestamp, np.datetime64)):
            if pd.Timestamp(xv) == pd.Timestamp(data_x):
                return i
        elif np.isclose(float(xv), float(data_x), rtol=1e-9):
            return i
    return 0


def _detect_preferred_direction(
    data_x: Any,
    data_y: float,
    x_vals: np.ndarray,
    y_vals: np.ndarray,
) -> tuple[float, float]:
    """Determine the best initial label offset based on the local line shape.

    Analyzes neighbors of the annotation point to classify whether it sits
    at a peak, valley, rising slope, or falling slope, then returns an offset
    direction that places the label on the "open" side of the line.

    Args:
        data_x: The x-coordinate of the annotation point.
        data_y: The y-coordinate of the annotation point.
        x_vals: All x-values of the series (sorted).
        y_vals: Corresponding y-values.

    Returns:
        (offset_x_pt, offset_y_pt) — a preferred direction constant.
    """
    idx = _find_point_index(data_x, data_y, x_vals, y_vals)
    n = len(y_vals)

    # Edge points: only one neighbor, default to above
    if idx == 0 or idx >= n - 1:
        return _ABOVE

    y_prev = float(y_vals[idx - 1])
    y_next = float(y_vals[idx + 1])

    # Use a fraction of the local range as a threshold so tiny wiggles
    # don't trigger peak/valley classification
    y_range = float(np.ptp(y_vals)) if len(y_vals) > 1 else 1.0
    threshold = y_range * 0.02  # 2% of total series range

    above_prev = (data_y - y_prev) > threshold
    above_next = (data_y - y_next) > threshold
    below_prev = (y_prev - data_y) > threshold
    below_next = (y_next - data_y) > threshold

    if above_prev and above_next:
        return _BELOW  # peak — place label underneath
    if below_prev and below_next:
        return _ABOVE  # valley — above is safe
    if above_next or below_prev:
        return _ABOVE_LEFT  # rising slope — shift left to avoid upward line
    if below_next or above_prev:
        return _ABOVE_RIGHT  # falling slope — shift right

    return _ABOVE  # flat or ambiguous — default


# ---------------------------------------------------------------------------
# Line-aware helpers for collision scoring
# ---------------------------------------------------------------------------

_LINE_OVERLAP_WEIGHT = 3.0  # penalize line overlap more heavily than label overlap


def _series_to_display(
    series_data: dict[str, tuple[np.ndarray, np.ndarray]],
    ax: plt.Axes,
) -> list[np.ndarray]:
    """Convert all series data to display (pixel) coordinate arrays.

    Returns a list of Nx2 arrays, one per series.
    """
    display_lines: list[np.ndarray] = []
    for x_vals, y_vals in series_data.values():
        points = np.array(
            [
                ax.transData.transform((_to_display_x(xv), float(yv)))
                for xv, yv in zip(x_vals, y_vals, strict=True)
            ]
        )
        display_lines.append(points)
    return display_lines


def _compute_line_overlap(
    center_x: float,
    center_y: float,
    label_w_pt: float,
    label_h_pt: float,
    display_lines: list[np.ndarray],
) -> float:
    """Compute penalty for a label bbox overlapping plotted line segments.

    Checks whether any sampled line points fall within the label's bounding
    box in display coordinates.  Each hit contributes a fraction of the
    label area so the metric is comparable to label-label overlap.
    """
    half_w = label_w_pt / 2
    half_h = label_h_pt / 2
    left = center_x - half_w
    right = center_x + half_w
    bottom = center_y - half_h
    top = center_y + half_h

    label_area = label_w_pt * label_h_pt
    total = 0.0

    for pts in display_lines:
        if len(pts) == 0:
            continue
        in_x = (pts[:, 0] >= left) & (pts[:, 0] <= right)
        in_y = (pts[:, 1] >= bottom) & (pts[:, 1] <= top)
        hits = int(np.sum(in_x & in_y))
        if hits > 0:
            total += label_area * 0.5 * hits

    return total * _LINE_OVERLAP_WEIGHT


# ---------------------------------------------------------------------------
# Label placement with collision avoidance
# ---------------------------------------------------------------------------


class _PlacedLabel:
    """A label with final display position."""

    __slots__ = ("data_x", "data_y", "label", "connector", "offset_x_pt", "offset_y_pt", "nudged")

    def __init__(
        self,
        data_x: Any,
        data_y: float,
        label: str,
        connector: bool | None,
    ) -> None:
        self.data_x = data_x
        self.data_y = data_y
        self.label = label
        self.connector = connector
        self.offset_x_pt = 0.0
        self.offset_y_pt = _DEFAULT_OFFSET_PT
        self.nudged = False


def place_annotations(
    resolved: list[_ResolvedAnnotation],
    ax: plt.Axes,
    series_data: dict[str, tuple[np.ndarray, np.ndarray]] | None = None,
) -> list[_PlacedLabel]:
    """Place annotation labels with collision avoidance.

    Labels are positioned using three layered strategies:
    1. **Slope-aware default**: local line shape picks the best initial direction.
    2. **Line-aware scoring**: candidate positions are penalised for overlapping
       plotted line segments, not just other labels.
    3. A background box (applied during rendering) provides a final safety net.

    Args:
        resolved: Resolved annotations with data coordinates.
        ax: The matplotlib axes (used for coordinate transforms).
        series_data: {series_name: (x_array, y_array)} — pass this to enable
            slope-aware defaults and line-overlap scoring.

    Returns:
        List of placed labels with final offset positions.
    """
    if not resolved:
        return []

    placed = [
        _PlacedLabel(
            data_x=r.data_x,
            data_y=r.data_y,
            label=r.label,
            connector=r.connector,
        )
        for r in resolved
    ]

    # Estimate label dimensions in points for overlap detection
    label_height_pt = TYPOGRAPHY.label_size * 1.4
    label_width_pt = TYPOGRAPHY.label_size * 4.0

    # Pre-compute display-coord line paths for line-aware scoring
    display_lines = _series_to_display(series_data, ax) if series_data else []

    for i in range(len(placed)):
        r = resolved[i]

        # --- Layer 1: slope-aware preferred direction ---
        preferred = _ABOVE
        if series_data and r.series_name and r.series_name in series_data:
            x_vals, y_vals = series_data[r.series_name]
            preferred = _detect_preferred_direction(r.data_x, r.data_y, x_vals, y_vals)

        # Build candidate list with preferred direction first
        if preferred in _BASE_CANDIDATES:
            candidates = [preferred] + [c for c in _BASE_CANDIDATES if c != preferred]
        else:
            candidates = [preferred] + list(_BASE_CANDIDATES)

        best_offset = candidates[0]
        best_score = float("inf")

        for cx, cy in candidates:
            # Label-to-label overlap
            label_overlap = _compute_overlap(placed, i, cx, cy, label_width_pt, label_height_pt, ax)

            # --- Layer 2: line-aware overlap ---
            line_overlap = 0.0
            if display_lines:
                display_xy = ax.transData.transform(
                    (_to_display_x(placed[i].data_x), placed[i].data_y)
                )
                line_overlap = _compute_line_overlap(
                    display_xy[0] + cx,
                    display_xy[1] + cy,
                    label_width_pt,
                    label_height_pt,
                    display_lines,
                )

            score = label_overlap + line_overlap
            if score < best_score:
                best_score = score
                best_offset = (cx, cy)
                if score == 0:
                    break  # perfect position found

        placed[i].offset_x_pt = best_offset[0]
        placed[i].offset_y_pt = best_offset[1]
        if best_offset != candidates[0]:
            placed[i].nudged = True

    return placed


def _compute_overlap(
    placed: list[_PlacedLabel],
    current_idx: int,
    offset_x_pt: float,
    offset_y_pt: float,
    label_w_pt: float,
    label_h_pt: float,
    ax: plt.Axes,
) -> float:
    """Compute total overlap area between the current label and all prior placed labels."""
    fig = ax.get_figure()
    if fig is None:
        return 0.0

    # Get display position for the current label's data point
    current = placed[current_idx]
    display_xy = ax.transData.transform(
        (
            _to_display_x(current.data_x),
            current.data_y,
        )
    )
    cx = display_xy[0] + offset_x_pt
    cy = display_xy[1] + offset_y_pt

    total_overlap = 0.0

    for j in range(current_idx):
        other = placed[j]
        other_display = ax.transData.transform(
            (
                _to_display_x(other.data_x),
                other.data_y,
            )
        )
        ox = other_display[0] + other.offset_x_pt
        oy = other_display[1] + other.offset_y_pt

        # Rectangle overlap (label bounding boxes in display coords)
        x_overlap = max(
            0,
            min(cx + label_w_pt / 2, ox + label_w_pt / 2)
            - max(cx - label_w_pt / 2, ox - label_w_pt / 2),
        )
        y_overlap = max(
            0,
            min(cy + label_h_pt / 2, oy + label_h_pt / 2)
            - max(cy - label_h_pt / 2, oy - label_h_pt / 2),
        )
        total_overlap += x_overlap * y_overlap

    return total_overlap


def _to_display_x(data_x: Any) -> float:
    """Convert a data x-value to a float suitable for transData."""
    if isinstance(data_x, (pd.Timestamp, np.datetime64)):
        return float(pd.Timestamp(data_x).value)
    return float(data_x)


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

_CONNECTOR_COLOR = "#cccccc"
_CONNECTOR_WIDTH = 0.8
_DOT_SIZE = 3.0
_AUTO_CONNECTOR_THRESHOLD_PT = 20.0


def render_annotations(
    placed: list[_PlacedLabel],
    ax: plt.Axes,
    bg_color: str = "#ffffff",
) -> None:
    """Render annotation labels and connectors on the axes.

    Args:
        placed: Labels with final positions from place_annotations().
        ax: The matplotlib axes to draw on.
        bg_color: Background color for the text halo box (Layer 3 safety net).
    """
    for p in placed:
        # Determine whether to draw connector
        draw_connector = _should_draw_connector(p)

        # --- Connector line + dot ---
        if draw_connector:
            ax.annotate(
                "",
                xy=(p.data_x, p.data_y),
                xytext=(p.offset_x_pt, p.offset_y_pt),
                textcoords="offset points",
                arrowprops={
                    "arrowstyle": "-",
                    "color": _CONNECTOR_COLOR,
                    "linewidth": _CONNECTOR_WIDTH,
                },
                zorder=5,
            )
            ax.plot(
                p.data_x,
                p.data_y,
                "o",
                color=_CONNECTOR_COLOR,
                markersize=_DOT_SIZE,
                zorder=5,
            )

        # --- Label text with background halo ---
        ax.annotate(
            p.label,
            xy=(p.data_x, p.data_y),
            xytext=(p.offset_x_pt, p.offset_y_pt),
            textcoords="offset points",
            fontsize=TYPOGRAPHY.label_size,
            color=TYPOGRAPHY.label_color,
            ha="center",
            va="bottom",
            fontweight="bold",
            zorder=6,
            bbox={
                "boxstyle": "round,pad=0.15",
                "facecolor": bg_color,
                "edgecolor": "none",
                "alpha": 0.85,
            },
        )


def _should_draw_connector(p: _PlacedLabel) -> bool:
    """Determine whether to draw a connector for this label."""
    if p.connector is True:
        return True
    if p.connector is False:
        return False
    # Auto: draw if label was nudged or offset exceeds threshold
    offset_dist = (p.offset_x_pt**2 + p.offset_y_pt**2) ** 0.5
    return p.nudged or offset_dist > _AUTO_CONNECTOR_THRESHOLD_PT
