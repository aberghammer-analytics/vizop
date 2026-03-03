"""Generate all documentation images for vizop README.

Usage:
    uv run python examples/gallery.py
"""

from pathlib import Path

import numpy as np
import pandas as pd

import vizop

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "docs" / "images"
DPI = 200


def save(chart: vizop.Chart, name: str) -> None:
    """Save a chart to the output directory and close it."""
    chart.save(OUTPUT_DIR / f"{name}.png", dpi=DPI)
    chart.close()
    print(f"  ✓ {name}.png")


# ---------------------------------------------------------------------------
# Quick Start
# ---------------------------------------------------------------------------


def make_quickstart() -> None:
    df = pd.DataFrame({
        "month": ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
        "visitors": [1200, 1350, 1800, 2400, 2800, 3200,
                     3500, 3300, 2900, 2100, 1600, 1400],
    })
    chart = vizop.line(
        df, x="month", y="visitors",
        title="Monthly Website Visitors",
        subtitle="Pageviews peaked in July before seasonal decline",
        source="Internal analytics",
    )
    save(chart, "quickstart")


# ---------------------------------------------------------------------------
# Line Charts
# ---------------------------------------------------------------------------


def make_line_basic() -> None:
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    df = pd.DataFrame({
        "month": months,
        "temperature": [32, 35, 45, 55, 65, 75, 82, 80, 70, 58, 45, 35],
    })
    chart = vizop.line(
        df, x="month", y="temperature",
        title="Average Monthly Temperature",
        subtitle="Temperatures in degrees Fahrenheit, New York City",
        source="National Weather Service",
    )
    save(chart, "line_basic")


def make_line_multi() -> None:
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    df = pd.DataFrame({
        "month": months * 3,
        "ridership": [
            # Subway
            145, 148, 155, 162, 168, 170, 165, 160, 167, 172, 158, 150,
            # Bus
            85, 88, 92, 95, 98, 100, 96, 93, 97, 99, 90, 87,
            # Ferry
            12, 14, 18, 25, 35, 42, 45, 43, 38, 28, 16, 13,
        ],
        "mode": ["Subway"] * 12 + ["Bus"] * 12 + ["Ferry"] * 12,
    })
    chart = vizop.line(
        df, x="month", y="ridership", group="mode",
        highlight="Subway",
        title="NYC Transit Ridership by Mode",
        subtitle="Daily riders in thousands — subway dominates year-round",
        source="MTA Open Data",
    )
    save(chart, "line_multi")


# ---------------------------------------------------------------------------
# Bar Charts
# ---------------------------------------------------------------------------


def make_bar_basic() -> None:
    df = pd.DataFrame({
        "language": ["Python", "JavaScript", "Java", "C++", "TypeScript",
                     "Go", "Rust", "Swift"],
        "satisfaction": [73, 61, 42, 48, 78, 80, 87, 65],
    })
    chart = vizop.bar(
        df, x="language", y="satisfaction",
        title="Developer Satisfaction by Language",
        subtitle="Percent of developers who would use the language again",
        source="2025 Developer Survey",
    )
    save(chart, "bar_basic")


def make_bar_grouped() -> None:
    df = pd.DataFrame({
        "region": ["Northeast", "Southeast", "Midwest", "West"] * 2,
        "revenue": [420, 380, 310, 490, 450, 410, 340, 520],
        "year": ["2024"] * 4 + ["2025"] * 4,
    })
    chart = vizop.bar(
        df, x="region", y="revenue", group="year",
        orientation="vertical", mode="grouped",
        title="Regional Revenue Growth",
        subtitle="Revenue in millions USD — all regions trending upward",
        source="Annual Report 2025",
    )
    save(chart, "bar_grouped")


# ---------------------------------------------------------------------------
# Scatter Plot
# ---------------------------------------------------------------------------


def make_scatter_basic() -> None:
    rng = np.random.default_rng(42)
    n = 50
    study_hours = rng.uniform(1, 10, n)
    scores = 40 + 5 * study_hours + rng.normal(0, 5, n)
    scores = np.clip(scores, 0, 100)
    df = pd.DataFrame({"study_hours": study_hours, "exam_score": scores})
    chart = vizop.scatter(
        df, x="study_hours", y="exam_score",
        trend="linear",
        title="Study Time vs. Exam Performance",
        subtitle="Each dot represents one student",
        source="University registrar data",
    )
    save(chart, "scatter_basic")


def make_scatter_groups() -> None:
    rng = np.random.default_rng(7)
    dfs = []
    for dept, (base_exp, base_sal) in [
        ("Engineering", (3, 95)),
        ("Marketing", (4, 72)),
        ("Sales", (3, 68)),
    ]:
        n = 20
        exp = rng.uniform(1, 15, n) + base_exp
        sal = base_sal + 3 * exp + rng.normal(0, 8, n)
        dfs.append(pd.DataFrame({
            "experience": exp, "salary": sal, "department": dept,
        }))
    df = pd.concat(dfs, ignore_index=True)
    chart = vizop.scatter(
        df, x="experience", y="salary", group="department",
        highlight="Engineering",
        title="Salary vs. Experience by Department",
        subtitle="Engineering salaries grow fastest with tenure",
        source="HR analytics, 2025",
    )
    save(chart, "scatter_groups")


# ---------------------------------------------------------------------------
# Slope Chart
# ---------------------------------------------------------------------------


