"""Typography, layout, and size constants for vizop theming.

These are internal constants — not user-facing. Users control appearance
via VizopConfig; this module translates config into matplotlib properties.
"""

from typing import TYPE_CHECKING

from matplotlib.ticker import FuncFormatter, MaxNLocator
from pydantic import BaseModel

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

from vizop.core.config import VizopConfig, get_config
from vizop.core.fonts import get_font_family, register_fonts
from vizop.core.formatting import format_value


class Typography(BaseModel):
    """Font sizes and colors for chart text elements."""

    title_size: float = 18.0
    title_color: str = "#1a1a1a"
    title_weight: str = "bold"
    subtitle_size: float = 12.0
    subtitle_color: str = "#666666"
    subtitle_weight: str = "regular"
    tick_size: float = 10.0
    tick_color: str = "#666666"
    label_size: float = 10.0
    label_color: str = "#333333"
    source_size: float = 8.0
    source_color: str = "#999999"
    note_size: float = 9.0
    note_color: str = "#666666"


class Layout(BaseModel):
    """Spacing and visual element constants."""

    gridline_color: str = "#e0e0e0"
    gridline_alpha: float = 0.7
    gridline_linewidth: float = 0.5
    spine_color: str = "#cccccc"
    spine_linewidth: float = 0.8
    line_width: float = 2.5
    bar_width: float = 0.7
    point_size: float = 40.0
    title_pad: float = 16.0
    subtitle_pad: float = 8.0
    source_pad: float = 24.0
    figure_margin: float = 0.025


class SizeSpec(BaseModel):
    """Figure dimensions for each size preset."""

    width: float
    height: float


SIZES: dict[str, SizeSpec] = {
    "standard": SizeSpec(width=8.0, height=5.5),
    "wide": SizeSpec(width=11.0, height=5.0),
    "tall": SizeSpec(width=7.0, height=8.0),
    "square": SizeSpec(width=7.0, height=7.0),
}

BACKGROUND_COLORS: dict[str, str] = {
    "white": "#ffffff",
    "light_gray": "#f5f5f5",
}

TYPOGRAPHY = Typography()
LAYOUT = Layout()


def _comma_tick_formatter(value: float, pos: int) -> str:
    """Format tick labels with commas for values >= 1000."""
    fmt = "comma" if abs(value) >= 1000 else "plain"
    return format_value(value, fmt)


def apply_theme(
    fig: "Figure",
    ax: "Axes",
    *,
    config: VizopConfig | None = None,
    title: str | None = None,
    subtitle: str | None = None,
    source: str | None = None,
    note: str | None = None,
    gridlines: bool = False,
) -> None:
    """Apply vizop's opinionated theme to a matplotlib figure and axes.

    This is the single entry point for all visual styling. Every chart
    function calls this after rendering data elements.
    """
    if config is None:
        config = get_config()

    register_fonts()
    font_family = get_font_family(config)

    # --- Figure size and background ---
    # DPI is NOT set here — the figure stays at matplotlib's default (100)
    # so Jupyter inline display renders at standard size. High-res DPI is
    # applied only at save time via Chart.save()/to_base64().
    size = SIZES[config.size]
    fig.set_size_inches(size.width, size.height)
    bg_color = BACKGROUND_COLORS[config.background]
    fig.set_facecolor(bg_color)
    ax.set_facecolor(bg_color)

    # --- Spines: only left and bottom ---
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(LAYOUT.spine_color)
    ax.spines["left"].set_linewidth(LAYOUT.spine_linewidth)
    ax.spines["bottom"].set_color(LAYOUT.spine_color)
    ax.spines["bottom"].set_linewidth(LAYOUT.spine_linewidth)

    # --- Gridlines ---
    if gridlines:
        ax.yaxis.grid(
            True,
            color=LAYOUT.gridline_color,
            alpha=LAYOUT.gridline_alpha,
            linewidth=LAYOUT.gridline_linewidth,
        )
        ax.xaxis.grid(False)
    else:
        ax.yaxis.grid(False)
        ax.xaxis.grid(False)

    ax.set_axisbelow(True)

    # --- Y-axis: fewer ticks ---
    ax.yaxis.set_major_locator(MaxNLocator(nbins=5))

    # --- Numeric tick formatting (commas for values >= 1000) ---
    tick_formatter = FuncFormatter(_comma_tick_formatter)
    ax.xaxis.set_major_formatter(tick_formatter)
    ax.yaxis.set_major_formatter(tick_formatter)

    # --- Tick styling ---
    ax.tick_params(
        axis="both",
        labelsize=TYPOGRAPHY.tick_size,
        labelcolor=TYPOGRAPHY.tick_color,
        length=0,
    )
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontfamily(font_family)

    # --- Layout first, then position text elements in reserved space ---
    fig.tight_layout()

    margin = LAYOUT.figure_margin
    has_title = bool(title)
    has_subtitle = bool(subtitle)

    # --- Reserve top space for title/subtitle ---
    if has_title or has_subtitle:
        fig_height_pts = fig.get_size_inches()[1] * 72
        top_pad = 4.0 / fig_height_pts
        element_gap = 6.0 / fig_height_pts

        space_needed = top_pad
        if has_title:
            space_needed += TYPOGRAPHY.title_size / fig_height_pts
        if has_subtitle:
            space_needed += TYPOGRAPHY.subtitle_size / fig_height_pts
        if has_title and has_subtitle:
            space_needed += element_gap
        space_needed += element_gap  # gap between header and axes

        fig.subplots_adjust(top=1.0 - space_needed)

        y_cursor = 1.0 - top_pad

        if has_title:
            title_text = fig.text(
                margin,
                y_cursor,
                title,
                fontsize=TYPOGRAPHY.title_size,
                fontweight=TYPOGRAPHY.title_weight,
                color=TYPOGRAPHY.title_color,
                fontfamily=font_family,
                ha="left",
                va="top",
                transform=fig.transFigure,
            )
            title_text._vizop_type = "title"
            y_cursor -= TYPOGRAPHY.title_size / fig_height_pts + element_gap

        if has_subtitle:
            subtitle_text = fig.text(
                margin,
                y_cursor,
                subtitle,
                fontsize=TYPOGRAPHY.subtitle_size,
                fontweight=TYPOGRAPHY.subtitle_weight,
                color=TYPOGRAPHY.subtitle_color,
                fontfamily=font_family,
                ha="left",
                va="top",
                transform=fig.transFigure,
            )
            subtitle_text._vizop_type = "subtitle"

    # --- Source and note (left-aligned to figure margin) ---
    source_text = source or config.source_label
    has_source = bool(source_text)
    has_note = bool(note)

    if has_source or has_note:
        bottom = 0.15 if has_source and has_note else 0.12
        fig.subplots_adjust(bottom=bottom)

        if has_source:
            fig.text(
                margin,
                0.02,
                f"Source: {source_text}",
                fontsize=TYPOGRAPHY.source_size,
                color=TYPOGRAPHY.source_color,
                fontfamily=font_family,
                ha="left",
                va="bottom",
                transform=fig.transFigure,
            )

        if has_note:
            y_offset = 0.05 if has_source else 0.02
            fig.text(
                margin,
                y_offset,
                f"Note: {note}",
                fontsize=TYPOGRAPHY.note_size,
                color=TYPOGRAPHY.note_color,
                fontfamily=font_family,
                ha="left",
                va="bottom",
                transform=fig.transFigure,
            )


