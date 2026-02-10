"""vizop — Opinionated data visualization for Python."""

from vizop.charts.line import line
from vizop.core.chart import Chart
from vizop.core.config import configure, get_config

__version__ = "0.1.0"

__all__ = [
    "Chart",
    "__version__",
    "configure",
    "get_config",
    "line",
]
