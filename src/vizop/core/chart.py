"""Chart wrapper returned by all vizop chart functions."""

import base64
from io import BytesIO
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.figure import Figure


class Chart:
    """Thin wrapper around a matplotlib Figure.

    Provides show(), save(), and to_base64() for convenient output.
    """

    def __init__(self, fig: Figure) -> None:
        self.fig = fig

    def show(self) -> None:
        """Display the chart interactively."""
        self.fig.show()

    def save(self, path: str | Path, *, dpi: int = 150) -> None:
        """Save the chart to a file."""
        self.fig.savefig(path, dpi=dpi, bbox_inches="tight")

    def to_base64(self, *, format: str = "png") -> str:
        """Return the chart as a base64-encoded string."""
        buf = BytesIO()
        self.fig.savefig(buf, format=format, bbox_inches="tight")
        buf.seek(0)
        return base64.b64encode(buf.read()).decode("utf-8")

    def close(self) -> None:
        """Close the underlying matplotlib figure."""
        plt.close(self.fig)