def make_slope_basic() -> None:
    df = pd.DataFrame({
        "country": ["Norway", "Germany", "USA", "China", "Brazil", "India"],
        "2015": [72, 65, 60, 38, 45, 28],
        "2025": [88, 78, 68, 62, 52, 48],
    })
    chart = vizop.slope(
        df, label="country", left="2015", right="2025",
        highlight=["China", "India"],
        show_change=True,
        title="Renewable Energy Adoption",
        subtitle="Clean energy index score, 2015 vs. 2025",
        source="Global Energy Monitor",
    )
    save(chart, "slope_basic")


# ---------------------------------------------------------------------------
# Waffle Chart
# ---------------------------------------------------------------------------


def make_waffle_basic() -> None:
    chart = vizop.waffle(
        values={"Employed": 62, "Unemployed": 5, "Not in labor force": 33},
        title="U.S. Labor Force Status",
        subtitle="Share of civilian population aged 16+",
        source="Bureau of Labor Statistics, Jan 2025",
    )
    save(chart, "waffle_basic")


# ---------------------------------------------------------------------------
# Raincloud Plot
# ---------------------------------------------------------------------------


def make_raincloud_basic() -> None:
    rng = np.random.default_rng(12)
    dfs = []
    for treatment, (mu, sigma) in [
        ("Control", (50, 12)),
        ("Drug A", (62, 10)),
        ("Drug B", (58, 15)),
    ]:
        vals = rng.normal(mu, sigma, 40)
        dfs.append(pd.DataFrame({"score": vals, "treatment": treatment}))
    df = pd.concat(dfs, ignore_index=True)
    chart = vizop.raincloud(
        df, value="score", group="treatment",
        title="Treatment Response Distribution",
        subtitle="Drug A shows higher median response with less variance",
        source="Clinical trial NCT-2025-0042",
    )
    save(chart, "raincloud_basic")


# ---------------------------------------------------------------------------
# Parliament Chart
# ---------------------------------------------------------------------------


def make_parliament_basic() -> None:
    chart = vizop.parliament(
        values={
            "Democrats": 213,
            "Republicans": 222,
        },
        color_map={"Democrats": "#3571C1", "Republicans": "#D94444"},
        title="U.S. House of Representatives",
        subtitle="119th Congress — Republicans hold a slim majority",
        source="clerk.house.gov",
    )
    save(chart, "parliament_basic")


# ---------------------------------------------------------------------------
# Bump Chart
# ---------------------------------------------------------------------------


def make_bump_basic() -> None:
    teams = ["Arsenal", "Man City", "Liverpool", "Chelsea", "Tottenham"]
    weeks = list(range(1, 9))
    rows = []
    # Points trajectories — every team has a unique value at every week (no ties)
    points = {
        "Arsenal":   [5, 7, 11, 14, 20, 23, 26, 29],
        "Man City":  [4, 8, 10, 16, 19, 25, 28, 31],
        "Liverpool": [3, 5,  8, 11, 14, 17, 20, 23],
        "Chelsea":   [2, 4,  6,  9, 11, 12, 16, 19],
        "Tottenham": [1, 3,  5,  7,  9, 13, 15, 17],
    }
    for team in teams:
        for i, week in enumerate(weeks):
            rows.append({"week": week, "points": points[team][i], "team": team})
    df = pd.DataFrame(rows)
    chart = vizop.bump(
        df, x="week", y="points", group="team",
        highlight=["Arsenal", "Man City"],
        title="Premier League Title Race",
        subtitle="Cumulative points through matchweek 8",
        source="premierleague.com",
    )
    save(chart, "bump_basic")


# ---------------------------------------------------------------------------
# Configuration Before/After
# ---------------------------------------------------------------------------


def make_config_before() -> None:
    df = pd.DataFrame({
        "quarter": ["Q1", "Q2", "Q3", "Q4"],
        "revenue": [42, 48, 51, 55],
    })
    chart = vizop.line(
        df, x="quarter", y="revenue",
        title="Quarterly Revenue",
        subtitle="Revenue in millions USD",
    )
    save(chart, "config_before")


def make_config_after() -> None:
    vizop.configure(
        accent_color="#E15759",
        background="light_gray",
        source_label="Finance Dept.",
    )
    df = pd.DataFrame({
        "quarter": ["Q1", "Q2", "Q3", "Q4"],
        "revenue": [42, 48, 51, 55],
    })
    chart = vizop.line(
        df, x="quarter", y="revenue",
        title="Quarterly Revenue",
        subtitle="Revenue in millions USD",
    )
    save(chart, "config_after")
    # Reset to defaults so other charts aren't affected
    vizop.configure(
        accent_color="#4E79A7",
        background="white",
        source_label=None,
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Generating images to {OUTPUT_DIR}/\n")

    generators = [
        ("Quick Start", make_quickstart),
        ("Line — basic", make_line_basic),
        ("Line — multi-series", make_line_multi),
        ("Bar — basic", make_bar_basic),
        ("Bar — grouped", make_bar_grouped),
        ("Scatter — basic", make_scatter_basic),
        ("Scatter — groups", make_scatter_groups),
        ("Slope — basic", make_slope_basic),
        ("Waffle — basic", make_waffle_basic),
        ("Raincloud — basic", make_raincloud_basic),
        ("Parliament — basic", make_parliament_basic),
        ("Bump — basic", make_bump_basic),
        ("Config — before", make_config_before),
        ("Config — after", make_config_after),
    ]

    for label, func in generators:
        print(f"[{label}]")
        func()

    total = len(list(OUTPUT_DIR.glob("*.png")))
    print(f"\nDone — {total} images generated.")


if __name__ == "__main__":
    main()
