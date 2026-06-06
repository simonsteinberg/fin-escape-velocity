"""Pure presentation helpers for the wealth forecast UI.

Formatting and chart/table shaping with no NiceGUI dependency, so they can be
unit-tested without rendering a page.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import pandas as pd

from finev.greet import get_version
from finev.models import Asset, AssetType


def version_label_text() -> str:
    """Build the version label shown next to the page title.

    Returns:
        The installed package version prefixed with ``v`` (e.g. ``"v0.1.0"``).
    """
    return f"v{get_version()}"


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


def asset_value_columns(assets: Iterable[Asset]) -> list[str]:
    """Return the value columns to plot/tabulate.

    Args:
        assets: Assets in the forecast.

    Returns:
        Per-asset balance column names (excluding INHERITANCE, which holds no
        running balance) followed by ``"total"``.
    """
    return [
        asset.name
        for asset in assets
        if asset.asset_type != AssetType.INHERITANCE
    ] + ["total"]


def forecast_table_columns(value_columns: list[str]) -> list[dict[str, Any]]:
    """Build NiceGUI table column definitions for the yearly forecast.

    Args:
        value_columns: Per-asset and total balance column names.

    Returns:
        Column definition dictionaries (fixed columns followed by value columns).
    """
    columns: list[dict[str, Any]] = [
        {
            "name": "year_index",
            "label": "Year",
            "field": "year_index",
            "sortable": True,
        },
        {"name": "age", "label": "Age", "field": "age", "sortable": False},
        {
            "name": "net_cashflow",
            "label": "Net Cashflow p.m.",
            "field": "net_cashflow",
            "sortable": True,
        },
        {
            "name": "taxes",
            "label": "Taxes p.m.",
            "field": "taxes",
            "sortable": True,
        },
    ]
    columns.extend(
        {"name": column, "label": column, "field": column, "sortable": True}
        for column in value_columns
    )
    return columns


def chart_series(
    frame: pd.DataFrame,
    value_columns: list[str],
) -> list[dict[str, Any]]:
    """Build ECharts line-series definitions for each value column.

    Args:
        frame: Display frame containing the value columns.
        value_columns: Column names to plot.

    Returns:
        One smooth line-series definition per value column.
    """
    return [
        {
            "name": column,
            "type": "line",
            "data": frame[column].tolist(),
            "smooth": True,
            "showSymbol": False,
        }
        for column in value_columns
    ]
