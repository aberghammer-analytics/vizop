"""vizop — Opinionated data visualization for Python."""

from vizop.charts.bar import bar
from vizop.charts.bump import bump
from vizop.charts.line import line
from vizop.charts.parliament import parliament
from vizop.charts.raincloud import raincloud
from vizop.charts.scatter import scatter
from vizop.charts.slope import slope
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
    "bump",
    "configure",
    "get_config",
    "line",
    "parliament",
    "raincloud",
    "scatter",
    "slope",
    "waffle",
]
