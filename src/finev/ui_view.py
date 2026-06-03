"""Pure presentation helpers for the wealth forecast UI.

Formatting and chart/table shaping with no NiceGUI dependency, so they can be
unit-tested without rendering a page.
"""

from __future__ import annotations

from typing import Any

import pandas as pd


def format_currency(value: float, currency: str) -> str:
    """Format a numeric value with a currency suffix.

    Args:
        value: Amount to format.
        currency: Currency code or symbol.

    Returns:
        Formatted currency string.
    """
    return f"{value:,.0f} {currency}".strip()


def build_chart_options() -> dict[str, Any]:
    """Build default chart options for the forecast plot.

    Returns:
        Base chart configuration dictionary.
    """
    return {
        "tooltip": {"trigger": "axis"},
        "legend": {"top": 0},
        "xAxis": {"type": "category", "data": []},
        "yAxis": {"type": "value"},
        "series": [],
    }


def yearly_display_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Return a yearly-sampled DataFrame for presentation.

    Args:
        df: Monthly forecast frame.

    Returns:
        One row per whole year (every 12th month), with a ``year_index`` column;
        the input frame is returned unchanged when empty.
    """
    if df.empty:
        return df
    yearly = df[df["month_index"] % 12 == 0].copy()
    yearly["year_index"] = (yearly["month_index"] // 12).astype(int)
    return yearly.reset_index(drop=True)
