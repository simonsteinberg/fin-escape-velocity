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


# ── Theme palette ──────────────────────────────────────────────────────────
# Brand teal that matches the logo gradient (light mode navbar).
NAVBAR_LIGHT_BG = "#0f766e"
# A neutral dark gray (not black) for the dark-mode navbar.
NAVBAR_DARK_BG = "#1f2937"
# Dark-mode surfaces: a gray-ish page and a slightly lighter card/surface (so the
# profile/asset cards and the data table read as raised, mid-gray panels rather
# than near-black), overriding Quasar's defaults (#121212 / #1d1d1d).
DARK_PAGE_BG = "#22272e"
DARK_SURFACE_BG = "#313945"
# Dark-mode body text: a soft gray rather than pure white, easier on the eyes.
DARK_TEXT = "#c4cad3"
# Dark-mode scrollbar colors (track matches the page; thumb is a mid gray).
DARK_SCROLLBAR_THUMB = "#4b5563"

#: CSS class applied to the navbar so its background can follow the scheme.
NAVBAR_CLASS = "fev-navbar"


def theme_css() -> str:
    """Build the global CSS that makes the page theme follow the color scheme.

    The rules key off Quasar's ``body--dark`` class (toggled by ``ui.dark_mode``
    for both forced-dark and auto-resolved-dark), so the navbar, page surfaces
    and scrollbars track the active scheme without Python knowing the
    OS preference. It also overrides Quasar's near-black dark defaults with
    neutral grays.

    Returns:
        A CSS string (no surrounding ``<style>`` tag).
    """
    return (
        # Gray-ish dark surfaces instead of Quasar's near-black defaults.
        f":root {{ --q-dark-page: {DARK_PAGE_BG}; --q-dark: {DARK_SURFACE_BG}; }}\n"
        f".body--dark {{ background-color: {DARK_PAGE_BG}; color: {DARK_TEXT}; }}\n"
        # Cards (profile/asset panels) and the data table read as raised, lighter
        # mid-gray surfaces; set explicitly so the table does not stay near-black.
        f".body--dark .q-card, .body--dark .q-table, "
        f".body--dark .q-table__container, .body--dark .q-table thead tr "
        f"{{ background-color: {DARK_SURFACE_BG}; }}\n"
        # Navbar background follows the scheme.
        f".{NAVBAR_CLASS} {{ background-color: {NAVBAR_LIGHT_BG}; }}\n"
        f".body--dark .{NAVBAR_CLASS} {{ background-color: {NAVBAR_DARK_BG}; }}\n"
        # Dark scrollbars (WebKit + Firefox) so they are not left white.
        f".body--dark {{ scrollbar-color: {DARK_SCROLLBAR_THUMB} "
        f"{DARK_PAGE_BG}; }}\n"
        ".body--dark ::-webkit-scrollbar { width: 12px; height: 12px; }\n"
        f".body--dark ::-webkit-scrollbar-track {{ background: {DARK_PAGE_BG}; }}\n"
        ".body--dark ::-webkit-scrollbar-thumb { "
        f"background: {DARK_SCROLLBAR_THUMB}; border-radius: 6px; }}\n"
    )


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


# Logarithmic capital (y) axis behaviour.
#
# The visible axis bottom stays at 1000 € (``LOG_SCALE_Y_AXIS_MIN_EUR``). Series
# values are independently clamped up to a 1 € minimum (``LOG_SCALE_VALUE_FLOOR_EUR``)
# only so the log axis stays well-defined — a log scale cannot represent values
# <= 0. Because the value floor (1 €) is below the axis minimum (1000 €), a
# falling series descends past the 1000 € gridline and slides off the bottom of
# the chart on its own, rather than throwing on a non-positive value.
LOG_SCALE_Y_AXIS_MIN_EUR = 1000
LOG_SCALE_VALUE_FLOOR_EUR = 1


def chart_y_axis(log_scale: bool) -> dict[str, Any]:
    """Build the capital (y) axis config for the forecast plot.

    Args:
        log_scale: When ``True``, use a logarithmic scale whose visible lower
            bound is :data:`LOG_SCALE_Y_AXIS_MIN_EUR` euros (series falling below
            it leave the chart at the bottom); otherwise use a linear scale
            spanning the data.

    Returns:
        The ECharts ``yAxis`` configuration dictionary.
    """
    if log_scale:
        return {"type": "log", "min": LOG_SCALE_Y_AXIS_MIN_EUR}
    return {"type": "value"}


def build_chart_options(log_scale: bool = False) -> dict[str, Any]:
    """Build default chart options for the forecast plot.

    Args:
        log_scale: When ``True``, render the capital (y) axis on a logarithmic
            scale (see :func:`chart_y_axis`); otherwise use a linear scale.

    Returns:
        Base chart configuration dictionary.
    """
    return {
        "tooltip": {"trigger": "axis"},
        "legend": {"top": 0},
        "xAxis": {"type": "category", "data": []},
        "yAxis": chart_y_axis(log_scale),
        "series": [],
    }


def yearly_display_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Return a yearly-sampled DataFrame for presentation.

    Rows are sampled on **birthdays** (``age_months == 0``), not every twelfth
    month from the forecast start, so each row holds the balance at exactly the
    age it is labelled with. Sampling by month offset would shift every row by
    the start month-in-year (a forecast starting at 25y1m would label the 26y1m
    balance as "26"), making the displayed value independent of the start month.
    The forecast's first month is always kept so the view shows today's balance
    even when the forecast does not start on a birthday.

    Args:
        df: Monthly forecast frame.

    Returns:
        One row per birthday plus the start month, with a ``year_index`` column
        counting age-years since the first row; the input frame is returned
        unchanged when empty.
    """
    if df.empty:
        return df
    on_birthday = df["age_months"] == 0
    is_start = df["month_index"] == df["month_index"].min()
    yearly = df[on_birthday | is_start].copy()
    start_age_years = int(yearly["age_years"].iloc[0])
    yearly["year_index"] = yearly["age_years"].astype(int) - start_age_years
    return yearly.reset_index(drop=True)


def asset_value_columns(assets: Iterable[Asset]) -> list[str]:
    """Return the value columns to plot/tabulate.

    Args:
        assets: Assets in the forecast.

    Returns:
        Per-asset balance column names (excluding INHERITANCE, VBLklassik and
        INVESTMENT, which hold no running balance) followed by ``"total"``.
    """
    return [
        asset.name
        for asset in assets
        if asset.asset_type
        not in (
            AssetType.INHERITANCE,
            AssetType.VBL_KLASSIK,
            AssetType.INVESTMENT,
        )
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
    log_scale: bool = False,
) -> list[dict[str, Any]]:
    """Build ECharts line-series definitions for each value column.

    Args:
        frame: Display frame containing the value columns.
        value_columns: Column names to plot.
        log_scale: When ``True``, clamp every value up to a 1 € minimum
            (:data:`LOG_SCALE_VALUE_FLOOR_EUR`) so the log axis stays well-defined
            for non-positive values. The axis bottom is 1000 €, so values below
            it simply slide off the bottom of the chart.

    Returns:
        One smooth line-series definition per value column.
    """

    def points(column: str) -> list[Any]:
        values = frame[column].tolist()
        if not log_scale:
            return values
        return [max(value, LOG_SCALE_VALUE_FLOOR_EUR) for value in values]

    return [
        {
            "name": column,
            "type": "line",
            "data": points(column),
            "smooth": True,
            "showSymbol": False,
        }
        for column in value_columns
    ]
