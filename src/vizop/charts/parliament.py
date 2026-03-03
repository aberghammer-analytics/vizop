"""Parliament (hemicycle) chart implementation for vizop."""

import math

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import pandas as pd

from vizop.core.annotations import Annotation
from vizop.core.chart import Chart
from vizop.core.config import get_config
from vizop.core.palettes import assign_colors, normalize_highlight
from vizop.core.theme import LAYOUT, TYPOGRAPHY, apply_theme, draw_legend


def parliament(
    data: pd.DataFrame | None = None,
    *,
    party: str | None = None,
    seats: str | None = None,
    values: dict[str, int] | None = None,
    rows: int | None = None,
    arc_degrees: float = 180.0,
    inner_radius: float = 0.4,
    majority_line: bool | int = False,
    center_label: str | bool = True,
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
    legend: str | bool | None = "bottom",
) -> Chart:
    """Create a parliament (hemicycle) chart.

    Two input modes (mutually exclusive):
    - DataFrame mode: ``parliament(data, party="col", seats="col")``
    - Dict mode: ``parliament(values={"Democrats": 213, "Republicans": 222})``

    Args:
        data: Source DataFrame (DataFrame mode).
        party: Column name for party labels (DataFrame mode).
        seats: Column name for seat counts (DataFrame mode).
        values: Dict of party names to seat counts (dict mode).
        rows: Number of arc rows (auto-calculated if None).
        arc_degrees: Arc span in degrees (default 180 = semicircle).
        inner_radius: Radius of innermost row as fraction of outer (0.0–1.0).
        majority_line: Draw majority threshold line. True = auto, int = custom.
        center_label: Label at arc center. True = total seats, str = custom, False = none.
        title: Chart title (left-aligned).
        subtitle: Subtitle below the title.
        source: Source attribution below the chart.
        note: Note text below the chart.
        accent_color: Override color for single-party charts.
        palette: Color palette name.
        highlight: Party name(s) to highlight; others are muted.
        color_map: Dict mapping party names to hex colors.
        size: Override figure size preset.
        annotate: List of Annotation objects.
        legend: Legend placement — "bottom" (default), "top", "right", False, or None.

    Returns:
        A Chart object wrapping the matplotlib figure.
    """
    # --- Validation (before figure creation) ---
    _validate(data, party, seats, values, arc_degrees, inner_radius, rows, legend)
    config = get_config()

    if size is None:
        size = "wide"
    config = config.model_copy(update={"size": size})

    # --- Prepare party data ---
    party_seats = _prepare_data(data, party, seats, values)
    total_seats = sum(party_seats.values())

    # --- Seat layout ---
    num_rows = _auto_rows(total_seats) if rows is None else rows
    arc_radians = math.radians(arc_degrees)
    seat_positions, seats_per_row = _compute_seat_positions(
        total_seats, num_rows, arc_radians, inner_radius
    )

    # --- Assign parties to seats (contiguous wedge fill) ---
    seat_parties, sorted_party_names = _assign_parties_wedge(party_seats, seats_per_row)

    # --- Color assignment (use size-sorted order) ---
    colors = assign_colors(
        sorted_party_names,
        accent_color=accent_color,
        palette=palette,
        highlight=highlight,
        color_map=color_map,
        config_accent=config.accent_color,
    )

    # --- Highlight alpha ---
    highlight_set = normalize_highlight(highlight)

    # --- Compute dot radius ---
    dot_radius = _dot_radius(num_rows, inner_radius)

    # --- Create figure ---
    fig, ax = plt.subplots()

    # --- Draw seat dots ---
    for (x, y), party_name in zip(seat_positions, seat_parties, strict=True):
        color = colors[party_name]
        alpha = 0.3 if (highlight_set and party_name not in highlight_set) else 1.0
        patch = mpatches.Circle(
            (x, y),
            radius=dot_radius,
            facecolor=color,
            edgecolor="none",
            alpha=alpha,
        )
        ax.add_patch(patch)

    # --- Majority line ---
    if majority_line is not False:
        threshold = total_seats // 2 + 1 if majority_line is True else int(majority_line)
        _draw_majority_line(ax, seat_positions, threshold, arc_radians, inner_radius, dot_radius)

    # --- Center label ---
    if center_label is not False:
        label_text = str(total_seats) if center_label is True else str(center_label)
        ax.text(
            0,
            0,
            label_text,
            ha="center",
            va="center",
            fontsize=TYPOGRAPHY.title_size,
            fontweight="bold",
            color=TYPOGRAPHY.title_color,
        )

    # --- Configure axes ---
    ax.set_aspect("equal")
    ax.set_anchor("W")
    ax.axis("off")
    # Auto-scale to fit all dots
    ax.autoscale_view()

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

    # Re-hide axes after apply_theme
    ax.axis("off")

    # --- Left-align to figure margin ---
    pos = ax.get_position()
    ax.set_position([LAYOUT.figure_margin, pos.y0, pos.width, pos.height])

    # --- Legend ---
    if legend is not False and legend is not None and len(sorted_party_names) > 1:
        handles = [
            mpatches.Rectangle((0, 0), 1, 1, facecolor=colors[name], edgecolor="none", label=name)
            for name in sorted_party_names
        ]
        draw_legend(fig, ax, sorted_party_names, legend, handles=handles)

    return Chart(fig)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _validate(
    data: pd.DataFrame | None,
    party: str | None,
    seats: str | None,
    values: dict[str, int] | None,
    arc_degrees: float,
    inner_radius: float,
    rows: int | None,
    legend: str | bool | None,
) -> None:
    """Validate inputs before creating any figure."""
    has_df = data is not None
    has_dict = values is not None

    if has_df and has_dict:
        raise ValueError(
            "Cannot use both DataFrame (data/party/seats) and dict (values) inputs. "
            "Provide one or the other."
        )

    if not has_df and not has_dict:
        raise ValueError(
            "Must provide either DataFrame (data, party, seats) or dict (values) input."
        )

    if has_df:
        if data.empty:
            raise ValueError("DataFrame is empty. Cannot create chart.")
        available = list(data.columns)
        available_str = ", ".join(repr(c) for c in available)
        if party is None:
            raise ValueError("Must provide 'party' column name with DataFrame input.")
        if seats is None:
            raise ValueError("Must provide 'seats' column name with DataFrame input.")
        if party not in data.columns:
            raise ValueError(f"Column '{party}' not found in DataFrame. Available: {available_str}")
        if seats not in data.columns:
            raise ValueError(f"Column '{seats}' not found in DataFrame. Available: {available_str}")

    if has_dict:
        if not values:
            raise ValueError("values dict is empty. Cannot create chart.")
        if any(v < 0 for v in values.values()):
            raise ValueError("All values must be >= 0.")

    if not (0 < arc_degrees <= 360):
        raise ValueError(
            f"arc_degrees must be between 0 (exclusive) and 360 (inclusive), got {arc_degrees}."
        )

    if not (0.0 <= inner_radius < 1.0):
        raise ValueError(
            f"inner_radius must be between 0.0 (inclusive) and 1.0 (exclusive), got {inner_radius}."
        )

    if rows is not None and rows < 2:
        raise ValueError(f"rows must be >= 2, got {rows}.")

    if legend is not None and legend is not False and legend not in ("top", "bottom", "right"):
        raise ValueError(
            f"Invalid legend '{legend}'. Must be 'top', 'bottom', 'right', False, or None."
        )


