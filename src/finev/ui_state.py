"""UI state: defaults, persistence, coercion, and row-to-model conversion.

Pure helpers backing the wealth forecast page. They have no NiceGUI dependency,
so the data handling can be unit-tested without rendering a page. The NiceGUI
layer (:mod:`finev.ui`) reads and writes the dictionaries these produce and
turns rows into :class:`~finev.models.Asset` instances via
:func:`asset_from_row`.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from finev.models import (
    DEFAULT_ANNUAL_GAIN_RATES,
    Asset,
    AssetType,
    BAVStrategy,
    InheritanceRelationship,
)


def default_gain_pct(asset_type: AssetType) -> float:
    """Return the default annual gain percentage for an asset type."""
    return DEFAULT_ANNUAL_GAIN_RATES[asset_type] * 100


def default_asset_rows() -> list[dict[str, Any]]:
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
            "annual_gain_rate_pct": default_gain_pct(AssetType.ETF),
            "monthly_contribution": 500.0,
            "active": True,
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
            "annual_gain_rate_pct": default_gain_pct(AssetType.BAV),
            "monthly_contribution": 100.0,
            "active": True,
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
            "annual_gain_rate_pct": default_gain_pct(AssetType.CASH),
            "monthly_contribution": 0.0,
            "active": True,
            "bav_strategy": BAVStrategy.TRANSFER.value,
            "bav_transfer_start_age": 67,
            "bav_transfer_end_age": 72,
            "bav_transfer_etf_ratio_pct": 50.0,
        },
    ]


def new_asset_row() -> dict[str, Any]:
    """Return a blank asset row with sensible defaults (for 'Add asset')."""
    return {
        "name": "New asset",
        "type": AssetType.ETF.value,
        "current_value": 0.0,
        "unrealized_gains": 0.0,
        "annual_gain_rate_pct": default_gain_pct(AssetType.ETF),
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


def state_path() -> Path:
    """Return the cache path for persisted UI state."""
    env_path = os.getenv("WEALTH_APP_STATE_PATH")
    if env_path:
        return Path(env_path).expanduser()
    repo_root = Path(__file__).resolve().parents[2]
    return repo_root / ".cache" / "finev" / "wealth_state.json"


def load_cached_state() -> dict[str, Any] | None:
    """Load cached UI state from disk if present."""
    path = state_path()
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("Cached state must be a JSON object")
    return data


def save_cached_state(state: dict[str, Any]) -> None:
    """Persist UI state to disk."""
    path = state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2, sort_keys=True)


def clear_cached_state() -> None:
    """Remove the cached UI state file if it exists."""
    path = state_path()
    if path.exists():
        path.unlink()


def default_profile_state() -> dict[str, Any]:
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


def default_withdrawal_state() -> dict[str, Any]:
    """Return default withdrawal values for UI inputs."""
    return {
        "monthly_withdrawal": 3000.0,
        "state_pension_current_monthly_amount": 0.0,
        "state_pension_growth_per_working_year": 0.0,
        "state_pension_start_age": 67,
    }


def coerce_float(value: Any, field_name: str) -> float:
    """Convert a cached value to float or raise a descriptive error."""
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Cached state field '{field_name}' must be a number"
        ) from exc


def coerce_int(value: Any, field_name: str) -> int:
    """Convert a cached value to int or raise a descriptive error."""
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Cached state field '{field_name}' must be an integer"
        ) from exc


def normalize_asset_row(row: dict[str, Any]) -> dict[str, Any]:
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
        current_value = coerce_float(current_value_raw, "assets.current_value")
    current_value = max(current_value, 0.0)
    rate_value = row.get("annual_gain_rate_pct")
    if rate_value in (None, ""):
        annual_gain_rate_pct = default_gain_pct(asset_type)
    else:
        annual_gain_rate_pct = coerce_float(
            rate_value, "assets.annual_gain_rate_pct"
        )
    monthly_contribution_raw = row.get("monthly_contribution")
    if monthly_contribution_raw in (None, ""):
        monthly_contribution = 0.0
    else:
        monthly_contribution = coerce_float(
            monthly_contribution_raw, "assets.monthly_contribution"
        )
    unrealized_gains_raw = row.get("unrealized_gains")
    if unrealized_gains_raw in (None, ""):
        unrealized_gains = 0.0
    else:
        unrealized_gains = coerce_float(
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
            coerce_int(start_age_raw, "assets.bav_transfer_start_age"), 0
        )
    end_age_raw = row.get("bav_transfer_end_age")
    if end_age_raw in (None, ""):
        bav_transfer_end_age = 72
    else:
        bav_transfer_end_age = max(
            coerce_int(end_age_raw, "assets.bav_transfer_end_age"), 0
        )
    ratio_raw = row.get("bav_transfer_etf_ratio_pct")
    if ratio_raw in (None, ""):
        bav_transfer_etf_ratio_pct = 50.0
    else:
        bav_transfer_etf_ratio_pct = coerce_float(
            ratio_raw, "assets.bav_transfer_etf_ratio_pct"
        )
    bav_transfer_etf_ratio_pct = max(
        min(bav_transfer_etf_ratio_pct, 100.0), 0.0
    )
    # active flag: accept booleans, numbers, or common strings
    active_raw = row.get("active")
    if isinstance(active_raw, bool):
        active = active_raw
    elif isinstance(active_raw, (int, float)):
        active = bool(active_raw)
    elif isinstance(active_raw, str):
        active = active_raw.strip().lower() in ("1", "true", "yes", "y")
    else:
        active = True
    inheritance_gross_raw = row.get("inheritance_gross_amount")
    if inheritance_gross_raw in (None, ""):
        inheritance_gross_amount = 0.0
    else:
        inheritance_gross_amount = max(
            coerce_float(
                inheritance_gross_raw, "assets.inheritance_gross_amount"
            ),
            0.0,
        )
    inheritance_age_raw = row.get("inheritance_age")
    if inheritance_age_raw in (None, ""):
        inheritance_age = 67
    else:
        inheritance_age = max(
            coerce_int(inheritance_age_raw, "assets.inheritance_age"), 0
        )
    relationship_raw = row.get(
        "inheritance_relationship", InheritanceRelationship.KIND.value
    )
    try:
        inheritance_relationship = InheritanceRelationship(
            str(relationship_raw)
        ).value
    except ValueError:
        inheritance_relationship = InheritanceRelationship.KIND.value
    return {
        "name": name,
        "type": asset_type.value,
        "current_value": current_value,
        "unrealized_gains": unrealized_gains,
        "annual_gain_rate_pct": annual_gain_rate_pct,
        "monthly_contribution": monthly_contribution,
        "active": active,
        "bav_strategy": bav_strategy,
        "bav_transfer_start_age": bav_transfer_start_age,
        "bav_transfer_end_age": bav_transfer_end_age,
        "bav_transfer_etf_ratio_pct": bav_transfer_etf_ratio_pct,
        "inheritance_gross_amount": inheritance_gross_amount,
        "inheritance_age": inheritance_age,
        "inheritance_relationship": inheritance_relationship,
    }


def load_asset_rows(
    cached_state: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Load asset rows from cached state or fall back to defaults."""
    if not cached_state:
        return default_asset_rows()
    raw_assets = cached_state.get("assets")
    if raw_assets is None:
        return default_asset_rows()
    if not isinstance(raw_assets, list):
        raise ValueError("Cached assets must be a list")
    rows: list[dict[str, Any]] = []
    for row in raw_assets:
        if not isinstance(row, dict):
            raise ValueError("Cached asset rows must be objects")
        rows.append(normalize_asset_row(row))
    if not rows:
        raise ValueError("Cached assets must not be empty")
    return rows