def _adjust_top_spacing_for_legend(fig: "Figure", ax: "Axes") -> None:
    """Push axes down to make room for a top-positioned legend.

    Title and subtitle are figure-level text (tagged with _vizop_type),
    so we just need to push the axes top down — the title/subtitle stay put
    since they're in absolute figure coordinates.
    """
    fig_height_pts = fig.get_size_inches()[1] * 72
    legend_space = (TYPOGRAPHY.label_size + 12.0) / fig_height_pts

    current_top = fig.subplotpars.top
    fig.subplots_adjust(top=current_top - legend_space)


def draw_legend(
    fig: "Figure",
    ax: "Axes",
    labels: list[str],
    position: str | bool | None,
    handles: list | None = None,
) -> None:
    """Draw a left-aligned legend at the specified position.

    This is the shared legend function for all chart types. Handles
    subtitle/title spacing adjustments when position is "top".

    Args:
        fig: The matplotlib Figure.
        ax: The matplotlib Axes containing labeled artists.
        labels: Series/group names (used for ncol sizing).
        position: "top", "bottom", "right", False, or None.
        handles: Explicit legend handles. When None, uses labeled artists on *ax*.
    """
    if position is False or position is None:
        return

    ncol = len(labels)
    handle_kwargs: dict = {}
    if handles is not None:
        handle_kwargs["handles"] = handles

    if position == "top":
        _adjust_top_spacing_for_legend(fig, ax)
        ax_pos = ax.get_position()
        margin = LAYOUT.figure_margin
        legend_x = (margin - ax_pos.x0) / ax_pos.width
        ax.legend(
            loc="lower left",
            bbox_to_anchor=(legend_x, 1.02),
            ncol=ncol,
            frameon=False,
            fontsize=TYPOGRAPHY.label_size,
            borderpad=0.0,
            borderaxespad=0.2,
            handlelength=2.0,
            columnspacing=1.0,
            **handle_kwargs,
        )
    elif position == "bottom":
        ax.legend(
            loc="lower left",
            bbox_to_anchor=(0.0, -0.12),
            ncol=ncol,
            frameon=False,
            fontsize=TYPOGRAPHY.label_size,
            columnspacing=1.0,
            **handle_kwargs,
        )
    elif position == "right":
        ax.legend(
            loc="center left",
            bbox_to_anchor=(1.02, 0.5),
            ncol=1,
            frameon=False,
            fontsize=TYPOGRAPHY.label_size,
            **handle_kwargs,
        )
        fig.subplots_adjust(right=0.82)
