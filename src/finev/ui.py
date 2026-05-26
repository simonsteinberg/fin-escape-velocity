"""NiceGUI page composition for the wealth forecast app."""

from __future__ import annotations

from typing import Any

import pandas as pd
from nicegui import ui

from finev.forecast import forecast_wealth
from finev.models import (
    DEFAULT_ANNUAL_GAIN_RATES,
    Asset,
    AssetType,
    UserProfile,
    WithdrawalPlan,
)


def _format_currency(value: float, currency: str) -> str:
    """Format a numeric value with a currency suffix.

    Args:
        value: Amount to format.
        currency: Currency code or symbol.

    Returns:
        Formatted currency string.
    """
    return f"{value:,.0f} {currency}".strip()


def _default_gain_pct(asset_type: AssetType) -> float:
    """Return the default annual gain percentage for an asset type."""
    return DEFAULT_ANNUAL_GAIN_RATES[asset_type] * 100


def _default_asset_rows() -> list[dict[str, Any]]:
    """Return default asset input rows for the UI.

    Returns:
        List of asset row dictionaries.
    """
    return [
        {
            "name": "ETF MSCI World",
            "type": AssetType.ETF.value,
            "current_value": 100_000.0,
            "unrealized_gains": 0.0,
            "annual_gain_rate_pct": _default_gain_pct(AssetType.ETF),
            "monthly_contribution": 500.0,
        },
        {
            "name": "bAV",
            "type": AssetType.BAV.value,
            "current_value": 20_000.0,
            "unrealized_gains": 0.0,
            "annual_gain_rate_pct": _default_gain_pct(AssetType.BAV),
            "monthly_contribution": 100.0,
        },
        {
            "name": "Daily account",
            "type": AssetType.CASH.value,
            "current_value": 50_000.0,
            "unrealized_gains": 0.0,
            "annual_gain_rate_pct": _default_gain_pct(AssetType.CASH),
            "monthly_contribution": 0.0,
        },
    ]


def _asset_from_row(row: dict[str, Any]) -> Asset:
    """Build an Asset instance from a UI row definition."""
    asset_type = AssetType(str(row.get("type")))
    rate_pct = row.get("annual_gain_rate_pct")
    annual_rate = None if rate_pct in (None, "") else float(rate_pct) / 100
    current_value = float(row.get("current_value") or 0)
    unrealized_gains = float(row.get("unrealized_gains") or 0)
    unrealized_gains = min(unrealized_gains, current_value)
    initial_cost_basis = current_value - unrealized_gains
    return Asset(
        name=str(row.get("name", "")).strip(),
        asset_type=asset_type,
        current_value=current_value,
        initial_cost_basis=initial_cost_basis,
        annual_gain_rate=annual_rate,
        monthly_contribution=float(row.get("monthly_contribution") or 0),
    )


def _build_chart_options() -> dict[str, Any]:
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