def load_profile_state(cached_state: dict[str, Any] | None) -> dict[str, Any]:
    """Load profile state from cached data or fall back to defaults."""
    profile_state = default_profile_state()
    if not cached_state:
        return profile_state
    raw_profile = cached_state.get("profile")
    if raw_profile is None:
        return profile_state
    if not isinstance(raw_profile, dict):
        raise ValueError("Cached profile must be an object")
    if raw_profile.get("current_age_years") not in (None, ""):
        profile_state["current_age_years"] = coerce_int(
            raw_profile.get("current_age_years"), "profile.current_age_years"
        )
    if raw_profile.get("current_age_months") not in (None, ""):
        profile_state["current_age_months"] = coerce_int(
            raw_profile.get("current_age_months"), "profile.current_age_months"
        )
    if raw_profile.get("retirement_age") not in (None, ""):
        profile_state["retirement_age"] = coerce_int(
            raw_profile.get("retirement_age"), "profile.retirement_age"
        )
    if raw_profile.get("end_age") not in (None, ""):
        profile_state["end_age"] = coerce_int(
            raw_profile.get("end_age"), "profile.end_age"
        )
    if "currency" in raw_profile:
        profile_state["currency"] = str(raw_profile.get("currency") or "EUR")
    if raw_profile.get("average_inflation_rate_pct") not in (None, ""):
        profile_state["average_inflation_rate_pct"] = coerce_float(
            raw_profile.get("average_inflation_rate_pct"),
            "profile.average_inflation_rate_pct",
        )
    if raw_profile.get("annual_income") not in (None, ""):
        profile_state["annual_income"] = coerce_float(
            raw_profile.get("annual_income"), "profile.annual_income"
        )
    return profile_state


