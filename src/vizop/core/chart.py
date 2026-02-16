"""Chart wrapper returned by all vizop chart functions."""

import base64
from io import BytesIO
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from vizop.core.config import get_config


class Chart:
    """Thin wrapper around a matplotlib Figure.

    Provides show(), save(), and to_base64() for convenient output.
    """

    DISPLAY_DPI: int = 100

    def __init__(self, fig: Figure) -> None:
        self.fig = fig

    def show(self) -> None:
        """Display the chart interactively."""
        self.fig.show()

    def save(self, path: str | Path, *, dpi: int | None = None) -> None:
        """Save the chart to a file."""
        if dpi is None:
            dpi = get_config().dpi
        self.fig.savefig(path, dpi=dpi, bbox_inches="tight")

    def to_base64(self, *, format: str = "png", dpi: int | None = None) -> str:
        """Return the chart as a base64-encoded string."""
        if dpi is None:
            dpi = get_config().dpi
        buf = BytesIO()
        self.fig.savefig(buf, format=format, dpi=dpi, bbox_inches="tight")
        buf.seek(0)
        return base64.b64encode(buf.read()).decode("utf-8")

    def _repr_png_(self) -> bytes:
        """Render as PNG for Jupyter notebook inline display."""
        buf = BytesIO()
        self.fig.savefig(buf, format="png", dpi=self.DISPLAY_DPI, bbox_inches="tight")
        buf.seek(0)
        return buf.read()

    def close(self) -> None:
        """Close the underlying matplotlib figure."""
        plt.close(self.fig)
