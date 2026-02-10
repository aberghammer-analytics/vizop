"""Number auto-detection and formatting for axis ticks and labels."""

import re

import numpy as np
import pandas as pd

# Keywords used to sniff column names for format hints
_PERCENT_KEYWORDS = {"pct", "percent", "percentage", "rate", "share", "ratio"}
_DOLLAR_KEYWORDS = {"price", "cost", "revenue", "salary", "income", "spend", "budget", "dollar"}


def auto_detect_format(column_name: str, values: pd.Series) -> str:
    """Detect the best number format for a column based on name and values.

    Returns one of: "percent", "dollar", "comma", "plain".
    """
    name_lower = column_name.lower().replace("_", " ")
    tokens = set(re.split(r"[\s_\-]+", name_lower))

    # Check column name keywords
    if tokens & _PERCENT_KEYWORDS:
        return "percent"
    if tokens & _DOLLAR_KEYWORDS:
        return "dollar"

    # Check value ranges
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    if numeric.empty:
        return "plain"

    # Values between 0 and 1 that aren't counts → likely percentages
    if (numeric >= 0).all() and (numeric <= 1).all() and numeric.nunique() > 2:
        return "percent"

    # Large numbers benefit from comma formatting
    if numeric.abs().max() >= 1000:
        return "comma"

    return "plain"


def format_value(value: float, fmt: str = "plain", decimals: int | None = None) -> str:
    """Format a single numeric value according to the specified format.

    Args:
        value: The number to format.
        fmt: One of "percent", "dollar", "comma", "plain".
        decimals: Override decimal places. If None, auto-selects.
    """
    if np.isnan(value):
        return ""

    if decimals is None:
        decimals = _auto_decimals(value, fmt)

    if fmt == "percent":
        # If value is 0-1 range, multiply by 100
        display_val = value * 100 if abs(value) <= 1 else value
        return f"{display_val:,.{decimals}f}%"

    if fmt == "dollar":
        if abs(value) >= 1_000_000_000:
            return f"${value / 1_000_000_000:,.{decimals}f}B"
        if abs(value) >= 1_000_000:
            return f"${value / 1_000_000:,.{decimals}f}M"
        if abs(value) >= 1_000:
            return f"${value / 1_000:,.{decimals}f}K"
        return f"${value:,.{decimals}f}"

    if fmt == "comma":
        return f"{value:,.{decimals}f}"

    return f"{value:.{decimals}f}"


def format_tick(value: float, fmt: str = "plain") -> str:
    """Format a tick label — same as format_value but with simpler defaults."""
    return format_value(value, fmt)


def _auto_decimals(value: float, fmt: str) -> int:
    """Choose decimal places based on format and magnitude."""
    if fmt == "percent":
        display_val = value * 100 if abs(value) <= 1 else value
        return 0 if abs(display_val) >= 1 else 1

    if fmt == "dollar":
        if abs(value) >= 1_000:
            return 1
        return 2

    if fmt == "comma":
        return 0

    # Plain: show decimals only if needed
    if value == int(value):
        return 0
    return 1
