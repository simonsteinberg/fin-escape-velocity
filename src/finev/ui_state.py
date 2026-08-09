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

from finev.config import get_config
from finev.i18n import normalize_language
from finev.models import (
    DEFAULT_ANNUAL_GAIN_RATES,
    Asset,
    AssetType,
    BAVStrategy,
    InheritanceRelationship,
    InvestmentKind,
)
from finev.ui_config import ColorScheme

#: Lower bound (in percent) for an annual rate entered on an asset row. The
#: engine rejects any rate at or below -100%, so the UI clamps just above it.
MIN_ANNUAL_RATE_PCT = -99.9

#: Pre-filled loan terms for a new financed investment row: a typical German
#: mortgage rate and a round monthly payment, so the row is a starting point
#: rather than an immediately invalid plan.
DEFAULT_INVESTMENT_INTEREST_PCT = 3.0
DEFAULT_INVESTMENT_MONTHLY_PAYMENT = 1_000.0


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
            "monthly_contribution_growth_pct": 0.0,
            "active": True,
            "notgroschen": False,
            "notgroschen_inflation_rate_pct": 0.0,
            "bav_strategy": BAVStrategy.TRANSFER.value,
            "bav_retirement_age": 67,
            "bav_transfer_etf_ratio_pct": 50.0,
        },
        {
            "name": "bAV",
            "type": AssetType.BAV.value,
            "current_value": 20_000.0,
            "unrealized_gains": 0.0,
            "annual_gain_rate_pct": default_gain_pct(AssetType.BAV),
            "monthly_contribution": 100.0,
            "monthly_contribution_growth_pct": 0.0,
            "active": True,
            "notgroschen": False,
            "notgroschen_inflation_rate_pct": 0.0,
            "bav_strategy": BAVStrategy.TRANSFER.value,
            "bav_retirement_age": 67,
            "bav_transfer_etf_ratio_pct": 50.0,
        },
        {
            "name": "Daily account",
            "type": AssetType.CASH.value,
            "current_value": 50_000.0,
            "unrealized_gains": 0.0,
            "annual_gain_rate_pct": default_gain_pct(AssetType.CASH),
            "monthly_contribution": 0.0,
            "monthly_contribution_growth_pct": 0.0,
            "active": True,
            "notgroschen": False,
            "notgroschen_inflation_rate_pct": 0.0,
            "bav_strategy": BAVStrategy.TRANSFER.value,
            "bav_retirement_age": 67,
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
        "monthly_contribution_growth_pct": 0.0,
        "active": True,
        "notgroschen": False,
        "notgroschen_inflation_rate_pct": 0.0,
        "bav_strategy": BAVStrategy.TRANSFER.value,
        "bav_retirement_age": 67,
        "bav_transfer_etf_ratio_pct": 50.0,
        "inheritance_gross_amount": 0.0,
        "inheritance_age": 67,
        "inheritance_relationship": InheritanceRelationship.KIND.value,
        "vbl_input_mode": "points",
        "vbl_points": 0.0,
        "vbl_monthly_pension": 0.0,
        "vbl_still_working": False,
        "vbl_start_age": 67,
        "vbl_tax_rate_pct": "",
        "investment_kind": InvestmentKind.ONE_TIME.value,
        "investment_amount": 0.0,
        "investment_age": 67,
        "investment_interest_rate_pct": DEFAULT_INVESTMENT_INTEREST_PCT,
        "investment_monthly_payment": DEFAULT_INVESTMENT_MONTHLY_PAYMENT,
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


def load_language(cached_state: dict[str, Any] | None) -> str:
    """Load the persisted UI language from cached state.

    The language is a UI-wide preference stored at the top level of the cached
    state (alongside ``assets``/``profile``/``withdrawal``), so a reload restores
    the user's last choice.

    Args:
        cached_state: The loaded cache dict, or ``None`` when no cache exists.

    Returns:
        A supported language code, defaulting to English when absent or
        unrecognised (see :func:`finev.i18n.normalize_language`).
    """
    if not cached_state:
        return normalize_language(None)
    return normalize_language(cached_state.get("language"))


def load_color_scheme(
    cached_state: dict[str, Any] | None, default: ColorScheme
) -> ColorScheme:
    """Load the persisted color scheme from cached state.

    The color scheme is a UI-wide preference stored at the top level of the
    cached state (alongside ``language``), so a navbar toggle survives a reload.
    When absent or unrecognised it falls back to *default* (the value configured
    in ``ui_config.json``).

    Args:
        cached_state: The loaded cache dict, or ``None`` when no cache exists.
        default: The scheme to use when the cache carries no valid choice.

    Returns:
        The persisted scheme, or *default*.
    """
    if not cached_state:
        return default
    raw = cached_state.get("color_scheme")
    if raw is None:
        return default
    try:
        return ColorScheme(str(raw).strip().lower())
    except ValueError:
        return default


def load_log_scale(cached_state: dict[str, Any] | None) -> bool:
    """Load the persisted y-axis log-scale preference from cached state.

    Like ``language`` and ``color_scheme``, the chart's log-scale toggle is a
    UI-wide preference stored at the top level of the cached state so it
    survives a reload. Absent or non-boolean values fall back to ``False``
    (linear scale).

    Args:
        cached_state: The loaded cache dict, or ``None`` when no cache exists.

    Returns:
        ``True`` when the capital axis should use a logarithmic scale.
    """
    if not cached_state:
        return False
    return bool(cached_state.get("log_scale", False))


def default_profile_state() -> dict[str, Any]:
    """Return default profile values for UI inputs."""
    return {
        "current_age_years": 40,
        "current_age_months": 0,
        "retirement_age": 67,
        "end_age": 100,
        "currency": "EUR",
        "average_inflation_rate_pct": 2.0,
        "debt_interest_rate_pct": 8.0,
        "annual_income": 50000.0,
    }


def default_withdrawal_state() -> dict[str, Any]:
    """Return default withdrawal values for UI inputs."""
    return {
        "monthly_withdrawal": 3000.0,
        "state_pension_current_monthly_amount": 0.0,
        "state_pension_growth_per_working_year": 0.0,
        "state_pension_start_age": 67,
        "state_pension_adjustment_rate_pct": 1.0,
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
    contribution_growth_raw = row.get("monthly_contribution_growth_pct")
    if contribution_growth_raw in (None, ""):
        monthly_contribution_growth_pct = 0.0
    else:
        monthly_contribution_growth_pct = max(
            coerce_float(
                contribution_growth_raw,
                "assets.monthly_contribution_growth_pct",
            ),
            MIN_ANNUAL_RATE_PCT,
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
    retirement_age_raw = row.get("bav_retirement_age")
    if retirement_age_raw in (None, ""):
        bav_retirement_age = 67
    else:
        bav_retirement_age = max(
            coerce_int(retirement_age_raw, "assets.bav_retirement_age"), 0
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
    notgroschen_raw = row.get("notgroschen")
    if isinstance(notgroschen_raw, bool):
        notgroschen = notgroschen_raw
    elif isinstance(notgroschen_raw, (int, float)):
        notgroschen = bool(notgroschen_raw)
    elif isinstance(notgroschen_raw, str):
        notgroschen = notgroschen_raw.strip().lower() in (
            "1",
            "true",
            "yes",
            "y",
        )
    else:
        notgroschen = False
    notgroschen_rate_raw = row.get("notgroschen_inflation_rate_pct")
    if notgroschen_rate_raw in (None, ""):
        notgroschen_inflation_rate_pct = 0.0
    else:
        notgroschen_inflation_rate_pct = max(
            coerce_float(
                notgroschen_rate_raw, "assets.notgroschen_inflation_rate_pct"
            ),
            0.0,
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
    vbl_input_mode = str(row.get("vbl_input_mode", "points")).strip().lower()
    if vbl_input_mode not in ("points", "euro"):
        vbl_input_mode = "points"
    vbl_points_raw = row.get("vbl_points")
    vbl_points = (
        0.0
        if vbl_points_raw in (None, "")
        else max(coerce_float(vbl_points_raw, "assets.vbl_points"), 0.0)
    )
    vbl_pension_raw = row.get("vbl_monthly_pension")
    vbl_monthly_pension = (
        0.0
        if vbl_pension_raw in (None, "")
        else max(
            coerce_float(vbl_pension_raw, "assets.vbl_monthly_pension"), 0.0
        )
    )
    vbl_still_working_raw = row.get("vbl_still_working")
    if isinstance(vbl_still_working_raw, bool):
        vbl_still_working = vbl_still_working_raw
    elif isinstance(vbl_still_working_raw, (int, float)):
        vbl_still_working = bool(vbl_still_working_raw)
    elif isinstance(vbl_still_working_raw, str):
        vbl_still_working = vbl_still_working_raw.strip().lower() in (
            "1",
            "true",
            "yes",
            "y",
        )
    else:
        vbl_still_working = False
    vbl_start_age_raw = row.get("vbl_start_age")
    vbl_start_age = (
        67
        if vbl_start_age_raw in (None, "")
        else max(coerce_int(vbl_start_age_raw, "assets.vbl_start_age"), 0)
    )
    vbl_tax_raw = row.get("vbl_tax_rate_pct")
    if vbl_tax_raw in (None, ""):
        vbl_tax_rate_pct: float | str = ""
    else:
        vbl_tax_rate_pct = max(
            min(coerce_float(vbl_tax_raw, "assets.vbl_tax_rate_pct"), 100.0),
            0.0,
        )
    investment_kind_raw = row.get(
        "investment_kind", InvestmentKind.ONE_TIME.value
    )
    try:
        investment_kind = InvestmentKind(str(investment_kind_raw)).value
    except ValueError:
        investment_kind = InvestmentKind.ONE_TIME.value
    investment_amount_raw = row.get("investment_amount")
    investment_amount = (
        0.0
        if investment_amount_raw in (None, "")
        else max(
            coerce_float(investment_amount_raw, "assets.investment_amount"),
            0.0,
        )
    )
    investment_age_raw = row.get("investment_age")
    investment_age = (
        67
        if investment_age_raw in (None, "")
        else max(coerce_int(investment_age_raw, "assets.investment_age"), 0)
    )
    investment_interest_raw = row.get("investment_interest_rate_pct")
    investment_interest_rate_pct = (
        DEFAULT_INVESTMENT_INTEREST_PCT
        if investment_interest_raw in (None, "")
        else max(
            coerce_float(
                investment_interest_raw, "assets.investment_interest_rate_pct"
            ),
            0.0,
        )
    )
    investment_payment_raw = row.get("investment_monthly_payment")
    investment_monthly_payment = (
        DEFAULT_INVESTMENT_MONTHLY_PAYMENT
        if investment_payment_raw in (None, "")
        else max(
            coerce_float(
                investment_payment_raw, "assets.investment_monthly_payment"
            ),
            0.0,
        )
    )
    return {
        "name": name,
        "type": asset_type.value,
        "current_value": current_value,
        "unrealized_gains": unrealized_gains,
        "annual_gain_rate_pct": annual_gain_rate_pct,
        "monthly_contribution": monthly_contribution,
        "monthly_contribution_growth_pct": monthly_contribution_growth_pct,
        "active": active,
        "notgroschen": notgroschen,
        "notgroschen_inflation_rate_pct": notgroschen_inflation_rate_pct,
        "bav_strategy": bav_strategy,
        "bav_retirement_age": bav_retirement_age,
        "bav_transfer_etf_ratio_pct": bav_transfer_etf_ratio_pct,
        "inheritance_gross_amount": inheritance_gross_amount,
        "inheritance_age": inheritance_age,
        "inheritance_relationship": inheritance_relationship,
        "vbl_input_mode": vbl_input_mode,
        "vbl_points": vbl_points,
        "vbl_monthly_pension": vbl_monthly_pension,
        "vbl_still_working": vbl_still_working,
        "vbl_start_age": vbl_start_age,
        "vbl_tax_rate_pct": vbl_tax_rate_pct,
        "investment_kind": investment_kind,
        "investment_amount": investment_amount,
        "investment_age": investment_age,
        "investment_interest_rate_pct": investment_interest_rate_pct,
        "investment_monthly_payment": investment_monthly_payment,
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
    if raw_profile.get("debt_interest_rate_pct") not in (None, ""):
        profile_state["debt_interest_rate_pct"] = coerce_float(
            raw_profile.get("debt_interest_rate_pct"),
            "profile.debt_interest_rate_pct",
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
    if raw_withdrawal.get("state_pension_adjustment_rate_pct") not in (
        None,
        "",
    ):
        withdrawal_state["state_pension_adjustment_rate_pct"] = coerce_float(
            raw_withdrawal.get("state_pension_adjustment_rate_pct"),
            "withdrawal.state_pension_adjustment_rate_pct",
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

    if asset_type == AssetType.INVESTMENT:
        try:
            kind = InvestmentKind(
                str(row.get("investment_kind", InvestmentKind.ONE_TIME.value))
            )
        except ValueError:
            kind = InvestmentKind.ONE_TIME
        return Asset(
            name=name,
            asset_type=asset_type,
            current_value=0.0,
            active=active,
            investment_kind=kind,
            # An inactive purchase is zeroed rather than validated away, so a
            # hidden what-if row can never block the forecast.
            investment_amount=float(row.get("investment_amount") or 0)
            if active
            else 0.0,
            investment_age=int(row.get("investment_age") or 67),
            investment_interest_rate=float(
                row.get("investment_interest_rate_pct") or 0
            )
            / 100,
            investment_monthly_payment=float(
                row.get("investment_monthly_payment") or 0
            ),
        )

    if asset_type == AssetType.VBL_KLASSIK:
        point_value = get_config().vbl.rente_pro_punkt_euro
        input_mode = str(row.get("vbl_input_mode", "points")).strip().lower()
        if input_mode == "euro":
            monthly_pension = float(row.get("vbl_monthly_pension") or 0)
        else:
            monthly_pension = float(row.get("vbl_points") or 0) * point_value
        still_working = bool(row.get("vbl_still_working", False))
        # The "still in public service" option earns one Versorgungspunkt per
        # working year, i.e. one point's euro value of extra monthly pension.
        growth = point_value if still_working else 0.0
        vbl_start_age = int(row.get("vbl_start_age") or 67)
        tax_pct = row.get("vbl_tax_rate_pct")
        if tax_pct is None or tax_pct == "":
            vbl_tax_rate = None
        else:
            vbl_tax_rate = float(tax_pct) / 100
        return Asset(
            name=name,
            asset_type=asset_type,
            current_value=0.0,
            active=active,
            vbl_monthly_pension=monthly_pension if active else 0.0,
            vbl_monthly_growth_per_working_year=growth if active else 0.0,
            vbl_start_age=vbl_start_age,
            vbl_tax_rate=vbl_tax_rate,
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
    bav_retirement_age = int(row.get("bav_retirement_age") or 67)
    ratio_pct = float(row.get("bav_transfer_etf_ratio_pct") or 50.0)
    bav_transfer_etf_ratio = min(max(ratio_pct / 100, 0.0), 1.0)
    is_cash = asset_type == AssetType.CASH
    contribution_growth_pct = max(
        float(row.get("monthly_contribution_growth_pct") or 0),
        MIN_ANNUAL_RATE_PCT,
    )
    return Asset(
        name=name,
        asset_type=asset_type,
        current_value=current_value if active else 0.0,
        initial_cost_basis=initial_cost_basis if active else 0.0,
        annual_gain_rate=annual_rate,
        monthly_contribution=float(row.get("monthly_contribution") or 0)
        if active
        else 0.0,
        monthly_contribution_growth_rate=contribution_growth_pct / 100,
        active=active,
        # Only a Cash row can be a buffer; a stale flag left on a row whose
        # type was switched is dropped rather than rejected by the engine.
        notgroschen=is_cash and bool(row.get("notgroschen", False)),
        notgroschen_inflation_rate=(
            float(row.get("notgroschen_inflation_rate_pct") or 0) / 100
            if is_cash
            else 0.0
        ),
        bav_strategy=bav_strategy,
        bav_retirement_age=bav_retirement_age,
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
        if row.get("monthly_contribution_growth_pct") in (None, ""):
            row["monthly_contribution_growth_pct"] = 0.0
        if row.get("notgroschen") is None:
            row["notgroschen"] = False
        if row.get("notgroschen_inflation_rate_pct") in (None, ""):
            row["notgroschen_inflation_rate_pct"] = 0.0
        if row.get("bav_strategy") in (None, ""):
            row["bav_strategy"] = BAVStrategy.TRANSFER.value
        if row.get("bav_retirement_age") in (None, ""):
            row["bav_retirement_age"] = 67
        if row.get("bav_transfer_etf_ratio_pct") in (None, ""):
            row["bav_transfer_etf_ratio_pct"] = 50.0
    if row.get("inheritance_gross_amount") in (None, ""):
        row["inheritance_gross_amount"] = 0.0
    if row.get("inheritance_age") in (None, ""):
        row["inheritance_age"] = 67
    if row.get("inheritance_relationship") in (None, ""):
        row["inheritance_relationship"] = InheritanceRelationship.KIND.value
    if row.get("vbl_input_mode") in (None, ""):
        row["vbl_input_mode"] = "points"
    if row.get("vbl_points") in (None, ""):
        row["vbl_points"] = 0.0
    if row.get("vbl_monthly_pension") in (None, ""):
        row["vbl_monthly_pension"] = 0.0
    if row.get("vbl_still_working") is None:
        row["vbl_still_working"] = False
    if row.get("vbl_start_age") in (None, ""):
        row["vbl_start_age"] = 67
    if "vbl_tax_rate_pct" not in row:
        row["vbl_tax_rate_pct"] = ""
    if row.get("investment_kind") in (None, ""):
        row["investment_kind"] = InvestmentKind.ONE_TIME.value
    if row.get("investment_amount") in (None, ""):
        row["investment_amount"] = 0.0
    if row.get("investment_age") in (None, ""):
        row["investment_age"] = 67
    if row.get("investment_interest_rate_pct") in (None, ""):
        row["investment_interest_rate_pct"] = DEFAULT_INVESTMENT_INTEREST_PCT
    if row.get("investment_monthly_payment") in (None, ""):
        row["investment_monthly_payment"] = DEFAULT_INVESTMENT_MONTHLY_PAYMENT


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
    if field == "notgroschen":
        return bool(value)
    if field == "notgroschen_inflation_rate_pct":
        return max(float(value or 0), 0.0)
    if field == "monthly_contribution_growth_pct":
        return max(float(value or 0), MIN_ANNUAL_RATE_PCT)
    if field == "unrealized_gains":
        current_value = float(row.get("current_value") or 0)
        return max(min(float(value or 0), current_value), 0.0)
    if field == "bav_retirement_age":
        return max(int(value or 0), 0)
    if field == "bav_transfer_etf_ratio_pct":
        return max(min(float(value or 0), 100.0), 0.0)
    if field == "vbl_input_mode":
        return str(value) if str(value) in ("points", "euro") else "points"
    if field in ("vbl_points", "vbl_monthly_pension"):
        return max(float(value or 0), 0.0)
    if field == "vbl_still_working":
        return bool(value)
    if field == "vbl_start_age":
        return max(int(value or 0), 0)
    if field == "investment_kind":
        try:
            return InvestmentKind(str(value)).value
        except ValueError:
            return InvestmentKind.ONE_TIME.value
    if field in (
        "investment_amount",
        "investment_interest_rate_pct",
        "investment_monthly_payment",
    ):
        return max(float(value or 0), 0.0)
    if field == "investment_age":
        return max(int(value or 0), 0)
    if field == "vbl_tax_rate_pct":
        if value in (None, ""):
            return ""
        return max(min(float(value), 100.0), 0.0)
    return value
