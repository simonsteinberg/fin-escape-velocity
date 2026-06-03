"""NiceGUI page composition for the wealth forecast app."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from nicegui import ui

from finev.config import get_config
from finev.forecast import forecast_wealth
from finev.models import (
    Asset,
    AssetType,
    BAVStrategy,
    InheritanceRelationship,
    StatePension,
    UserProfile,
    WithdrawalPlan,
)
from finev.pension import (
    early_retirement_penalty_fraction,
    estimate_monthly_growth_per_working_year,
    estimate_pension_at_start,
)
from finev.ui_state import (
    asset_from_row as _asset_from_row,
)
from finev.ui_state import (
    clear_cached_state as _clear_cached_state,
)
from finev.ui_state import (
    default_asset_rows as _default_asset_rows,
)
from finev.ui_state import (
    default_gain_pct as _default_gain_pct,
)
from finev.ui_state import (
    default_profile_state as _default_profile_state,
)
from finev.ui_state import (
    default_withdrawal_state as _default_withdrawal_state,
)
from finev.ui_state import (
    load_asset_rows as _load_asset_rows,
)
from finev.ui_state import (
    load_cached_state as _load_cached_state,
)
from finev.ui_state import (
    load_profile_state as _load_profile_state,
)
from finev.ui_state import (
    load_withdrawal_state as _load_withdrawal_state,
)
from finev.ui_state import (
    normalize_asset_row as _normalize_asset_row,
)
from finev.ui_state import (
    save_cached_state as _save_cached_state,
)
from finev.ui_view import (
    build_chart_options as _build_chart_options,
)
from finev.ui_view import (
    format_currency as _format_currency,
)
from finev.ui_view import (
    yearly_display_frame as _yearly_display_frame,
)


def build_wealth_page() -> None:
    """Construct UI and bind update logic."""
    state_error: str | None = None
    cached_state: dict[str, Any] | None = None
    try:
        cached_state = _load_cached_state()
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        state_error = f"Failed to load cached state: {exc}"
        cached_state = None

    asset_rows = _load_asset_rows(cached_state)
    profile_state = _load_profile_state(cached_state)
    withdrawal_state = _load_withdrawal_state(cached_state)
    default_profile_state = _default_profile_state()
    default_withdrawal_state = _default_withdrawal_state()
    suppress_cache_save = False
    debounce_seconds = 0.5
    pending_handle: asyncio.Handle | None = None
    pending_rebuild = False

    def _run_scheduled() -> None:
        nonlocal pending_handle, pending_rebuild
        pending_handle = None
        if pending_rebuild:
            pending_rebuild = False
            render_asset_rows()
        run_forecast()

    def schedule_forecast(rebuild_assets: bool = False) -> None:
        nonlocal pending_handle, pending_rebuild
        pending_rebuild = pending_rebuild or rebuild_assets
        if pending_handle is not None:
            pending_handle.cancel()
        pending_handle = asyncio.get_running_loop().call_later(
            debounce_seconds, _run_scheduled
        )

    def run_immediate(rebuild_assets: bool = False) -> None:
        nonlocal pending_handle, pending_rebuild
        if pending_handle is not None:
            pending_handle.cancel()
            pending_handle = None
        if rebuild_assets:
            pending_rebuild = False
            render_asset_rows()
        run_forecast()

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
            if new_type != AssetType.INHERITANCE:
                current_default = (
                    _default_gain_pct(previous_type)
                    if previous_type != AssetType.INHERITANCE
                    else _default_gain_pct(new_type)
                )
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
                if current_row.get("bav_strategy") in (None, ""):
                    current_row["bav_strategy"] = BAVStrategy.TRANSFER.value
                if current_row.get("bav_transfer_start_age") in (None, ""):
                    current_row["bav_transfer_start_age"] = 67
                if current_row.get("bav_transfer_end_age") in (None, ""):
                    current_row["bav_transfer_end_age"] = 72
                if current_row.get("bav_transfer_etf_ratio_pct") in (None, ""):
                    current_row["bav_transfer_etf_ratio_pct"] = 50.0
            if current_row.get("inheritance_gross_amount") in (None, ""):
                current_row["inheritance_gross_amount"] = 0.0
            if current_row.get("inheritance_age") in (None, ""):
                current_row["inheritance_age"] = 67
            if current_row.get("inheritance_relationship") in (None, ""):
                current_row["inheritance_relationship"] = (
                    InheritanceRelationship.KIND.value
                )
        if field == "bav_strategy":
            try:
                value = BAVStrategy(str(value)).value
            except ValueError:
                value = BAVStrategy.TRANSFER.value
        if field == "inheritance_relationship":
            try:
                value = InheritanceRelationship(str(value)).value
            except ValueError:
                value = InheritanceRelationship.KIND.value
        if field == "inheritance_gross_amount":
            value = max(float(value or 0), 0.0)
        if field == "inheritance_age":
            value = max(int(value or 0), 0)
        if field == "unrealized_gains":
            current_value = float(current_row.get("current_value") or 0)
            value = max(min(float(value or 0), current_value), 0.0)
        if field in {"bav_transfer_start_age", "bav_transfer_end_age"}:
            value = max(int(value or 0), 0)
        if field == "bav_transfer_etf_ratio_pct":
            value = max(min(float(value or 0), 100.0), 0.0)
        if field == "current_value":
            unrealized_gains = float(current_row.get("unrealized_gains") or 0)
            current_row["unrealized_gains"] = min(
                unrealized_gains, float(value or 0)
            )
        current_row[field] = value
        if field in {
            "type",
            "bav_strategy",
            "active",
            "inheritance_relationship",
        }:
            render_asset_rows()
            run_immediate()
            return
        if field == "current_value":
            schedule_forecast(rebuild_assets=True)
            return
        schedule_forecast()

    def remove_asset_row(index: int) -> None:
        """Remove an asset row from the list.

        Args:
            index: Row index to remove.
        """
        asset_rows.pop(index)
        render_asset_rows()
        run_immediate()

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
                "active": True,
                "bav_strategy": BAVStrategy.TRANSFER.value,
                "bav_transfer_start_age": 67,
                "bav_transfer_end_age": 72,
                "bav_transfer_etf_ratio_pct": 50.0,
                "inheritance_gross_amount": 0.0,
                "inheritance_age": 67,
                "inheritance_relationship": InheritanceRelationship.KIND.value,
            }
        )
        render_asset_rows()
        run_immediate()

    def reset_state() -> None:
        """Reset UI values to defaults and clear cached state."""
        nonlocal suppress_cache_save
        suppress_cache_save = True
        asset_rows[:] = _default_asset_rows()
        current_age_years.value = default_profile_state["current_age_years"]
        current_age_years.update()
        current_age_months.value = default_profile_state["current_age_months"]
        current_age_months.update()
        retirement_age.value = default_profile_state["retirement_age"]
        retirement_age.update()
        end_age.value = default_profile_state["end_age"]
        end_age.update()
        currency.value = default_profile_state["currency"]
        currency.update()
        average_inflation_rate.value = default_profile_state[
            "average_inflation_rate_pct"
        ]
        average_inflation_rate.update()
        annual_income.value = default_profile_state["annual_income"]
        annual_income.update()
        withdrawal_input.value = default_withdrawal_state["monthly_withdrawal"]
        withdrawal_input.update()
        state_pension_current_monthly_amount.value = default_withdrawal_state[
            "state_pension_current_monthly_amount"
        ]
        state_pension_current_monthly_amount.update()
        state_pension_growth_display.text = (
            _format_currency(
                default_withdrawal_state[
                    "state_pension_growth_per_working_year"
                ],
                default_profile_state["currency"],
            )
            + " p.m."
        )
        state_pension_growth_display.update()
        # Reset penalty display to empty (no penalty by default at retirement age 67)
        try:
            state_pension_penalty_display.text = ""
            state_pension_penalty_display.update()
            state_pension_achieved_display.text = ""
            state_pension_achieved_display.update()
        except NameError:
            # UI not fully constructed yet; ignore
            pass
        state_pension_start_age.value = default_withdrawal_state[
            "state_pension_start_age"
        ]
        state_pension_start_age.update()
        render_asset_rows()
        run_immediate()
        suppress_cache_save = False
        try:
            _clear_cached_state()
        except OSError as error:
            ui.notify(
                f"Failed to clear cached state: {error}", type="negative"
            )

    def build_assets() -> list[Asset]:
        """Build asset objects from the current UI rows.

        Returns:
            List of assets for the forecast.
        """
        return [_asset_from_row(row) for row in asset_rows]

    with ui.column().classes("w-full p-4 gap-4"):
        ui.label("Wealth Forecast").classes("text-2xl font-bold")
        with ui.row().classes("w-full gap-4 items-start"):
            # ── Left sidebar ──────────────────────────────────────────────
            with ui.column().classes("w-[420px] shrink-0 gap-4"):
                with ui.card().classes("w-full p-3"):
                    ui.label("Profile").classes("text-lg font-semibold")
                    with ui.grid(columns=2).classes("w-full gap-3"):
                        current_age_years = ui.number(
                            label="Current age (years)",
                            value=profile_state["current_age_years"],
                            format="%.0f",
                            on_change=lambda _: schedule_forecast(),
                        )
                        current_age_months = ui.number(
                            label="Current age (months)",
                            value=profile_state["current_age_months"],
                            format="%.0f",
                            min=0,
                            max=11,
                            on_change=lambda _: schedule_forecast(),
                        )
                        retirement_age = ui.number(
                            label="Retirement age",
                            value=profile_state["retirement_age"],
                            format="%.0f",
                            on_change=lambda _: schedule_forecast(),
                        )
                        end_age = ui.number(
                            label="End age",
                            value=profile_state["end_age"],
                            format="%.0f",
                            on_change=lambda _: schedule_forecast(),
                        )
                        currency = ui.input(
                            label="Currency",
                            value=profile_state["currency"],
                            on_change=lambda _: schedule_forecast(),
                        )
                        average_inflation_rate = ui.number(
                            label="Average inflation rate (%)",
                            value=profile_state["average_inflation_rate_pct"],
                            format="%.2f",
                            min=-99.9,
                            step=0.1,
                            on_change=lambda _: schedule_forecast(),
                        )
                        withdrawal_input = ui.number(
                            label="Monthly withdrawal",
                            value=withdrawal_state["monthly_withdrawal"],
                            format="%.0f",
                            min=0,
                            step=50,
                            on_change=lambda _: schedule_forecast(),
                        )

                with ui.card().classes("w-full p-3"):
                    ui.label("State pension").classes("text-lg font-semibold")
                    with ui.grid(columns=2).classes("w-full gap-3"):
                        annual_income = ui.number(
                            label="Annual income",
                            value=profile_state.get("annual_income", 50000.0),
                            format="%.0f",
                            min=0,
                            step=1000,
                            on_change=lambda _: schedule_forecast(),
                        )
                        state_pension_current_monthly_amount = ui.number(
                            label="State pension now (monthly)",
                            value=withdrawal_state[
                                "state_pension_current_monthly_amount"
                            ],
                            format="%.0f",
                            min=0,
                            step=50,
                            on_change=lambda _: schedule_forecast(),
                        )
                        state_pension_growth_display = ui.label(
                            _format_currency(
                                withdrawal_state[
                                    "state_pension_growth_per_working_year"
                                ],
                                profile_state["currency"],
                            )
                            + " p.m."
                        )
                        # Read-only display for estimated early-retirement penalty at pension start
                        state_pension_penalty_display = ui.label("")
                        # Read-only display for total achieved monthly pension at start age
                        state_pension_achieved_display = ui.label("")
                        state_pension_start_age = ui.number(
                            label="State pension start age",
                            value=withdrawal_state["state_pension_start_age"],
                            format="%.0f",
                            min=63,
                            max=67,
                            step=1,
                            on_change=lambda _: schedule_forecast(),
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
                                with ui.column().classes(
                                    "w-full gap-1 p-2 border rounded"
                                ):
                                    with ui.row().classes(
                                        "w-full gap-2 items-center"
                                    ):
                                        asset_type = AssetType(
                                            str(row.get("type"))
                                        )
                                        current_value = float(
                                            row.get("current_value") or 0
                                        )
                                        # Active toggle (hide/show) for what-if scenarios
                                        ui.button(
                                            icon=(
                                                "visibility"
                                                if row.get("active", True)
                                                else "visibility_off"
                                            ),
                                            on_click=lambda e, i=index: (
                                                update_asset_row(
                                                    i,
                                                    "active",
                                                    not asset_rows[i].get(
                                                        "active", True
                                                    ),
                                                )
                                            ),
                                        ).props("dense flat")
                                        ui.input(
                                            label="Name",
                                            value=row["name"],
                                            on_change=lambda e, i=index: (
                                                update_asset_row(
                                                    i, "name", e.value
                                                )
                                            ),
                                        ).classes("flex-1")
                                        ui.select(
                                            options=[
                                                item.value
                                                for item in AssetType
                                            ],
                                            value=row["type"],
                                            label="Type",
                                            on_change=lambda e, i=index: (
                                                update_asset_row(
                                                    i, "type", e.value
                                                )
                                            ),
                                        ).classes("w-28")
                                        ui.button(
                                            icon="delete",
                                            on_click=lambda i=index: (
                                                remove_asset_row(i)
                                            ),
                                        ).props("dense flat color=red")
                                    if asset_type == AssetType.INHERITANCE:
                                        _inheritance_relationship_labels = {
                                            InheritanceRelationship.EHEGATTE.value: "Ehegatte / Lebenspartner (I, 500 K€)",
                                            InheritanceRelationship.KIND.value: "Kind / Stiefkind (I, 400 K€)",
                                            InheritanceRelationship.ENKEL.value: "Enkel (I, 200 K€)",
                                            InheritanceRelationship.ELTERNTEIL.value: "Elternteil (I, 100 K€)",
                                            InheritanceRelationship.KLASSE_II.value: "Geschwister / Nichte / Neffe (II, 20 K€)",
                                            InheritanceRelationship.KLASSE_III.value: "Sonstige (III, 20 K€)",
                                        }
                                        with ui.grid(columns=2).classes(
                                            "w-full gap-2"
                                        ):
                                            ui.number(
                                                label="Gross amount",
                                                value=row.get(
                                                    "inheritance_gross_amount"
                                                )
                                                or 0,
                                                format="%.0f",
                                                min=0,
                                                step=10000,
                                                on_change=lambda e, i=index: (
                                                    update_asset_row(
                                                        i,
                                                        "inheritance_gross_amount",
                                                        e.value,
                                                    )
                                                ),
                                            ).classes("w-full")
                                            ui.number(
                                                label="Age at receipt",
                                                value=row.get(
                                                    "inheritance_age"
                                                )
                                                or 67,
                                                format="%.0f",
                                                min=0,
                                                step=1,
                                                on_change=lambda e, i=index: (
                                                    update_asset_row(
                                                        i,
                                                        "inheritance_age",
                                                        e.value,
                                                    )
                                                ),
                                            ).classes("w-full")
                                        ui.select(
                                            options=_inheritance_relationship_labels,
                                            value=row.get(
                                                "inheritance_relationship",
                                                InheritanceRelationship.KIND.value,
                                            ),
                                            label="Relationship",
                                            on_change=lambda e, i=index: (
                                                update_asset_row(
                                                    i,
                                                    "inheritance_relationship",
                                                    e.value,
                                                )
                                            ),
                                        ).classes("w-full")
                                    else:
                                        with ui.grid(columns=2).classes(
                                            "w-full gap-2"
                                        ):
                                            ui.number(
                                                label="Current value",
                                                value=row["current_value"],
                                                format="%.0f",
                                                min=0,
                                                step=10000,
                                                on_change=lambda e, i=index: (
                                                    update_asset_row(
                                                        i,
                                                        "current_value",
                                                        e.value,
                                                    )
                                                ),
                                            ).classes("w-full")
                                            ui.number(
                                                label="Unrealized gains",
                                                value=row.get(
                                                    "unrealized_gains"
                                                )
                                                or 0,
                                                format="%.0f",
                                                min=0,
                                                max=current_value,
                                                step=10000,
                                                on_change=lambda e, i=index: (
                                                    update_asset_row(
                                                        i,
                                                        "unrealized_gains",
                                                        e.value,
                                                    )
                                                ),
                                            ).classes("w-full")
                                            ui.number(
                                                label="Annual gain (%)",
                                                value=row[
                                                    "annual_gain_rate_pct"
                                                ],
                                                format="%.1f",
                                                step=0.1,
                                                on_change=lambda e, i=index: (
                                                    update_asset_row(
                                                        i,
                                                        "annual_gain_rate_pct",
                                                        e.value,
                                                    )
                                                ),
                                            ).classes("w-full")
                                            ui.number(
                                                label="Monthly contribution",
                                                value=row[
                                                    "monthly_contribution"
                                                ],
                                                format="%.0f",
                                                min=0,
                                                step=50,
                                                on_change=lambda e, i=index: (
                                                    update_asset_row(
                                                        i,
                                                        "monthly_contribution",
                                                        e.value,
                                                    )
                                                ),
                                            ).classes("w-full")
                                        if asset_type == AssetType.BAV:
                                            with ui.column().classes(
                                                "w-full gap-2"
                                            ):
                                                ui.select(
                                                    options={
                                                        BAVStrategy.TRANSFER.value: (
                                                            "Transfer to ETF/Cash"
                                                        ),
                                                        BAVStrategy.INCOME.value: (
                                                            "Monthly gains income"
                                                        ),
                                                    },
                                                    value=row.get(
                                                        "bav_strategy",
                                                        BAVStrategy.TRANSFER.value,
                                                    ),
                                                    label="bAV mode",
                                                    on_change=lambda e, i=index: (
                                                        update_asset_row(
                                                            i,
                                                            "bav_strategy",
                                                            e.value,
                                                        )
                                                    ),
                                                ).classes("w-full")
                                                if row.get("bav_strategy") == (
                                                    BAVStrategy.TRANSFER.value
                                                ):
                                                    with ui.row().classes(
                                                        "w-full gap-2"
                                                    ):
                                                        ui.number(
                                                            label="Transfer start age",
                                                            value=row.get(
                                                                "bav_transfer_start_age",
                                                                67,
                                                            ),
                                                            format="%.0f",
                                                            min=0,
                                                            step=1,
                                                            on_change=lambda e, i=index: (
                                                                update_asset_row(
                                                                    i,
                                                                    "bav_transfer_start_age",
                                                                    e.value,
                                                                )
                                                            ),
                                                        ).classes("w-32")
                                                        ui.number(
                                                            label="Transfer end age",
                                                            value=row.get(
                                                                "bav_transfer_end_age",
                                                                72,
                                                            ),
                                                            format="%.0f",
                                                            min=0,
                                                            step=1,
                                                            on_change=lambda e, i=index: (
                                                                update_asset_row(
                                                                    i,
                                                                    "bav_transfer_end_age",
                                                                    e.value,
                                                                )
                                                            ),
                                                        ).classes("w-32")
                                                        ui.number(
                                                            label="ETF share (%)",
                                                            value=row.get(
                                                                "bav_transfer_etf_ratio_pct",
                                                                50.0,
                                                            ),
                                                            format="%.0f",
                                                            min=0,
                                                            max=100,
                                                            step=5,
                                                            on_change=lambda e, i=index: (
                                                                update_asset_row(
                                                                    i,
                                                                    "bav_transfer_etf_ratio_pct",
                                                                    e.value,
                                                                )
                                                            ),
                                                        ).classes("w-28")
                                                elif row.get(
                                                    "bav_strategy"
                                                ) == (
                                                    BAVStrategy.INCOME.value
                                                ):
                                                    ui.number(
                                                        label="Withdraw start age",
                                                        value=row.get(
                                                            "bav_transfer_start_age",
                                                            67,
                                                        ),
                                                        format="%.0f",
                                                        min=0,
                                                        step=1,
                                                        on_change=lambda e, i=index: (
                                                            update_asset_row(
                                                                i,
                                                                "bav_transfer_start_age",
                                                                e.value,
                                                            )
                                                        ),
                                                    ).classes("w-32")

                    render_asset_rows()

                    with ui.row().classes("gap-2"):
                        ui.button("Add asset", on_click=add_asset_row).props(
                            "outline color=green-4"
                        )
                        ui.button("Reset", on_click=reset_state).props(
                            "outline color=red"
                        )

            # ── Right panel (chart + table) ───────────────────────────────
            with ui.column().classes("flex-1 min-w-0 gap-4"):
                summary_label = ui.label("No forecast yet.").classes("text-sm")
                chart = ui.echart(_build_chart_options()).classes(
                    "w-full h-[500px]"
                )
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
                # State-pension estimates (display-only). The business math lives
                # in finev.pension; the UI only renders the results.
                config = get_config()
                annual_income_value = float(annual_income.value or 0)
                pension_start_age = int(state_pension_start_age.value or 67)
                monthly_growth_per_working_year_computed = (
                    estimate_monthly_growth_per_working_year(
                        annual_income_value, config.drv
                    )
                )
                penalty_fraction = early_retirement_penalty_fraction(
                    pension_start_age, config.drv
                )
                years_remaining = max(
                    0, profile.retirement_age - profile.current_age_years
                )
                net_pension = estimate_pension_at_start(
                    current_monthly_amount=float(
                        state_pension_current_monthly_amount.value or 0
                    ),
                    monthly_growth_per_working_year=(
                        monthly_growth_per_working_year_computed
                    ),
                    years_until_retirement=years_remaining,
                    penalty_fraction=penalty_fraction,
                )

                state_pension_growth_display.text = (
                    _format_currency(
                        monthly_growth_per_working_year_computed,
                        profile.currency,
                    )
                    + " p.m."
                )
                state_pension_growth_display.update()
                if penalty_fraction > 0:
                    penalty_monthly = (
                        monthly_growth_per_working_year_computed
                        * penalty_fraction
                    )
                    state_pension_penalty_display.text = (
                        "Estimated early-retirement penalty: -"
                        + _format_currency(penalty_monthly, profile.currency)
                        + f" p.m. ({penalty_fraction * 100:.1f}% reduction)"
                    )
                else:
                    state_pension_penalty_display.text = (
                        "No early-retirement penalty"
                    )
                state_pension_penalty_display.update()
                state_pension_achieved_display.text = (
                    f"Pension at age {pension_start_age}: "
                    + _format_currency(net_pension, profile.currency)
                    + " p.m. gross"
                    f" ({years_remaining} working year(s) remaining,"
                    f" retiring at {profile.retirement_age})"
                )
                state_pension_achieved_display.update()

                withdrawal = WithdrawalPlan(
                    monthly_withdrawal=float(withdrawal_input.value or 0),
                    state_pension=StatePension(
                        current_monthly_amount=float(
                            state_pension_current_monthly_amount.value or 0
                        ),
                        monthly_growth_per_working_year=float(
                            monthly_growth_per_working_year_computed
                        ),
                        start_age=pension_start_age,
                    ),
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
                f"{int(age)}" for age in display_df["age_years"].tolist()
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
            asset_columns = [
                asset.name
                for asset in assets
                if asset.asset_type != AssetType.INHERITANCE
            ] + ["total"]
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
            if suppress_cache_save:
                return
            try:
                state_snapshot = {
                    "assets": [
                        _normalize_asset_row(row) for row in asset_rows
                    ],
                    "profile": {
                        "current_age_years": int(current_age_years.value or 0),
                        "current_age_months": int(
                            current_age_months.value or 0
                        ),
                        "retirement_age": int(retirement_age.value or 0),
                        "end_age": int(end_age.value or 0),
                        "currency": str(currency.value or "EUR"),
                        "average_inflation_rate_pct": float(
                            average_inflation_rate.value or 0.0
                        ),
                        "annual_income": float(annual_income.value or 0),
                    },
                    "withdrawal": {
                        "monthly_withdrawal": float(
                            withdrawal_input.value or 0
                        ),
                        "state_pension_current_monthly_amount": float(
                            state_pension_current_monthly_amount.value or 0
                        ),
                        "state_pension_growth_per_working_year": float(
                            monthly_growth_per_working_year_computed
                        ),
                        "state_pension_start_age": int(
                            state_pension_start_age.value or 67
                        ),
                    },
                }
                _save_cached_state(state_snapshot)
            except (OSError, ValueError) as error:
                ui.notify(
                    f"Failed to save cached state: {error}",
                    type="negative",
                )

        run_forecast()
        if state_error:
            ui.notify(state_error, type="negative")