def _yearly_display_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Return a yearly-sampled DataFrame for presentation."""
    if df.empty:
        return df
    yearly = df[df["month_index"] % 12 == 0].copy()
    yearly["year_index"] = (yearly["month_index"] // 12).astype(int)
    return yearly.reset_index(drop=True)


def build_wealth_page() -> None:
    """Construct UI and bind update logic."""
    asset_rows = _default_asset_rows()

    def update_asset_row(index: int, field: str, value: Any) -> None:
        """Update a field on a specific asset row.

        Args:
            index: Row index to update.
            field: Field name to update.
            value: New field value.
        """
        current_row = asset_rows[index]
        if field == "type":
            previous_type = AssetType(str(current_row.get("type")))
            new_type = AssetType(str(value))
            current_default = _default_gain_pct(previous_type)
            if current_row.get("annual_gain_rate_pct") in (
                None,
                "",
                current_default,
            ):
                current_row["annual_gain_rate_pct"] = _default_gain_pct(
                    new_type
                )
            if current_row.get("unrealized_gains") in (None, ""):
                current_row["unrealized_gains"] = 0.0
        if field == "current_value":
            unrealized_gains = float(current_row.get("unrealized_gains") or 0)
            current_row["unrealized_gains"] = min(
                unrealized_gains, float(value or 0)
            )
        current_row[field] = value
        if field in {"type", "current_value"}:
            render_asset_rows()
        run_forecast()

    def remove_asset_row(index: int) -> None:
        """Remove an asset row from the list.

        Args:
            index: Row index to remove.
        """
        asset_rows.pop(index)
        render_asset_rows()
        run_forecast()

    def add_asset_row() -> None:
        """Append a new blank asset row."""
        asset_rows.append(
            {
                "name": "New asset",
                "type": AssetType.ETF.value,
                "current_value": 0.0,
                "unrealized_gains": 0.0,
                "annual_gain_rate_pct": _default_gain_pct(AssetType.ETF),
                "monthly_contribution": 0.0,
            }
        )
        render_asset_rows()
        run_forecast()

    def build_assets() -> list[Asset]:
        """Build asset objects from the current UI rows.

        Returns:
            List of assets for the forecast.
        """
        return [_asset_from_row(row) for row in asset_rows]

    with ui.column().classes("w-full max-w-[1200px] mx-auto p-4 gap-4"):
        ui.label("Wealth Forecast").classes("text-2xl font-bold")
        with ui.card().classes("w-full p-3"):
            ui.label("Assets").classes("text-lg font-semibold")
            ui.label(
                "Defaults: ETF 5.0% | bAV 2.0% | Cash 0.5% (annual)"
            ).classes("text-xs text-gray-500")

            assets_container = ui.column().classes("w-full gap-2")

            def render_asset_rows() -> None:
                """Render the asset input rows."""
                assets_container.clear()
                for index, row in enumerate(asset_rows):
                    with assets_container:
                        with ui.row().classes("w-full gap-2 items-end"):
                            current_value = float(
                                row.get("current_value") or 0
                            )
                            ui.input(
                                label="Name",
                                value=row["name"],
                                on_change=lambda e, i=index: update_asset_row(
                                    i, "name", e.value
                                ),
                            ).classes("w-48")
                            ui.select(
                                options=[item.value for item in AssetType],
                                value=row["type"],
                                label="Type",
                                on_change=lambda e, i=index: update_asset_row(
                                    i, "type", e.value
                                ),
                            ).classes("w-28")
                            ui.number(
                                label="Current value",
                                value=row["current_value"],
                                format="%.0f",
                                min=0,
                                step=1000,
                                on_change=lambda e, i=index: update_asset_row(
                                    i, "current_value", e.value
                                ),
                            ).classes("w-32")
                            ui.number(
                                label="Unrealized gains",
                                value=row.get("unrealized_gains") or 0,
                                format="%.0f",
                                min=0,
                                max=current_value,
                                step=100,
                                on_change=lambda e, i=index: update_asset_row(
                                    i, "unrealized_gains", e.value
                                ),
                            ).classes("w-36")
                            ui.number(
                                label="Annual gain (%)",
                                value=row["annual_gain_rate_pct"],
                                format="%.1f",
                                step=0.1,
                                on_change=lambda e, i=index: update_asset_row(
                                    i, "annual_gain_rate_pct", e.value
                                ),
                            ).classes("w-32")
                            ui.number(
                                label="Monthly contribution",
                                value=row["monthly_contribution"],
                                format="%.0f",
                                min=0,
                                step=50,
                                on_change=lambda e, i=index: update_asset_row(
                                    i, "monthly_contribution", e.value
                                ),
                            ).classes("w-36")
                            ui.button(
                                icon="delete",
                                on_click=lambda i=index: remove_asset_row(i),
                            ).props("dense flat color=red")

            render_asset_rows()

            ui.button("Add asset", on_click=add_asset_row).props(
                "outline color=green-4"
            )

        with ui.card().classes("w-full p-3"):
            ui.label("Profile").classes("text-lg font-semibold")
            with ui.grid(columns=6).classes("w-full gap-3"):
                current_age_years = ui.number(
                    label="Current age (years)",
                    value=40,
                    format="%.0f",
                    on_change=lambda _: run_forecast(),
                )
                current_age_months = ui.number(
                    label="Current age (months)",
                    value=0,
                    format="%.0f",
                    min=0,
                    max=11,
                    on_change=lambda _: run_forecast(),
                )
                retirement_age = ui.number(
                    label="Retirement age",
                    value=67,
                    format="%.0f",
                    on_change=lambda _: run_forecast(),
                )
                end_age = ui.number(
                    label="End age",
                    value=100,
                    format="%.0f",
                    on_change=lambda _: run_forecast(),
                )
                currency = ui.input(
                    label="Currency",
                    value="EUR",
                    on_change=lambda _: run_forecast(),
                )
                average_inflation_rate = ui.number(
                    label="Average inflation rate (%)",
                    value=2.0,
                    format="%.2f",
                    min=-99.9,
                    step=0.1,
                    on_change=lambda _: run_forecast(),
                )
                withdrawal_input = ui.number(
                    label="Monthly withdrawal",
                    value=3000,
                    format="%.0f",
                    min=0,
                    step=50,
                    on_change=lambda _: run_forecast(),
                )

        summary_label = ui.label("No forecast yet.").classes("text-sm")
        chart = ui.echart(_build_chart_options()).classes("w-full h-72")
        table = (
            ui.table(columns=[], rows=[], row_key="month_index")
            .props("dense flat bordered separator=horizontal")
            .classes("w-full text-xs")
        )

        def run_forecast() -> None:
            """Run the forecast and update the UI outputs."""
            try:
                profile = UserProfile(
                    current_age_years=int(current_age_years.value or 0),
                    current_age_months=int(current_age_months.value or 0),
                    retirement_age=int(retirement_age.value or 0),
                    end_age=int(end_age.value or 0),
                    currency=str(currency.value or "EUR"),
                    average_inflation_rate=float(
                        average_inflation_rate.value or 0.0
                    )
                    / 100,
                )
                assets = build_assets()
                withdrawal = WithdrawalPlan(
                    monthly_withdrawal=float(withdrawal_input.value or 0),
                )
                df = forecast_wealth(
                    profile=profile,
                    assets=assets,
                    withdrawal=withdrawal,
                )
            except (ValueError, KeyError) as error:
                ui.notify(str(error), type="negative")
                return

            display_df = _yearly_display_frame(df)
            age_labels = [
                f"{int(row.age_years)}" for row in display_df.itertuples()
            ]
            rounded = display_df.copy()
            rounded["age"] = age_labels
            numeric_columns = rounded.select_dtypes(include="number").columns
            rounded[numeric_columns] = (
                rounded[numeric_columns].round(0).astype(int)
            )

            columns = [
                {
                    "name": "year_index",
                    "label": "Year",
                    "field": "year_index",
                    "sortable": True,
                },
                {
                    "name": "age",
                    "label": "Age",
                    "field": "age",
                    "sortable": False,
                },
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
            asset_columns = [asset.name for asset in assets] + ["total"]
            for column in asset_columns:
                columns.append(
                    {
                        "name": column,
                        "label": column,
                        "field": column,
                        "sortable": True,
                    }
                )

            table.columns = columns
            table.rows = rounded.to_dict(orient="records")
            table.update()

            series = []
            for column in asset_columns:
                series.append(
                    {
                        "name": column,
                        "type": "line",
                        "data": rounded[column].tolist(),
                        "smooth": True,
                        "showSymbol": False,
                    }
                )

            chart.options["xAxis"]["data"] = age_labels
            chart.options["series"] = series
            chart.update()

            final_total = float(df["total"].iloc[-1])
            summary_label.text = (
                f"Total at age {profile.end_age}: "
                f"{_format_currency(final_total, profile.currency)}"
            )

        run_forecast()
