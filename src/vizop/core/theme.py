"""Typography, layout, and size constants for vizop theming.

These are internal constants — not user-facing. Users control appearance
via VizopConfig; this module translates config into matplotlib properties.
"""

from typing import Literal

from matplotlib.axes import Axes
from matplotlib.figure import Figure
from pydantic import BaseModel

from vizop.core.config import VizopConfig, get_config
from vizop.core.fonts import get_font_family, register_fonts


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


class SizeSpec(BaseModel):
    """Figure dimensions for each size preset."""

    width: float
    height: float


SIZES: dict[str, SizeSpec] = {
    "standard": SizeSpec(width=8.0, height=5.5),
    "wide": SizeSpec(width=11.0, height=5.0),
    "tall": SizeSpec(width=7.0, height=8.0),
}

BACKGROUND_COLORS: dict[str, str] = {
    "white": "#ffffff",
    "light_gray": "#f5f5f5",
}

TYPOGRAPHY = Typography()
LAYOUT = Layout()


def apply_theme(
    fig: "Figure",
    ax: "Axes",
    *,
    config: VizopConfig | None = None,
    title: str | None = None,
    subtitle: str | None = None,
    source: str | None = None,
    note: str | None = None,
    gridlines: Literal["horizontal", "both", "none"] = "horizontal",
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
    if gridlines == "horizontal":
        ax.yaxis.grid(
            True,
            color=LAYOUT.gridline_color,
            alpha=LAYOUT.gridline_alpha,
            linewidth=LAYOUT.gridline_linewidth,
        )
        ax.xaxis.grid(False)
    elif gridlines == "both":
        ax.yaxis.grid(
            True,
            color=LAYOUT.gridline_color,
            alpha=LAYOUT.gridline_alpha,
            linewidth=LAYOUT.gridline_linewidth,
        )
        ax.xaxis.grid(
            True,
            color=LAYOUT.gridline_color,
            alpha=LAYOUT.gridline_alpha,
            linewidth=LAYOUT.gridline_linewidth,
        )
    else:
        ax.yaxis.grid(False)
        ax.xaxis.grid(False)

    ax.set_axisbelow(True)

    # --- Tick styling ---
    ax.tick_params(
        axis="both",
        labelsize=TYPOGRAPHY.tick_size,
        labelcolor=TYPOGRAPHY.tick_color,
        length=0,
    )
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontfamily(font_family)

    # --- Title (left-aligned) ---
    if title:
        ax.set_title(
            title,
            fontsize=TYPOGRAPHY.title_size,
            fontweight=TYPOGRAPHY.title_weight,
            color=TYPOGRAPHY.title_color,
            fontfamily=font_family,
            loc="left",
            pad=LAYOUT.title_pad,
        )

    # --- Subtitle (left-aligned, below title) ---
    if subtitle:
        # Use fig.text for subtitle positioned just below the title
        ax_pos = ax.get_position()
        fig.text(
            ax_pos.x0,
            ax_pos.y1 + 0.02,
            subtitle,
            fontsize=TYPOGRAPHY.subtitle_size,
            fontweight=TYPOGRAPHY.subtitle_weight,
            color=TYPOGRAPHY.subtitle_color,
            fontfamily=font_family,
            ha="left",
            va="bottom",
            transform=fig.transFigure,
        )

    # --- Source label (below plot) ---
    source_text = source or config.source_label
    if source_text:
        ax_pos = ax.get_position()
        fig.text(
            ax_pos.x0,
            0.02,
            f"Source: {source_text}",
            fontsize=TYPOGRAPHY.source_size,
            color=TYPOGRAPHY.source_color,
            fontfamily=font_family,
            ha="left",
            va="bottom",
            transform=fig.transFigure,
        )

    # --- Note (below source, slightly larger) ---
    if note:
        ax_pos = ax.get_position()
        y_offset = 0.05 if source_text else 0.02
        fig.text(
            ax_pos.x0,
            y_offset,
            f"Note: {note}",
            fontsize=TYPOGRAPHY.note_size,
            color=TYPOGRAPHY.note_color,
            fontfamily=font_family,
            ha="left",
            va="bottom",
            transform=fig.transFigure,
        )

    fig.tight_layout()
