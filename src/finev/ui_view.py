"""Pure presentation helpers for the wealth forecast UI.

Formatting and chart/table shaping with no NiceGUI dependency, so they can be
unit-tested without rendering a page.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from datetime import datetime
from importlib import resources
from typing import Any

import pandas as pd

from finev.greet import get_version
from finev.models import Asset, AssetType


def favicon_svg() -> str:
    """Load the application favicon as an inline SVG string.

    NiceGUI renders a raw SVG string (one starting with ``<svg``) as the page
    favicon, so the bundled asset is returned verbatim.

    Returns:
        The contents of ``static/favicon.svg`` shipped with the package.
    """
    return (
        resources.files("finev")
        .joinpath("static/favicon.svg")
        .read_text(encoding="utf-8")
    )


# Matches a ``width``/``height`` attribute inside the opening ``<svg>`` tag only
# (``[^>]*?`` cannot cross the tag's closing ``>``), so inner attributes such as
# ``stroke-width`` are never touched.
_SVG_ROOT_WIDTH_RE = re.compile(r'(<svg\b[^>]*?\s)width="[^"]*"')
_SVG_ROOT_HEIGHT_RE = re.compile(r'(<svg\b[^>]*?\s)height="[^"]*"')


def inline_logo_svg() -> str:
    """Return the app logo SVG sized to fill its container.

    The bundled favicon hard-codes a 128px ``width``/``height``, which is right
    for a browser tab but oversizes the icon when it is embedded inline (e.g. as
    the navbar logo). This replaces those fixed root dimensions with ``100%`` so
    the SVG scales to whatever box the caller sizes it to via CSS classes.

    Returns:
        The favicon SVG with its root ``width``/``height`` set to ``100%``.
    """
    svg = favicon_svg()
    svg = _SVG_ROOT_WIDTH_RE.sub(r'\1width="100%"', svg, count=1)
    svg = _SVG_ROOT_HEIGHT_RE.sub(r'\1height="100%"', svg, count=1)
    return svg


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
        Per-asset balance column names (excluding INHERITANCE and VBLklassik,
        which hold no running balance) followed by ``"total"``.
    """
    return [
        asset.name
        for asset in assets
        if asset.asset_type
        not in (AssetType.INHERITANCE, AssetType.VBL_KLASSIK)
    ] + ["total"]


def forecast_table_columns(
    value_columns: list[str],
    translate: Callable[[str], str] | None = None,
) -> list[dict[str, Any]]:
    """Build NiceGUI table column definitions for the yearly forecast.

    Args:
        value_columns: Per-asset and total balance column names.
        translate: Optional translator mapping a catalog key to its localized
            label (see :func:`finev.i18n.make_translator`). When ``None``, the
            fixed columns keep their English labels. Value columns are per-asset
            names and are never translated.

    Returns:
        Column definition dictionaries (fixed columns followed by value columns).
    """
    labels = {
        "table.year": "Year",
        "table.age": "Age",
        "table.net_cashflow": "Net Cashflow p.m.",
        "table.taxes": "Taxes p.m.",
    }
    if translate is not None:
        labels = {key: translate(key) for key in labels}
    columns: list[dict[str, Any]] = [
        {
            "name": "year_index",
            "label": labels["table.year"],
            "field": "year_index",
            "sortable": True,
        },
        {
            "name": "age",
            "label": labels["table.age"],
            "field": "age",
            "sortable": False,
        },
        {
            "name": "net_cashflow",
            "label": labels["table.net_cashflow"],
            "field": "net_cashflow",
            "sortable": True,
        },
        {
            "name": "taxes",
            "label": labels["table.taxes"],
            "field": "taxes",
            "sortable": True,
        },
    ]
    columns.extend(
        {"name": column, "label": column, "field": column, "sortable": True}
        for column in value_columns
    )
    return columns


def forecast_csv(df: pd.DataFrame) -> str:
    """Serialize the full monthly forecast frame to CSV text.

    Exports the detailed engine output (every month, all computed columns:
    ``month_index``, ``age_years``, ``age_months``, ``net_cashflow``,
    ``taxes``, the per-asset balances, and ``total``) rather than the
    yearly-sampled display frame, so the download holds the full backend detail.

    To keep the file frugal, the EURO-valued columns (the floating-point
    columns: ``net_cashflow``, ``taxes``, the per-asset balances, and
    ``total``) are rounded to whole euros and written as integers; the
    already-integer ``month_index``/``age_*`` columns are untouched.

    Args:
        df: Monthly forecast frame as returned by ``forecast_wealth``.

    Returns:
        CSV text with a header row and one row per month, without the pandas
        index column, EURO values rendered as integers.
    """
    rounded = df.copy()
    euro_columns = rounded.select_dtypes(include="float").columns
    rounded[euro_columns] = rounded[euro_columns].round(0).astype("int64")
    return rounded.to_csv(index=False)


def export_csv_filename(generated_at: datetime | None = None) -> str:
    """Build a timestamped filename for a forecast CSV export.

    The timestamp keeps successive downloads distinct in the browser's download
    folder without relying on its automatic ``(1)``/``(2)`` suffixing.

    Args:
        generated_at: Moment the export was produced; defaults to ``now()``.

    Returns:
        A filename such as ``wealth-forecast-20260606-153000.csv``.
    """
    moment = generated_at or datetime.now()
    return f"wealth-forecast-{moment:%Y%m%d-%H%M%S}.csv"


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
