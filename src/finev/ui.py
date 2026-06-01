"""NiceGUI page composition for the wealth forecast app."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any

import pandas as pd
from nicegui import ui

from finev.forecast import forecast_wealth
from finev.config import get_config
from finev.models import (
    DEFAULT_ANNUAL_GAIN_RATES,
    Asset,
    AssetType,
    BAVStrategy,
    StatePension,
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
            "bav_strategy": BAVStrategy.TRANSFER.value,
            "bav_transfer_start_age": 67,
            "bav_transfer_end_age": 72,
            "bav_transfer_etf_ratio_pct": 50.0,
        },
        {
            "name": "bAV",
            "type": AssetType.BAV.value,
            "current_value": 20_000.0,
            "unrealized_gains": 0.0,
            "annual_gain_rate_pct": _default_gain_pct(AssetType.BAV),
            "monthly_contribution": 100.0,
            "bav_strategy": BAVStrategy.TRANSFER.value,
            "bav_transfer_start_age": 67,
            "bav_transfer_end_age": 72,
            "bav_transfer_etf_ratio_pct": 50.0,
        },
        {
            "name": "Daily account",
            "type": AssetType.CASH.value,
            "current_value": 50_000.0,
            "unrealized_gains": 0.0,
            "annual_gain_rate_pct": _default_gain_pct(AssetType.CASH),
            "monthly_contribution": 0.0,
            "bav_strategy": BAVStrategy.TRANSFER.value,
            "bav_transfer_start_age": 67,
            "bav_transfer_end_age": 72,
            "bav_transfer_etf_ratio_pct": 50.0,
        },
    ]


def _state_path() -> Path:
    """Return the cache path for persisted UI state."""
    env_path = os.getenv("WEALTH_APP_STATE_PATH")
    if env_path:
        return Path(env_path).expanduser()
    repo_root = Path(__file__).resolve().parents[2]
    return repo_root / ".cache" / "finev" / "wealth_state.json"


def _load_cached_state() -> dict[str, Any] | None:
    """Load cached UI state from disk if present."""
    path = _state_path()
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("Cached state must be a JSON object")
    return data


def _save_cached_state(state: dict[str, Any]) -> None:
    """Persist UI state to disk."""
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2, sort_keys=True)


def _clear_cached_state() -> None:
    """Remove the cached UI state file if it exists."""
    path = _state_path()
    if path.exists():
        path.unlink()


def _default_profile_state() -> dict[str, Any]:
    """Return default profile values for UI inputs."""
    return {
        "current_age_years": 40,
        "current_age_months": 0,
        "retirement_age": 67,
        "end_age": 100,
        "currency": "EUR",
            "average_inflation_rate_pct": 2.0,
            "annual_income": 50000.0,
        }


def _default_withdrawal_state() -> dict[str, Any]:
    """Return default withdrawal values for UI inputs."""
    return {
        "monthly_withdrawal": 3000.0,
        "state_pension_current_monthly_amount": 0.0,
        "state_pension_growth_per_working_year": 0.0,
        "state_pension_start_age": 67,
    }


def _coerce_float(value: Any, field_name: str) -> float:
    """Convert a cached value to float or raise a descriptive error."""
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Cached state field '{field_name}' must be a number"
        ) from exc


def _coerce_int(value: Any, field_name: str) -> int:
    """Convert a cached value to int or raise a descriptive error."""
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Cached state field '{field_name}' must be an integer"
        ) from exc


def _normalize_asset_row(row: dict[str, Any]) -> dict[str, Any]:
    """Normalize a cached asset row into a consistent structure."""
    name = str(row.get("name", "")).strip() or "New asset"
    try:
        asset_type = AssetType(str(row.get("type", AssetType.ETF.value)))
    except ValueError:
        asset_type = AssetType.ETF
    current_value_raw = row.get("current_value")
    if current_value_raw in (None, ""):
        current_value = 0.0
    else:
        current_value = _coerce_float(
            current_value_raw, "assets.current_value"
        )
    current_value = max(current_value, 0.0)
    rate_value = row.get("annual_gain_rate_pct")
    if rate_value in (None, ""):
        annual_gain_rate_pct = _default_gain_pct(asset_type)
    else:
        annual_gain_rate_pct = _coerce_float(
            rate_value, "assets.annual_gain_rate_pct"
        )
    monthly_contribution_raw = row.get("monthly_contribution")
    if monthly_contribution_raw in (None, ""):
        monthly_contribution = 0.0
    else:
        monthly_contribution = _coerce_float(
            monthly_contribution_raw, "assets.monthly_contribution"
        )
    unrealized_gains_raw = row.get("unrealized_gains")
    if unrealized_gains_raw in (None, ""):
        unrealized_gains = 0.0
    else:
        unrealized_gains = _coerce_float(
            unrealized_gains_raw, "assets.unrealized_gains"
        )
    unrealized_gains = max(min(unrealized_gains, current_value), 0.0)
    strategy_value = row.get("bav_strategy", BAVStrategy.TRANSFER.value)
    try:
        bav_strategy = BAVStrategy(str(strategy_value)).value
    except ValueError:
        bav_strategy = BAVStrategy.TRANSFER.value
    start_age_raw = row.get("bav_transfer_start_age")
    if start_age_raw in (None, ""):
        bav_transfer_start_age = 67
    else:
        bav_transfer_start_age = max(
            _coerce_int(start_age_raw, "assets.bav_transfer_start_age"), 0
        )
    end_age_raw = row.get("bav_transfer_end_age")
    if end_age_raw in (None, ""):
        bav_transfer_end_age = 72
    else:
        bav_transfer_end_age = max(
            _coerce_int(end_age_raw, "assets.bav_transfer_end_age"), 0
        )
    ratio_raw = row.get("bav_transfer_etf_ratio_pct")
    if ratio_raw in (None, ""):
        bav_transfer_etf_ratio_pct = 50.0
    else:
        bav_transfer_etf_ratio_pct = _coerce_float(
            ratio_raw, "assets.bav_transfer_etf_ratio_pct"
        )
    bav_transfer_etf_ratio_pct = max(
        min(bav_transfer_etf_ratio_pct, 100.0), 0.0
    )
    return {
        "name": name,
        "type": asset_type.value,
        "current_value": current_value,
        "unrealized_gains": unrealized_gains,
        "annual_gain_rate_pct": annual_gain_rate_pct,
        "monthly_contribution": monthly_contribution,
        "bav_strategy": bav_strategy,
        "bav_transfer_start_age": bav_transfer_start_age,
        "bav_transfer_end_age": bav_transfer_end_age,
        "bav_transfer_etf_ratio_pct": bav_transfer_etf_ratio_pct,
    }


def _load_asset_rows(
    cached_state: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Load asset rows from cached state or fall back to defaults."""
    if not cached_state:
        return _default_asset_rows()
    raw_assets = cached_state.get("assets")
    if raw_assets is None:
        return _default_asset_rows()
    if not isinstance(raw_assets, list):
        raise ValueError("Cached assets must be a list")
    rows: list[dict[str, Any]] = []
    for row in raw_assets:
        if not isinstance(row, dict):
            raise ValueError("Cached asset rows must be objects")
        rows.append(_normalize_asset_row(row))
    if not rows:
        raise ValueError("Cached assets must not be empty")
    return rows


