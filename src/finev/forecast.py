"""Forecast engine for monthly wealth projections."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pandas as pd

from finev.config import get_config
from finev.models import (
    AllocationStrategy,
    Asset,
    AssetType,
    BAVStrategy,
    InheritanceRelationship,
    StatePension,
    UserProfile,
    WithdrawalPlan,
)

if TYPE_CHECKING:
    from finev.config import FinevConfig


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


def _allocate_amount(
    amount: float,
    indices: list[int],
    balances: list[float],
) -> list[tuple[int, float]]:
    """Allocate an amount across target assets by balance weight."""
    if amount <= 0 or not indices:
        return []
    total_balance = sum(balances[index] for index in indices)
    if total_balance > 0:
        return [
            (index, amount * (balances[index] / total_balance))
            for index in indices
        ]
    share = amount / len(indices)
    return [(index, share) for index in indices]


def _annual_to_monthly_rate(annual_rate: float) -> float:
    """Convert an annual rate to an effective monthly rate.

    Args:
        annual_rate: Annual rate as a decimal fraction.

    Returns:
        Effective monthly rate as a decimal fraction.
    """
    return (1 + annual_rate) ** (1 / 12) - 1


def _inflation_multiplier(
    annual_rate: float,
    months_since_start: int,
) -> float:
    """Return the cumulative inflation multiplier for a number of months.

    Args:
        annual_rate: Average annual inflation rate as a decimal fraction.
        months_since_start: Number of months since the forecast start.

    Returns:
        Inflation multiplier to apply to today's currency.
    """
    monthly_rate = _annual_to_monthly_rate(annual_rate)
    return (1 + monthly_rate) ** months_since_start


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
    if profile.average_inflation_rate <= -1:
        raise ValueError("Average inflation rate must be greater than -100%")

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

        if asset.asset_type == AssetType.INHERITANCE:
            if asset.inheritance_gross_amount < 0:
                raise ValueError(
                    f"Asset '{asset.name}' inheritance amount must be non-negative"
                )
            if asset.inheritance_age < 0:
                raise ValueError(
                    f"Asset '{asset.name}' inheritance age must be non-negative"
                )
            try:
                InheritanceRelationship(asset.inheritance_relationship)
            except ValueError as exc:
                valid = ", ".join(r.value for r in InheritanceRelationship)
                raise ValueError(
                    f"Asset '{asset.name}' inheritance relationship must be one of: "
                    f"{valid}"
                ) from exc
            continue

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
        if asset.asset_type == AssetType.BAV:
            try:
                BAVStrategy(asset.bav_strategy)
            except ValueError as exc:
                valid_strategies = ", ".join(
                    strategy.value for strategy in BAVStrategy
                )
                raise ValueError(
                    f"Asset '{asset.name}' bAV strategy must be one of: "
                    f"{valid_strategies}"
                ) from exc
            if asset.bav_transfer_start_age < 0:
                raise ValueError(
                    f"Asset '{asset.name}' bAV transfer start age must be "
                    "non-negative"
                )
            if asset.bav_transfer_end_age < 0:
                raise ValueError(
                    f"Asset '{asset.name}' bAV transfer end age must be "
                    "non-negative"
                )
            if asset.bav_transfer_end_age < asset.bav_transfer_start_age:
                raise ValueError(
                    f"Asset '{asset.name}' bAV transfer end age must be "
                    "at or after the start age"
                )
            if not 0 <= asset.bav_transfer_etf_ratio <= 1:
                raise ValueError(
                    f"Asset '{asset.name}' bAV transfer ETF ratio must be "
                    "between 0 and 1"
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
    if withdrawal.allocation_strategy != AllocationStrategy.PROPORTIONAL:
        raise ValueError(
            "Only proportional withdrawal allocation is supported"
        )
    state_pension = withdrawal.state_pension
    if state_pension is None:
        return
    if state_pension.current_monthly_amount < 0:
        raise ValueError("State pension amount must be non-negative")
    if state_pension.monthly_growth_per_working_year < 0:
        raise ValueError("State pension growth must be non-negative")
    if not 63 <= state_pension.start_age <= 67:
        raise ValueError("State pension start age must be between 63 and 67")
    if (
        state_pension.tax_rate is not None
        and not 0 <= state_pension.tax_rate < 1
    ):
        raise ValueError("State pension tax rate must be between 0 and 1")


def _net_state_pension_for_month(
    profile: UserProfile,
    metadata: ForecastMetadata,
    state_pension: StatePension | None,
    age_months: int,
    config: FinevConfig,
) -> float:
    """Return net monthly state pension for the given month."""
    if state_pension is None:
        return 0.0
    if age_months < state_pension.start_age * 12:
        return 0.0
    working_years = (
        max(metadata.retirement_age_months - metadata.start_age_months, 0) / 12
    )
    accrued_monthly_pension = state_pension.current_monthly_amount + (
        working_years * state_pension.monthly_growth_per_working_year
    )
    months_since_start = age_months - metadata.start_age_months
    inflation_multiplier = _inflation_multiplier(
        profile.average_inflation_rate,
        months_since_start,
    )
    reduction_years = max(67 - state_pension.start_age, 0)
    reduction_factor = 1 - (
        config.drv.rentenabschlag_pro_jahr * reduction_years
    )
    gross_monthly_pension = (
        accrued_monthly_pension * inflation_multiplier * reduction_factor
    )
    tax_rate = (
        state_pension.tax_rate
        if state_pension.tax_rate is not None
        else config.drv.brutto_rente_steuersatz
    )
    return gross_monthly_pension * (1 - tax_rate)


@dataclass(frozen=True)
class _EngineParams:
    """Immutable per-run context shared by every monthly step.

    Grouping the fixed inputs and derived lookups into one object keeps the step
    functions to two arguments (params + mutable state) instead of a dozen.
    """

    profile: UserProfile
    metadata: ForecastMetadata
    withdrawal: WithdrawalPlan
    config: FinevConfig
    assets_list: list[Asset]
    monthly_rates: list[float]
    etf_indices: list[int]
    cash_indices: list[int]
    # Inheritance events as (age_in_months, gross_amount, relationship).
    inheritance_events: list[tuple[int, float, InheritanceRelationship]]
    etf_tax_rate: float
    etf_taxable_share: float
    etf_annual_allowance: float
    bav_tax_rate: float


@dataclass
class _MonthlyState:
    """Mutable state evolving across the monthly timeline.

    ``balances``, ``cost_bases`` and ``remaining_etf_allowance`` carry over from
    month to month. ``taxes`` and ``net_cashflow`` accumulate within a single
    month and are reset by the caller at the start of each month.
    """

    balances: list[float]
    cost_bases: list[float]
    remaining_etf_allowance: float
    taxes: float = 0.0
    net_cashflow: float = 0.0


def _build_engine_params(
    profile: UserProfile,
    metadata: ForecastMetadata,
    assets_list: list[Asset],
    withdrawal: WithdrawalPlan,
    config: FinevConfig,
) -> _EngineParams:
    """Build the immutable per-run context and validate cross-asset rules.

    Raises:
        ValueError: If a bAV transfer lacks a required ETF or Cash target.
    """
    # Only consider active assets for allocation targets and transfer checks.
    etf_indices = [
        index
        for index, asset in enumerate(assets_list)
        if asset.asset_type == AssetType.ETF and asset.active
    ]
    cash_indices = [
        index
        for index, asset in enumerate(assets_list)
        if asset.asset_type == AssetType.CASH and asset.active
    ]
    transfer_assets = [
        asset
        for asset in assets_list
        if asset.asset_type == AssetType.BAV
        and asset.active
        and BAVStrategy(asset.bav_strategy) == BAVStrategy.TRANSFER
    ]
    inheritance_events: list[tuple[int, float, InheritanceRelationship]] = [
        (
            asset.inheritance_age * 12,
            asset.inheritance_gross_amount,
            asset.inheritance_relationship,
        )
        for asset in assets_list
        if asset.asset_type == AssetType.INHERITANCE
        and asset.active
        and asset.inheritance_gross_amount > 0
    ]
    if transfer_assets:
        if (
            any(asset.bav_transfer_etf_ratio > 0 for asset in transfer_assets)
            and not etf_indices
        ):
            raise ValueError("bAV transfer requires at least one ETF asset")
        if (
            any(asset.bav_transfer_etf_ratio < 1 for asset in transfer_assets)
            and not cash_indices
        ):
            raise ValueError("bAV transfer requires at least one Cash asset")

    monthly_rates = [
        _annual_to_monthly_rate(asset.effective_annual_gain_rate())
        for asset in assets_list
    ]
    return _EngineParams(
        profile=profile,
        metadata=metadata,
        withdrawal=withdrawal,
        config=config,
        assets_list=assets_list,
        monthly_rates=monthly_rates,
        etf_indices=etf_indices,
        cash_indices=cash_indices,
        inheritance_events=inheritance_events,
        etf_tax_rate=config.capital_gains_tax_rate,
        etf_taxable_share=config.etf.taxable_share,
        etf_annual_allowance=config.etf.steuerfreibetrag_euro,
        bav_tax_rate=config.capital_gains_tax_rate,
    )


def _initial_state(
    params: _EngineParams,
) -> _MonthlyState:
    """Build the starting balances and cost bases for the forecast.

    INHERITANCE assets hold no running balance; inactive assets are zeroed.
    """
    balances = [
        float(asset.current_value)
        if asset.active and asset.asset_type != AssetType.INHERITANCE
        else 0.0
        for asset in params.assets_list
    ]
    cost_bases = [
        float(asset.effective_cost_basis())
        if asset.active and asset.asset_type != AssetType.INHERITANCE
        else 0.0
        for asset in params.assets_list
    ]
    return _MonthlyState(
        balances=balances,
        cost_bases=cost_bases,
        remaining_etf_allowance=params.etf_annual_allowance,
    )


def _apply_inheritance(
    params: _EngineParams,
    state: _MonthlyState,
    age_months: int,
) -> None:
    """Credit net inheritance proceeds due this month to ETF (then Cash)."""
    for (
        inh_age_months,
        gross_amount,
        relationship,
    ) in params.inheritance_events:
        if age_months != inh_age_months:
            continue
        inh_tax = params.config.inheritance_tax.compute_tax(
            gross_amount, relationship
        )
        net_amount = gross_amount - inh_tax
        state.taxes += inh_tax
        state.net_cashflow += net_amount
        # Distribute net proceeds to ETF assets first, Cash as fallback.
        targets = params.etf_indices or params.cash_indices
        for target_idx, allocation in _allocate_amount(
            net_amount, targets, state.balances
        ):
            state.balances[target_idx] += allocation
            state.cost_bases[target_idx] += allocation


def _apply_contributions(
    params: _EngineParams,
    state: _MonthlyState,
) -> None:
    """Add monthly contributions to each active, non-inheritance asset."""
    contributions = [
        float(asset.monthly_contribution)
        if asset.active and asset.asset_type != AssetType.INHERITANCE
        else 0.0
        for asset in params.assets_list
    ]
    state.balances = [
        balance + contribution
        for balance, contribution in zip(
            state.balances, contributions, strict=True
        )
    ]
    state.cost_bases = [
        cost_basis + contribution
        for cost_basis, contribution in zip(
            state.cost_bases, contributions, strict=True
        )
    ]
    state.net_cashflow += float(sum(contributions))


def _withdrawable_indices(
    params: _EngineParams,
    age_months: int,
) -> list[int]:
    """Return indices of assets withdrawable at this age.

    ETFs and Cash are always withdrawable; bAV becomes withdrawable once its
    configured transfer/withdraw start age has been reached.
    """
    return [
        i
        for i, asset in enumerate(params.assets_list)
        if asset.active
        and (
            asset.asset_type in (AssetType.ETF, AssetType.CASH)
            or (
                asset.asset_type == AssetType.BAV
                and age_months >= asset.bav_transfer_start_age * 12
            )
        )
    ]


def _gross_up_withdrawal(
    params: _EngineParams,
    state: _MonthlyState,
    withdrawable_indices: list[int],
    withdrawal_target: float,
    total_balance: float,
) -> float:
    """Return the gross withdrawal that nets ``withdrawal_target`` after ETF tax.

    The net target must be grossed up to cover ETF capital-gains tax on the
    taxable gains portion of the withdrawal, accounting for any remaining annual
    tax-free allowance.
    """
    taxable_gains_ratio = 0.0
    # Only withdrawable ETFs with positive gains contribute taxable gains.
    for i in withdrawable_indices:
        asset = params.assets_list[i]
        balance = state.balances[i]
        cost_basis = state.cost_bases[i]
        if asset.asset_type != AssetType.ETF or balance <= 0:
            continue
        gains = balance - cost_basis
        if gains <= 0:
            continue
        gains_ratio = gains / balance
        taxable_gains_ratio += (
            (balance / total_balance) * gains_ratio * params.etf_taxable_share
        )

    gross_target = withdrawal_target
    if taxable_gains_ratio > 0 and params.etf_tax_rate > 0:
        if state.remaining_etf_allowance > 0:
            allowance_threshold = (
                state.remaining_etf_allowance / taxable_gains_ratio
            )
            if withdrawal_target > allowance_threshold:
                numerator = withdrawal_target - (
                    params.etf_tax_rate * state.remaining_etf_allowance
                )
                denominator = 1 - params.etf_tax_rate * taxable_gains_ratio
                gross_target = (
                    numerator / denominator
                    if denominator > 0
                    else total_balance
                )
        else:
            denominator = 1 - params.etf_tax_rate * taxable_gains_ratio
            gross_target = (
                withdrawal_target / denominator
                if denominator > 0
                else total_balance
            )
    return gross_target


def _apply_withdrawal(
    params: _EngineParams,
    state: _MonthlyState,
    age_months: int,
) -> None:
    """Withdraw the inflated net target proportionally across assets, after tax.

    The net monthly target is inflated to the current month and reduced by the
    net state pension, grossed up for ETF tax, then allocated by balance weight
    across the withdrawable assets.
    """
    months_since_start = age_months - params.metadata.start_age_months
    inflation_multiplier = _inflation_multiplier(
        params.profile.average_inflation_rate, months_since_start
    )
    withdrawal_target = (
        float(params.withdrawal.monthly_withdrawal) * inflation_multiplier
    )
    withdrawal_target = max(
        withdrawal_target
        - _net_state_pension_for_month(
            profile=params.profile,
            metadata=params.metadata,
            state_pension=params.withdrawal.state_pension,
            age_months=age_months,
            config=params.config,
        ),
        0.0,
    )
    withdrawable_indices = _withdrawable_indices(params, age_months)
    total_balance = (
        float(sum(state.balances[i] for i in withdrawable_indices))
        if withdrawable_indices
        else 0.0
    )
    if not (withdrawal_target > 0 and total_balance > 0):
        return

    gross_target = _gross_up_withdrawal(
        params, state, withdrawable_indices, withdrawal_target, total_balance
    )
    actual_withdrawn = min(gross_target, total_balance)
    new_balances: list[float] = []
    new_cost_bases: list[float] = []
    etf_taxable_gains = 0.0
    # Allocate withdrawals proportionally across withdrawable assets only.
    for i, (asset, balance, cost_basis) in enumerate(
        zip(params.assets_list, state.balances, state.cost_bases, strict=True)
    ):
        if i not in withdrawable_indices or balance <= 0:
            # Asset is not withdrawable now; keep as is.
            new_balances.append(balance)
            new_cost_bases.append(max(cost_basis, 0.0))
            continue

        asset_withdrawal = actual_withdrawn * (balance / total_balance)
        withdrawal_ratio = asset_withdrawal / balance if balance > 0 else 0.0
        new_balance = max(balance - asset_withdrawal, 0.0)
        cost_basis_reduction = cost_basis * withdrawal_ratio
        new_cost_basis = max(cost_basis - cost_basis_reduction, 0.0)

        if asset.asset_type == AssetType.ETF:
            gains = balance - cost_basis
            if gains > 0:
                gains_portion = asset_withdrawal * (gains / balance)
                etf_taxable_gains += gains_portion * params.etf_taxable_share

        new_balances.append(new_balance)
        new_cost_bases.append(new_cost_basis)

    state.balances = new_balances
    state.cost_bases = new_cost_bases
    allowance_used = min(state.remaining_etf_allowance, etf_taxable_gains)
    taxable_after_allowance = etf_taxable_gains - allowance_used
    withdrawal_taxes = taxable_after_allowance * params.etf_tax_rate
    state.remaining_etf_allowance -= allowance_used
    state.taxes += withdrawal_taxes
    state.net_cashflow += -actual_withdrawn + withdrawal_taxes


def _apply_bav_transfer(
    params: _EngineParams,
    state: _MonthlyState,
    age_months: int,
) -> None:
    """Transfer a slice of each in-window bAV (TRANSFER) balance to ETF/Cash."""
    for index, asset in enumerate(params.assets_list):
        if not asset.active:
            continue
        if not (
            asset.asset_type == AssetType.BAV
            and BAVStrategy(asset.bav_strategy) == BAVStrategy.TRANSFER
        ):
            continue
        start_months = asset.bav_transfer_start_age * 12
        end_months = (asset.bav_transfer_end_age + 1) * 12 - 1
        if not (start_months <= age_months <= end_months):
            continue
        remaining_months = end_months - age_months + 1
        if remaining_months <= 0:
            continue
        transfer_fraction = 1 / remaining_months
        gross_transfer = state.balances[index] * transfer_fraction
        if gross_transfer <= 0:
            continue
        cost_basis_transfer = state.cost_bases[index] * transfer_fraction
        gains = gross_transfer - cost_basis_transfer
        tax = params.bav_tax_rate * max(gains, 0.0)
        state.taxes += tax
        state.net_cashflow -= tax
        net_transfer = gross_transfer - tax
        etf_amount = net_transfer * asset.bav_transfer_etf_ratio
        cash_amount = net_transfer - etf_amount
        for target_index, allocation in _allocate_amount(
            etf_amount, params.etf_indices, state.balances
        ):
            state.balances[target_index] += allocation
            state.cost_bases[target_index] += allocation
        for target_index, allocation in _allocate_amount(
            cash_amount, params.cash_indices, state.balances
        ):
            state.balances[target_index] += allocation
            state.cost_bases[target_index] += allocation
        state.balances[index] -= gross_transfer
        state.cost_bases[index] = max(
            state.cost_bases[index] - cost_basis_transfer, 0.0
        )


def _apply_bav_income(
    params: _EngineParams,
    state: _MonthlyState,
    age_months: int,
) -> set[int]:
    """Pay out monthly gains from income-strategy bAV assets.

    Returns:
        Indices whose balance must not compound this month (income bAV freezes
        its principal once payouts have begun).
    """
    frozen_indices: set[int] = set()
    for index, asset in enumerate(params.assets_list):
        if not asset.active:
            continue
        if (
            asset.asset_type == AssetType.BAV
            and BAVStrategy(asset.bav_strategy) == BAVStrategy.INCOME
            and age_months >= asset.bav_transfer_start_age * 12
        ):
            monthly_gain = state.balances[index] * params.monthly_rates[index]
            if monthly_gain > 0:
                tax = monthly_gain * params.bav_tax_rate
                state.taxes += tax
                state.net_cashflow += monthly_gain - tax
            frozen_indices.add(index)
    return frozen_indices


def _apply_growth(
    params: _EngineParams,
    state: _MonthlyState,
    frozen_indices: set[int],
) -> None:
    """Compound each balance by its monthly rate, skipping frozen assets."""
    state.balances = [
        balance
        * (1 + (0.0 if i in frozen_indices else params.monthly_rates[i]))
        for i, balance in enumerate(state.balances)
    ]


def _build_row(
    params: _EngineParams,
    state: _MonthlyState,
    month_index: int,
    age_years: int,
    age_month_in_year: int,
) -> dict[str, float | int]:
    """Assemble one output row from the current state (excludes inheritance)."""
    row: dict[str, float | int] = {
        "month_index": month_index,
        "age_years": int(age_years),
        "age_months": int(age_month_in_year),
        "net_cashflow": float(state.net_cashflow),
        "taxes": float(state.taxes),
    }
    # INHERITANCE assets always hold a zero balance — exclude from columns.
    for asset, balance in zip(params.assets_list, state.balances, strict=True):
        if asset.asset_type != AssetType.INHERITANCE:
            row[asset.name] = float(balance)
    row["total"] = float(
        sum(
            balance
            for asset, balance in zip(
                params.assets_list, state.balances, strict=True
            )
            if asset.asset_type != AssetType.INHERITANCE
        )
    )
    return row


def forecast_wealth(
    profile: UserProfile,
    assets: Iterable[Asset],
    withdrawal: WithdrawalPlan | None = None,
) -> pd.DataFrame:
    """Forecast monthly balances per asset and total.

    The monthly timeline is an ordered pipeline of per-month steps (inheritance,
    contributions or withdrawal, bAV transfer, bAV income, growth); each step is
    a small pure function operating on the shared :class:`_MonthlyState`.

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
    config = get_config()

    params = _build_engine_params(
        profile, metadata, assets_list, withdrawal, config
    )
    state = _initial_state(params)

    months = metadata.end_age_months - metadata.start_age_months
    rows: list[dict[str, float | int]] = []
    for month_index in range(months + 1):
        age_months = metadata.start_age_months + month_index
        age_years = age_months // 12
        age_month_in_year = age_months % 12
        if month_index > 0 and age_month_in_year == 0:
            state.remaining_etf_allowance = params.etf_annual_allowance

        state.taxes = 0.0
        state.net_cashflow = 0.0
        if month_index > 0:
            _apply_inheritance(params, state, age_months)
            if age_months < metadata.retirement_age_months:
                _apply_contributions(params, state)
            else:
                _apply_withdrawal(params, state, age_months)
            _apply_bav_transfer(params, state, age_months)
            frozen_indices = (
                _apply_bav_income(params, state, age_months)
                if age_months >= metadata.retirement_age_months
                else set()
            )
            _apply_growth(params, state, frozen_indices)

        rows.append(
            _build_row(
                params, state, month_index, age_years, age_month_in_year
            )
        )

    return pd.DataFrame(rows)
