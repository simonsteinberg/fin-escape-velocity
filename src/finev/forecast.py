"""Forecast engine for monthly wealth projections."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd

from finev.models import (
    Asset,
    AssetType,
    UserProfile,
    WithdrawalPlan,
)

ETF_TAX_RATE = 0.2625
ETF_TAXABLE_SHARE = 0.70


@dataclass(frozen=True)
class ForecastMetadata:
    """Derived timeline boundaries for the forecast.

    Attributes:
        start_age_months: Age in months at forecast start.
        end_age_months: Age in months at forecast end.
        retirement_age_months: Retirement age in months.
    """

    start_age_months: int
    end_age_months: int
    retirement_age_months: int


def _annual_to_monthly_rate(annual_rate: float) -> float:
    """Convert an annual rate to an effective monthly rate.

    Args:
        annual_rate: Annual rate as a decimal fraction.

    Returns:
        Effective monthly rate as a decimal fraction.
    """
    return (1 + annual_rate) ** (1 / 12) - 1


def _validate_profile(profile: UserProfile) -> ForecastMetadata:
    """Validate user profile inputs and derive timeline metadata.

    Args:
        profile: User profile values for the forecast.

    Returns:
        Derived metadata used to build the monthly timeline.

    Raises:
        ValueError: If any profile input is invalid.
    """
    if profile.current_age_years < 0:
        raise ValueError("Current age must be non-negative")
    if not 0 <= profile.current_age_months <= 11:
        raise ValueError("Current age months must be between 0 and 11")
    if profile.retirement_age < 0:
        raise ValueError("Retirement age must be non-negative")
    if profile.end_age <= 0:
        raise ValueError("End age must be positive")
    if profile.end_age < profile.retirement_age:
        raise ValueError("End age must be at or after retirement age")

    start_age_months = (
        profile.current_age_years * 12 + profile.current_age_months
    )
    end_age_months = profile.end_age * 12
    retirement_age_months = profile.retirement_age * 12

    if end_age_months <= start_age_months:
        raise ValueError("End age must be after current age")

    return ForecastMetadata(
        start_age_months=start_age_months,
        end_age_months=end_age_months,
        retirement_age_months=retirement_age_months,
    )


def _validate_assets(assets: Iterable[Asset]) -> list[Asset]:
    """Validate asset inputs and normalize into a list.

    Args:
        assets: Iterable of asset definitions.

    Returns:
        Normalized list of assets.

    Raises:
        ValueError: If assets are missing or invalid.
    """
    assets_list = list(assets)
    if not assets_list:
        raise ValueError("At least one asset is required")

    seen_names: set[str] = set()
    for asset in assets_list:
        name = asset.name.strip()
        if not name:
            raise ValueError("Asset name must not be empty")
        normalized = name.casefold()
        if normalized in seen_names:
            raise ValueError(f"Duplicate asset name: {asset.name}")
        seen_names.add(normalized)

        if asset.current_value < 0:
            raise ValueError(
                f"Asset '{asset.name}' current value must be non-negative"
            )
        if asset.monthly_contribution < 0:
            raise ValueError(
                f"Asset '{asset.name}' monthly contribution must be non-negative"
            )
        if asset.annual_gain_rate is not None and asset.annual_gain_rate <= -1:
            raise ValueError(
                f"Asset '{asset.name}' annual gain rate must be greater than -100%"
            )
        if (
            asset.initial_cost_basis is not None
            and asset.initial_cost_basis < 0
        ):
            raise ValueError(
                f"Asset '{asset.name}' cost basis must be non-negative"
            )

    return assets_list


def _validate_withdrawal(withdrawal: WithdrawalPlan) -> None:
    """Validate withdrawal configuration.

    Args:
        withdrawal: Withdrawal plan configuration.

    Raises:
        ValueError: If the withdrawal plan is invalid.
    """
    if withdrawal.monthly_withdrawal < 0:
        raise ValueError("Monthly withdrawal must be non-negative")
    if withdrawal.allocation_strategy != "proportional":
        raise ValueError(
            "Only proportional withdrawal allocation is supported"
        )


def forecast_wealth(
    profile: UserProfile,
    assets: Iterable[Asset],
    withdrawal: WithdrawalPlan | None = None,
) -> pd.DataFrame:
    """Forecast monthly balances per asset and total.

    Args:
        profile: User profile values for the forecast.
        assets: Asset definitions and cashflows.
        withdrawal: Withdrawal configuration after retirement.

    Returns:
        DataFrame with monthly balances, net cashflow, taxes, and totals.

    Raises:
        ValueError: If inputs are invalid.
    """
    metadata = _validate_profile(profile)
    assets_list = _validate_assets(assets)
    withdrawal = withdrawal or WithdrawalPlan()
    _validate_withdrawal(withdrawal)

    months = metadata.end_age_months - metadata.start_age_months
    monthly_rates = [
        _annual_to_monthly_rate(asset.effective_annual_gain_rate())
        for asset in assets_list
    ]
    balances = [float(asset.current_value) for asset in assets_list]
    cost_bases = [float(asset.effective_cost_basis()) for asset in assets_list]

    rows: list[dict[str, float | int]] = []
    for month_index in range(months + 1):
        age_months = metadata.start_age_months + month_index
        age_years = age_months // 12
        age_month_in_year = age_months % 12

        net_cashflow = 0.0
        taxes = 0.0
        if month_index > 0:
            if age_months < metadata.retirement_age_months:
                contributions = [
                    float(asset.monthly_contribution) for asset in assets_list
                ]
                balances = [
                    balance + contribution
                    for balance, contribution in zip(balances, contributions)
                ]
                cost_bases = [
                    cost_basis + contribution
                    for cost_basis, contribution in zip(
                        cost_bases, contributions
                    )
                ]
                net_cashflow = float(sum(contributions))
            else:
                withdrawal_amount = float(withdrawal.monthly_withdrawal)
                total_balance = float(sum(balances))
                if withdrawal_amount > 0 and total_balance > 0:
                    actual_withdrawn = min(withdrawal_amount, total_balance)
                    new_balances: list[float] = []
                    new_cost_bases: list[float] = []
                    for asset, balance, cost_basis in zip(
                        assets_list, balances, cost_bases
                    ):
                        if balance <= 0:
                            new_balances.append(0.0)
                            new_cost_bases.append(max(cost_basis, 0.0))
                            continue

                        asset_withdrawal = actual_withdrawn * (
                            balance / total_balance
                        )
                        withdrawal_ratio = asset_withdrawal / balance
                        new_balance = max(balance - asset_withdrawal, 0.0)
                        cost_basis_reduction = cost_basis * withdrawal_ratio
                        new_cost_basis = max(
                            cost_basis - cost_basis_reduction, 0.0
                        )

                        if asset.asset_type == AssetType.ETF:
                            gains = balance - cost_basis
                            if gains > 0:
                                gains_portion = asset_withdrawal * (
                                    gains / balance
                                )
                                taxable_gains = (
                                    gains_portion * ETF_TAXABLE_SHARE
                                )
                                taxes += taxable_gains * ETF_TAX_RATE

                        new_balances.append(new_balance)
                        new_cost_bases.append(new_cost_basis)

                    balances = new_balances
                    cost_bases = new_cost_bases
                    net_cashflow = -actual_withdrawn + taxes

            balances = [
                balance * (1 + rate)
                for balance, rate in zip(balances, monthly_rates)
            ]

        row: dict[str, float | int] = {
            "month_index": month_index,
            "age_years": int(age_years),
            "age_months": int(age_month_in_year),
            "net_cashflow": float(net_cashflow),
            "taxes": float(taxes),
        }
        for asset, balance in zip(assets_list, balances):
            row[asset.name] = float(balance)
        row["total"] = float(sum(balances))
        rows.append(row)

    return pd.DataFrame(rows)
