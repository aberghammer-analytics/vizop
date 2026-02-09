"""vizop — Opinionated, publication-quality data visualization."""

from vizop.charts.bar import bar
from vizop.charts.line import line
from vizop.core.config import configure

__all__ = ["line", "bar", "configure"]