def _load_profile_state(cached_state: dict[str, Any] | None) -> dict[str, Any]:
    """Load profile state from cached data or fall back to defaults."""
    profile_state = _default_profile_state()
    if not cached_state:
        return profile_state
    raw_profile = cached_state.get("profile")
    if raw_profile is None:
        return profile_state
    if not isinstance(raw_profile, dict):
        raise ValueError("Cached profile must be an object")
    if raw_profile.get("current_age_years") not in (None, ""):
        profile_state["current_age_years"] = _coerce_int(
            raw_profile.get("current_age_years"), "profile.current_age_years"
        )
    if raw_profile.get("current_age_months") not in (None, ""):
        profile_state["current_age_months"] = _coerce_int(
            raw_profile.get("current_age_months"), "profile.current_age_months"
        )
    if raw_profile.get("retirement_age") not in (None, ""):
        profile_state["retirement_age"] = _coerce_int(
            raw_profile.get("retirement_age"), "profile.retirement_age"
        )
    if raw_profile.get("end_age") not in (None, ""):
        profile_state["end_age"] = _coerce_int(
            raw_profile.get("end_age"), "profile.end_age"
        )
    if "currency" in raw_profile:
        profile_state["currency"] = str(raw_profile.get("currency") or "EUR")
    if raw_profile.get("average_inflation_rate_pct") not in (None, ""):
        profile_state["average_inflation_rate_pct"] = _coerce_float(
            raw_profile.get("average_inflation_rate_pct"),
            "profile.average_inflation_rate_pct",
        )
    if raw_profile.get("annual_income") not in (None, ""):
        profile_state["annual_income"] = _coerce_float(
            raw_profile.get("annual_income"), "profile.annual_income"
        )
    return profile_state


