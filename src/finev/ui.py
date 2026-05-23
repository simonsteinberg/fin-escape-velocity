"""NiceGUI page composition for the wealth forecast app."""

from __future__ import annotations

from typing import Any
from nicegui import ui

from finev.forecast import forecast_wealth
from finev.models import (
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
    return f"{value:,.2f} {currency}".strip()


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
            "annual_gain_rate_pct": None,
            "monthly_contribution": 500.0,
        },
        {
            "name": "bAV",
            "type": AssetType.BAV.value,
            "current_value": 20_000.0,
            "annual_gain_rate_pct": None,
            "monthly_contribution": 100.0,
        },
        {
            "name": "Daily account",
            "type": AssetType.CASH.value,
            "current_value": 50_000.0,
            "annual_gain_rate_pct": None,
            "monthly_contribution": 0.0,
        },
    ]


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
        asset_rows[index][field] = value

    def remove_asset_row(index: int) -> None:
        """Remove an asset row from the list.

        Args:
            index: Row index to remove.
        """
        asset_rows.pop(index)
        render_asset_rows()

    def add_asset_row() -> None:
        """Append a new blank asset row."""
        asset_rows.append(
            {
                "name": "New asset",
                "type": AssetType.ETF.value,
                "current_value": 0.0,
                "annual_gain_rate_pct": None,
                "monthly_contribution": 0.0,
            }
        )
        render_asset_rows()

    def build_assets() -> list[Asset]:
        """Build asset objects from the current UI rows.

        Returns:
            List of assets for the forecast.
        """
        assets: list[Asset] = []
        for row in asset_rows:
            rate_pct = row.get("annual_gain_rate_pct")
            annual_rate = (
                None if rate_pct in (None, "") else float(rate_pct) / 100
            )
            assets.append(
                Asset(
                    name=str(row.get("name", "")).strip(),
                    asset_type=AssetType(str(row.get("type"))),
                    current_value=float(row.get("current_value") or 0),
                    annual_gain_rate=annual_rate,
                    monthly_contribution=float(
                        row.get("monthly_contribution") or 0
                    ),
                )
            )
        return assets

    with ui.column().classes("w-full max-w-[1200px] mx-auto p-4 gap-4"):
        ui.label("Wealth Forecast").classes("text-2xl font-bold")
        with ui.card().classes("w-full p-3"):
            ui.label("Profile").classes("text-lg font-semibold")
            with ui.grid(columns=6).classes("w-full gap-3"):
                current_age_years = ui.number(
                    label="Current age (years)", value=40, format="%.0f"
                )
                current_age_months = ui.number(
                    label="Current age (months)",
                    value=0,
                    format="%.0f",
                    min=0,
                    max=11,
                )
                retirement_age = ui.number(
                    label="Retirement age", value=67, format="%.0f"
                )
                end_age = ui.number(label="End age", value=100, format="%.0f")
                currency = ui.input(label="Currency", value="EUR")
                average_inflation_rate = ui.number(
                    label="Average inflation rate (%)",
                    value=2.0,
                    format="%.2f",
                    min=-100,
                    step=0.1,
                )

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
                                format="%.2f",
                                min=0,
                                on_change=lambda e, i=index: update_asset_row(
                                    i, "current_value", e.value
                                ),
                            ).classes("w-32")
                            ui.number(
                                label="Annual gain (%)",
                                value=row["annual_gain_rate_pct"],
                                format="%.2f",
                                on_change=lambda e, i=index: update_asset_row(
                                    i, "annual_gain_rate_pct", e.value
                                ),
                            ).classes("w-32")
                            ui.number(
                                label="Monthly contribution",
                                value=row["monthly_contribution"],
                                format="%.2f",
                                min=0,
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
            ui.label("Retirement withdrawals").classes("text-lg font-semibold")
            withdrawal_input = ui.number(
                label="Monthly withdrawal after retirement",
                value=3000,
                format="%.2f",
                min=0,
            )

        run_button = ui.button("Run forecast").props("color=green-4")

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

            age_labels = [
                f"{int(row.age_years)}y {int(row.age_months)}m"
                for row in df.itertuples()
            ]
            rounded = df.copy()
            rounded["age"] = age_labels
            rounded = rounded.round(2)

            columns = [
                {
                    "name": "month_index",
                    "label": "Month",
                    "field": "month_index",
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
                    "label": "Net cashflow",
                    "field": "net_cashflow",
                    "sortable": True,
                },
                {
                    "name": "taxes",
                    "label": "Taxes",
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

        run_button.on_click(run_forecast)