# ---------------------------------------------------------------------------
# Data preparation
# ---------------------------------------------------------------------------


def _prepare_data(
    data: pd.DataFrame | None,
    party: str | None,
    seats: str | None,
    values: dict[str, int] | None,
) -> dict[str, int]:
    """Convert inputs to a {party: seats} dict."""
    if values is not None:
        return dict(values)

    assert data is not None and party is not None and seats is not None
    grouped = data.groupby(party, sort=False)[seats].sum()
    return {str(k): int(v) for k, v in grouped.items()}


# ---------------------------------------------------------------------------
# Seat layout algorithm
# ---------------------------------------------------------------------------


def _auto_rows(total_seats: int) -> int:
    """Estimate number of arc rows from total seats."""
    return max(3, min(12, math.ceil(math.sqrt(total_seats / math.pi))))


def _largest_remainder(counts: dict[int, float], total: int) -> dict[int, int]:
    """Distribute total across keys proportionally using largest remainder method."""
    grand_total = sum(counts.values())
    if grand_total == 0:
        n = len(counts)
        base = total // n
        remainder = total % n
        return {k: base + (1 if i < remainder else 0) for i, k in enumerate(counts)}

    proportions = {k: (v / grand_total) * total for k, v in counts.items()}
    floored = {k: math.floor(p) for k, p in proportions.items()}
    remainders = {k: proportions[k] - floored[k] for k in proportions}

    allocated = sum(floored.values())
    deficit = total - allocated

    sorted_by_remainder = sorted(remainders, key=lambda k: remainders[k], reverse=True)
    for i in range(deficit):
        floored[sorted_by_remainder[i]] += 1

    return floored