def _load_withdrawal_state(
    cached_state: dict[str, Any] | None,
) -> dict[str, Any]:
    """Load withdrawal state from cached data or fall back to defaults."""
    withdrawal_state = _default_withdrawal_state()
    if not cached_state:
        return withdrawal_state
    raw_withdrawal = cached_state.get("withdrawal")
    if raw_withdrawal is None:
        return withdrawal_state
    if not isinstance(raw_withdrawal, dict):
        raise ValueError("Cached withdrawal must be an object")
    if raw_withdrawal.get("monthly_withdrawal") not in (None, ""):
        withdrawal_state["monthly_withdrawal"] = _coerce_float(
            raw_withdrawal.get("monthly_withdrawal"),
            "withdrawal.monthly_withdrawal",
        )
    if raw_withdrawal.get("state_pension_current_monthly_amount") not in (
        None,
        "",
    ):
        withdrawal_state["state_pension_current_monthly_amount"] = (
            _coerce_float(
                raw_withdrawal.get("state_pension_current_monthly_amount"),
                "withdrawal.state_pension_current_monthly_amount",
            )
        )
    if raw_withdrawal.get("state_pension_growth_per_working_year") not in (
        None,
        "",
    ):
        withdrawal_state["state_pension_growth_per_working_year"] = (
            _coerce_float(
                raw_withdrawal.get("state_pension_growth_per_working_year"),
                "withdrawal.state_pension_growth_per_working_year",
            )
        )
    if raw_withdrawal.get("state_pension_start_age") not in (None, ""):
        withdrawal_state["state_pension_start_age"] = _coerce_int(
            raw_withdrawal.get("state_pension_start_age"),
            "withdrawal.state_pension_start_age",
        )
    return withdrawal_state


