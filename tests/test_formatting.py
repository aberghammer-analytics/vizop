"""Tests for vizop.core.formatting."""

import numpy as np
import pandas as pd

from vizop.core.formatting import auto_detect_format, format_value


class TestAutoDetectFormat:
    def test_percent_keyword_in_name(self):
        values = pd.Series([10, 20, 30])
        assert auto_detect_format("growth_rate", values) == "percent"

    def test_dollar_keyword_in_name(self):
        values = pd.Series([100, 200, 300])
        assert auto_detect_format("total_revenue", values) == "dollar"

    def test_values_between_0_and_1_detected_as_percent(self):
        values = pd.Series([0.12, 0.45, 0.78, 0.33])
        assert auto_detect_format("some_metric", values) == "percent"

    def test_large_values_detected_as_comma(self):
        values = pd.Series([15000, 28000, 42000])
        assert auto_detect_format("population", values) == "comma"

    def test_small_integers_detected_as_plain(self):
        values = pd.Series([1, 5, 10, 15])
        assert auto_detect_format("count", values) == "plain"

    def test_empty_series_returns_plain(self):
        values = pd.Series([], dtype=float)
        assert auto_detect_format("empty", values) == "plain"


class TestFormatValue:
    def test_percent_from_decimal(self):
        result = format_value(0.456, "percent")
        assert result == "46%"

    def test_percent_from_whole_number(self):
        result = format_value(45.6, "percent")
        assert result == "46%"

    def test_dollar_millions(self):
        result = format_value(2_500_000, "dollar")
        assert result == "$2.5M"

    def test_dollar_thousands(self):
        result = format_value(15_000, "dollar")
        assert result == "$15.0K"

    def test_dollar_small(self):
        result = format_value(42.5, "dollar")
        assert result == "$42.50"

    def test_comma_format(self):
        result = format_value(1234567, "comma")
        assert result == "1,234,567"

    def test_plain_integer(self):
        result = format_value(42.0, "plain")
        assert result == "42"

    def test_plain_decimal(self):
        result = format_value(3.7, "plain")
        assert result == "3.7"

    def test_nan_returns_empty(self):
        result = format_value(np.nan, "dollar")
        assert result == ""

    def test_custom_decimals(self):
        result = format_value(0.456, "percent", decimals=1)
        assert result == "45.6%"

    def test_dollar_billions(self):
        result = format_value(3_200_000_000, "dollar")
        assert result == "$3.2B"
