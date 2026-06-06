"""Golden (characterization) tests pinning forecast_wealth output.

These tests hash the full monthly forecast frame for representative scenarios so
that refactors of the engine can be proven behavior-preserving. If the engine's
numbers change intentionally, regenerate the expected signatures below.
"""

from __future__ import annotations

import hashlib

import pandas as pd

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


def _signature(df: pd.DataFrame) -> tuple[str, int]:
    """Return a stable (hash, row-count) signature of a forecast frame.

    Floats are rounded to cents before hashing so the signature is robust to
    sub-cent floating-point noise but sensitive to any real change.
    """
    rounded = df.copy()
    for column in rounded.select_dtypes("float").columns:
        rounded[column] = rounded[column].round(2)
    digest = hashlib.sha256(rounded.to_csv(index=False).encode()).hexdigest()
    return digest[:16], len(df)


def test_golden_default_scenario() -> None:
    profile = UserProfile(current_age_years=40, retirement_age=67, end_age=100)
    assets = [
        Asset(
            "ETF MSCI World",
            AssetType.ETF,
            100_000.0,
            monthly_contribution=500.0,
        ),
        Asset(
            "bAV",
            AssetType.BAV,
            20_000.0,
            monthly_contribution=100.0,
            bav_strategy=BAVStrategy.TRANSFER,
            bav_retirement_age=67,
            bav_transfer_etf_ratio=0.5,
        ),
        Asset("Daily account", AssetType.CASH, 50_000.0),
    ]
    result = forecast_wealth(
        profile, assets, WithdrawalPlan(monthly_withdrawal=3000.0)
    )
    assert _signature(result) == ("834d745498418440", 721)


def test_golden_bav_income_scenario() -> None:
    profile = UserProfile(current_age_years=40, retirement_age=67, end_age=100)
    assets = [
        Asset("ETF", AssetType.ETF, 100_000.0, monthly_contribution=300.0),
        Asset(
            "bAV inc",
            AssetType.BAV,
            50_000.0,
            bav_strategy=BAVStrategy.INCOME,
            bav_retirement_age=67,
        ),
        Asset("Cash", AssetType.CASH, 20_000.0),
    ]
    result = forecast_wealth(
        profile, assets, WithdrawalPlan(monthly_withdrawal=2000.0)
    )
    assert _signature(result) == ("db6339c7eb4ac93c", 721)


def test_golden_inheritance_and_pension_scenario() -> None:
    profile = UserProfile(current_age_years=40, retirement_age=67, end_age=100)
    assets = [
        Asset("ETF", AssetType.ETF, 80_000.0, monthly_contribution=400.0),
        Asset("Cash", AssetType.CASH, 30_000.0),
        Asset(
            "Erbe",
            AssetType.INHERITANCE,
            0.0,
            inheritance_gross_amount=600_000.0,
            inheritance_age=70,
            inheritance_relationship=InheritanceRelationship.KIND,
        ),
    ]
    withdrawal = WithdrawalPlan(
        monthly_withdrawal=2500.0,
        state_pension=StatePension(
            current_monthly_amount=1200.0,
            monthly_growth_per_working_year=30.0,
            start_age=65,
        ),
    )
    result = forecast_wealth(profile, assets, withdrawal)
    assert _signature(result) == ("51c8c204b34b4f06", 721)


def test_golden_inactive_asset_and_fractional_start_age() -> None:
    profile = UserProfile(
        current_age_years=35,
        current_age_months=4,
        retirement_age=63,
        end_age=90,
    )
    assets = [
        Asset("ETF", AssetType.ETF, 50_000.0, monthly_contribution=600.0),
        Asset("ETF off", AssetType.ETF, 99_000.0, active=False),
        Asset("Cash", AssetType.CASH, 10_000.0),
        Asset(
            "bAV",
            AssetType.BAV,
            15_000.0,
            monthly_contribution=50.0,
            bav_strategy=BAVStrategy.TRANSFER,
            bav_retirement_age=63,
            bav_transfer_etf_ratio=0.5,
        ),
    ]
    result = forecast_wealth(
        profile, assets, WithdrawalPlan(monthly_withdrawal=1500.0)
    )
    assert _signature(result) == ("8df1c9224a8352fa", 657)