def _asset_from_row(row: dict[str, Any]) -> Asset:
    """Build an Asset instance from a UI row definition."""
    asset_type = AssetType(str(row.get("type")))
    rate_pct = row.get("annual_gain_rate_pct")
    annual_rate = None if rate_pct in (None, "") else float(rate_pct) / 100
    current_value = float(row.get("current_value") or 0)
    unrealized_gains = float(row.get("unrealized_gains") or 0)
    unrealized_gains = min(unrealized_gains, current_value)
    initial_cost_basis = current_value - unrealized_gains
    strategy_value = row.get("bav_strategy", BAVStrategy.TRANSFER.value)
    try:
        bav_strategy = BAVStrategy(str(strategy_value))
    except ValueError:
        bav_strategy = BAVStrategy.TRANSFER
    bav_transfer_start_age = int(row.get("bav_transfer_start_age") or 67)
    bav_transfer_end_age = int(row.get("bav_transfer_end_age") or 72)
    ratio_pct = float(row.get("bav_transfer_etf_ratio_pct") or 50.0)
    bav_transfer_etf_ratio = min(max(ratio_pct / 100, 0.0), 1.0)
    return Asset(
        name=str(row.get("name", "")).strip(),
        asset_type=asset_type,
        current_value=current_value,
        initial_cost_basis=initial_cost_basis,
        annual_gain_rate=annual_rate,
        monthly_contribution=float(row.get("monthly_contribution") or 0),
        bav_strategy=bav_strategy,
        bav_transfer_start_age=bav_transfer_start_age,
        bav_transfer_end_age=bav_transfer_end_age,
        bav_transfer_etf_ratio=bav_transfer_etf_ratio,
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
            if current_row.get("bav_strategy") in (None, ""):
                current_row["bav_strategy"] = BAVStrategy.TRANSFER.value
            if current_row.get("bav_transfer_start_age") in (None, ""):
                current_row["bav_transfer_start_age"] = 67
            if current_row.get("bav_transfer_end_age") in (None, ""):
                current_row["bav_transfer_end_age"] = 72
            if current_row.get("bav_transfer_etf_ratio_pct") in (None, ""):
                current_row["bav_transfer_etf_ratio_pct"] = 50.0
        if field == "bav_strategy":
            try:
                value = BAVStrategy(str(value)).value
            except ValueError:
                value = BAVStrategy.TRANSFER.value
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
        if field in {"type", "bav_strategy"}:
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
                "bav_strategy": BAVStrategy.TRANSFER.value,
                "bav_transfer_start_age": 67,
                "bav_transfer_end_age": 72,
                "bav_transfer_etf_ratio_pct": 50.0,
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
                default_withdrawal_state["state_pension_growth_per_working_year"],
                default_profile_state["currency"],
            )
            + " p.m."
        )
        state_pension_growth_display.update()
        # Reset penalty display to empty (no penalty by default at retirement age 67)
        try:
            state_pension_penalty_display.text = ""
            state_pension_penalty_display.update()
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
                            asset_type = AssetType(str(row.get("type")))
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
                            if asset_type == AssetType.BAV:
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
                                            i, "bav_strategy", e.value
                                        )
                                    ),
                                ).classes("w-48")
                                if row.get("bav_strategy") == (
                                    BAVStrategy.TRANSFER.value
                                ):
                                    ui.number(
                                        label="Transfer start age",
                                        value=row.get(
                                            "bav_transfer_start_age", 67
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
                                            "bav_transfer_end_age", 72
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
                                            "bav_transfer_etf_ratio_pct", 50.0
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
                            ui.number(
                                label="Current value",
                                value=row["current_value"],
                                format="%.0f",
                                min=0,
                                step=10000,
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
                                step=10000,
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

            with ui.row().classes("gap-2"):
                ui.button("Add asset", on_click=add_asset_row).props(
                    "outline color=green-4"
                )
                ui.button("Reset", on_click=reset_state).props(
                    "outline color=red"
                )

        with ui.card().classes("w-full p-3"):
            ui.label("Profile").classes("text-lg font-semibold")
            with ui.grid(columns=9).classes("w-full gap-3"):
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
                annual_income = ui.number(
                    label="Annual income",
                    value=profile_state.get("annual_income", 50000.0),
                    format="%.0f",
                    min=0,
                    step=1000,
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
                        withdrawal_state["state_pension_growth_per_working_year"],
                        profile_state["currency"],
                    )
                    + " p.m."
                )
                # Read-only display for estimated early-retirement penalty at pension start
                state_pension_penalty_display = ui.label("")
                state_pension_start_age = ui.number(
                    label="State pension start age",
                    value=withdrawal_state["state_pension_start_age"],
                    format="%.0f",
                    min=63,
                    max=67,
                    step=1,
                    on_change=lambda _: schedule_forecast(),
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
                # Compute state pension growth per working year from configured DRV values
                config = get_config()
                annual_income_value = float(annual_income.value or 0)
                points_per_year = min(
                    annual_income_value / config.drv.durchschnitts_jahresentgelt_euro,
                    config.drv.maximale_rentenpunkte_pro_jahr,
                )
                monthly_growth_per_working_year_computed = (
                    points_per_year * config.drv.rente_pro_rentenpunkt_euro
                )
                # Update read-only display
                try:
                    state_pension_growth_display.text = (
                        _format_currency(
                            monthly_growth_per_working_year_computed,
                            profile.currency,
                        )
                        + " p.m."
                    )
                    state_pension_growth_display.update()
                    # Compute estimated early-retirement penalty at pension start (display-only)
                    pension_start_age = int(state_pension_start_age.value or 67)
                    years_early = max(0, 67 - pension_start_age)
                    penalty_fraction = (
                        config.drv.rentenabschlag_pro_jahr * years_early
                    )
                    penalty_monthly = monthly_growth_per_working_year_computed * (
                        penalty_fraction
                    )
                    if years_early > 0:
                        state_pension_penalty_display.text = (
                            "Estimated early-retirement penalty: -" 
                            + _format_currency(penalty_monthly, profile.currency)
                            + f" p.m. ({penalty_fraction * 100:.1f}% reduction)"
                        )
                    else:
                        state_pension_penalty_display.text = "No early-retirement penalty"
                    state_pension_penalty_display.update()
                except Exception:
                    # UI not yet initialized; ignore
                    pass

                withdrawal = WithdrawalPlan(
                    monthly_withdrawal=float(withdrawal_input.value or 0),
                    state_pension=StatePension(
                        current_monthly_amount=float(
                            state_pension_current_monthly_amount.value or 0
                        ),
                        monthly_growth_per_working_year=float(
                            monthly_growth_per_working_year_computed
                        ),
                        start_age=int(state_pension_start_age.value or 67),
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
