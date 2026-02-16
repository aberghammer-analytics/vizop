"""vizop — Opinionated data visualization for Python."""

from vizop.charts.bar import bar
from vizop.charts.line import line
from vizop.charts.waffle import waffle
from vizop.core.annotations import Annotation
from vizop.core.chart import Chart
from vizop.core.config import configure, get_config

__version__ = "0.1.0"

__all__ = [
    "Annotation",
    "Chart",
    "__version__",
    "bar",
    "configure",
    "get_config",
    "line",
    "waffle",
]