def load_withdrawal_state(
    cached_state: dict[str, Any] | None,
) -> dict[str, Any]:
    """Load withdrawal state from cached data or fall back to defaults."""
    withdrawal_state = default_withdrawal_state()
    if not cached_state:
        return withdrawal_state
    raw_withdrawal = cached_state.get("withdrawal")
    if raw_withdrawal is None:
        return withdrawal_state
    if not isinstance(raw_withdrawal, dict):
        raise ValueError("Cached withdrawal must be an object")
    if raw_withdrawal.get("monthly_withdrawal") not in (None, ""):
        withdrawal_state["monthly_withdrawal"] = coerce_float(
            raw_withdrawal.get("monthly_withdrawal"),
            "withdrawal.monthly_withdrawal",
        )
    if raw_withdrawal.get("state_pension_current_monthly_amount") not in (
        None,
        "",
    ):
        withdrawal_state["state_pension_current_monthly_amount"] = (
            coerce_float(
                raw_withdrawal.get("state_pension_current_monthly_amount"),
                "withdrawal.state_pension_current_monthly_amount",
            )
        )
    if raw_withdrawal.get("state_pension_growth_per_working_year") not in (
        None,
        "",
    ):
        withdrawal_state["state_pension_growth_per_working_year"] = (
            coerce_float(
                raw_withdrawal.get("state_pension_growth_per_working_year"),
                "withdrawal.state_pension_growth_per_working_year",
            )
        )
    if raw_withdrawal.get("state_pension_start_age") not in (None, ""):
        withdrawal_state["state_pension_start_age"] = coerce_int(
            raw_withdrawal.get("state_pension_start_age"),
            "withdrawal.state_pension_start_age",
        )
    return withdrawal_state


