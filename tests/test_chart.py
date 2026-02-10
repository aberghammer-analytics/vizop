"""Tests for vizop.core.chart."""

import matplotlib.pyplot as plt

from vizop.core.chart import Chart


def test_chart_wraps_figure():
    fig = plt.figure()
    chart = Chart(fig)
    assert chart.fig is fig
    plt.close(fig)


def test_to_base64_returns_nonempty_string():
    fig, ax = plt.subplots()
    ax.plot([1, 2, 3], [1, 2, 3])
    chart = Chart(fig)
    result = chart.to_base64()
    assert isinstance(result, str)
    assert len(result) > 0
    plt.close(fig)


def test_to_base64_jpeg_format():
    fig, ax = plt.subplots()
    ax.plot([1, 2], [1, 2])
    chart = Chart(fig)
    result = chart.to_base64(format="jpeg")
    assert isinstance(result, str)
    assert len(result) > 0
    plt.close(fig)


def test_save_writes_file(tmp_path):
    fig, ax = plt.subplots()
    ax.plot([1, 2, 3], [1, 2, 3])
    chart = Chart(fig)
    path = tmp_path / "test_chart.png"
    chart.save(path)
    assert path.exists()
    assert path.stat().st_size > 0
    plt.close(fig)


def test_save_with_custom_dpi(tmp_path):
    fig, ax = plt.subplots()
    ax.plot([1, 2], [1, 2])
    chart = Chart(fig)
    path = tmp_path / "test_chart_300dpi.png"
    chart.save(path, dpi=300)
    assert path.exists()
    plt.close(fig)