def _compute_seat_positions(
    total_seats: int,
    num_rows: int,
    arc_radians: float,
    inner_radius: float,
) -> tuple[list[tuple[float, float]], dict[int, int]]:
    """Compute (x, y) positions for all seats in the hemicycle.

    Returns a tuple of:
    - positions: ordered inner-row left-to-right, then outer rows
    - seats_per_row: dict mapping row index to seat count
    """
    # Compute radius for each row
    radii = []
    for i in range(num_rows):
        if num_rows == 1:
            r = (1.0 + inner_radius) / 2
        else:
            r = inner_radius + (1.0 - inner_radius) * i / (num_rows - 1)
        radii.append(r)

    # Arc lengths per row (proportional to radius)
    arc_lengths = {i: radii[i] * arc_radians for i in range(num_rows)}

    # Distribute seats across rows proportionally to arc lengths
    seats_per_row = _largest_remainder(arc_lengths, total_seats)

    # Compute angular positions for each seat in each row
    # Arc centered on top: from (pi - arc) / 2 to (pi + arc) / 2
    arc_start = (math.pi - arc_radians) / 2
    arc_end = (math.pi + arc_radians) / 2

    positions: list[tuple[float, float]] = []
    for i in range(num_rows):
        n = seats_per_row[i]
        if n == 0:
            continue
        r = radii[i]
        if n == 1:
            theta = (arc_start + arc_end) / 2
            positions.append((r * math.cos(theta), r * math.sin(theta)))
        else:
            for j in range(n):
                theta = arc_start + j * (arc_end - arc_start) / (n - 1)
                x = r * math.cos(theta)
                y = r * math.sin(theta)
                positions.append((x, y))

    return positions, seats_per_row


def _assign_parties_wedge(
    party_seats: dict[str, int],
    seats_per_row: dict[int, int],
) -> tuple[list[str], list[str]]:
    """Assign parties to seats using contiguous wedge fill.

    Each party occupies a contiguous angular wedge across all rows. Within each
    row, seats are allocated proportionally via largest-remainder, and parties
    are placed left-to-right in descending seat-count order.

    Returns:
        A tuple of (seat_parties, sorted_party_names) where seat_parties is a
        flat list of party names matching position order (inner-row left-to-right)
        and sorted_party_names is the parties ordered by descending seat count.
    """
    # Sort parties by seat count descending (largest = leftmost wedge)
    sorted_parties = sorted(party_seats, key=lambda p: party_seats[p], reverse=True)
    total_seats = sum(party_seats.values())

    # Track remaining seats per party to avoid rounding drift
    remaining = {p: party_seats[p] for p in sorted_parties}

    result: list[str] = []
    for row_idx in sorted(seats_per_row):
        row_total = seats_per_row[row_idx]
        if row_total == 0:
            continue

        # Proportional allocation using remaining counts
        row_alloc = _largest_remainder(remaining, row_total)

        # Place party blocks left-to-right in size order
        for p in sorted_parties:
            result.extend([p] * row_alloc[p])
            remaining[p] -= row_alloc[p]

    # Truncate to total seats (shouldn't differ, but be safe)
    return result[:total_seats], sorted_parties


def _dot_radius(num_rows: int, inner_radius: float) -> float:
    """Compute dot radius to avoid overlap between rows."""
    if num_rows <= 1:
        return 0.15
    row_gap = (1.0 - inner_radius) / (num_rows - 1)
    return 0.4 * row_gap


# ---------------------------------------------------------------------------
# Majority line
# ---------------------------------------------------------------------------


def _draw_majority_line(
    ax: plt.Axes,
    seat_positions: list[tuple[float, float]],
    threshold: int,
    arc_radians: float,
    inner_radius: float,
    dot_radius: float,
) -> None:
    """Draw a dashed arc at the angular position where the majority threshold falls."""
    if threshold <= 0 or threshold > len(seat_positions):
        return

    # Sort seats by angle (left-to-right) and find where cumulative count
    # reaches the threshold
    angles = sorted(math.atan2(y, x) for x, y in seat_positions)
    theta = angles[threshold - 1]

    # Draw arc line from inner_radius to slightly beyond outer radius
    r_inner = max(inner_radius - dot_radius * 2, 0.0)
    r_outer = 1.0 + dot_radius * 2

    xs = [r_inner * math.cos(theta), r_outer * math.cos(theta)]
    ys = [r_inner * math.sin(theta), r_outer * math.sin(theta)]

    ax.plot(
        xs,
        ys,
        color="#999999",
        linewidth=1.0,
        linestyle="--",
        zorder=5,
    )

    # Label
    label_r = r_outer + dot_radius * 1.0
    ax.text(
        label_r * math.cos(theta),
        label_r * math.sin(theta),
        f"Majority: {threshold}",
        fontsize=TYPOGRAPHY.source_size,
        color="#999999",
        ha="center",
        va="top",
    )