def asset_from_row(row: dict[str, Any]) -> Asset:
    """Build an Asset instance from a UI row definition."""
    asset_type = AssetType(str(row.get("type")))
    active = bool(row.get("active", True))
    name = str(row.get("name", "")).strip()

    if asset_type == AssetType.INHERITANCE:
        gross_amount = float(row.get("inheritance_gross_amount") or 0)
        inheritance_age = int(row.get("inheritance_age") or 67)
        try:
            relationship = InheritanceRelationship(
                str(
                    row.get(
                        "inheritance_relationship",
                        InheritanceRelationship.KIND.value,
                    )
                )
            )
        except ValueError:
            relationship = InheritanceRelationship.KIND
        return Asset(
            name=name,
            asset_type=asset_type,
            current_value=0.0,
            active=active,
            inheritance_gross_amount=gross_amount if active else 0.0,
            inheritance_age=inheritance_age,
            inheritance_relationship=relationship,
        )

    rate_pct = row.get("annual_gain_rate_pct")
    annual_rate: float | None
    if rate_pct is None or rate_pct == "":
        annual_rate = None
    else:
        annual_rate = float(rate_pct) / 100
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
        name=name,
        asset_type=asset_type,
        current_value=current_value if active else 0.0,
        initial_cost_basis=initial_cost_basis if active else 0.0,
        annual_gain_rate=annual_rate,
        monthly_contribution=float(row.get("monthly_contribution") or 0)
        if active
        else 0.0,
        active=active,
        bav_strategy=bav_strategy,
        bav_transfer_start_age=bav_transfer_start_age,
        bav_transfer_end_age=bav_transfer_end_age,
        bav_transfer_etf_ratio=bav_transfer_etf_ratio,
    )


def apply_type_change_defaults(
    row: dict[str, Any], new_type: AssetType
) -> None:
    """Fill in type-appropriate default fields when an asset's type changes.

    Call this *before* writing the new type onto ``row`` (it reads the previous
    type to decide whether the gain rate was left at its default and should
    therefore track the new type's default).

    Args:
        row: The asset row being edited (mutated in place).
        new_type: The asset type the row is changing to.
    """
    previous_type = AssetType(str(row.get("type")))
    if new_type != AssetType.INHERITANCE:
        current_default = (
            default_gain_pct(previous_type)
            if previous_type != AssetType.INHERITANCE
            else default_gain_pct(new_type)
        )
        if row.get("annual_gain_rate_pct") in (None, "", current_default):
            row["annual_gain_rate_pct"] = default_gain_pct(new_type)
        if row.get("unrealized_gains") in (None, ""):
            row["unrealized_gains"] = 0.0
        if row.get("bav_strategy") in (None, ""):
            row["bav_strategy"] = BAVStrategy.TRANSFER.value
        if row.get("bav_transfer_start_age") in (None, ""):
            row["bav_transfer_start_age"] = 67
        if row.get("bav_transfer_end_age") in (None, ""):
            row["bav_transfer_end_age"] = 72
        if row.get("bav_transfer_etf_ratio_pct") in (None, ""):
            row["bav_transfer_etf_ratio_pct"] = 50.0
    if row.get("inheritance_gross_amount") in (None, ""):
        row["inheritance_gross_amount"] = 0.0
    if row.get("inheritance_age") in (None, ""):
        row["inheritance_age"] = 67
    if row.get("inheritance_relationship") in (None, ""):
        row["inheritance_relationship"] = InheritanceRelationship.KIND.value


def coerce_asset_field(row: dict[str, Any], field: str, value: Any) -> Any:
    """Coerce and clamp a single edited asset-row field value.

    Args:
        row: The asset row being edited (read-only here; used to clamp
            ``unrealized_gains`` against the row's current value).
        field: The field being edited.
        value: The raw incoming value.

    Returns:
        The coerced/clamped value to store for ``field`` (unchanged for fields
        with no special handling).
    """
    if field == "bav_strategy":
        try:
            return BAVStrategy(str(value)).value
        except ValueError:
            return BAVStrategy.TRANSFER.value
    if field == "inheritance_relationship":
        try:
            return InheritanceRelationship(str(value)).value
        except ValueError:
            return InheritanceRelationship.KIND.value
    if field == "inheritance_gross_amount":
        return max(float(value or 0), 0.0)
    if field == "inheritance_age":
        return max(int(value or 0), 0)
    if field == "unrealized_gains":
        current_value = float(row.get("current_value") or 0)
        return max(min(float(value or 0), current_value), 0.0)
    if field in {"bav_transfer_start_age", "bav_transfer_end_age"}:
        return max(int(value or 0), 0)
    if field == "bav_transfer_etf_ratio_pct":
        return max(min(float(value or 0), 100.0), 0.0)
    return value
