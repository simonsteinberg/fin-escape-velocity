import pytest

from finev.forecast import (
    _validate_assets,
    _validate_profile,
    _validate_withdrawal,
    forecast_wealth,
)
from finev.models import (
    Asset,
    AssetType,
    BAVStrategy,
    InvestmentKind,
    StatePension,
    UserProfile,
    WithdrawalPlan,
)


def _valid_profile() -> UserProfile:
    return UserProfile(current_age_years=30, retirement_age=65, end_age=90)


def _valid_asset(**overrides: float | str | AssetType | None) -> Asset:
    data = {
        "name": "ETF",
        "asset_type": AssetType.ETF,
        "current_value": 100.0,
        "monthly_contribution": 0.0,
        "annual_gain_rate": 0.05,
    }
    data.update(overrides)
    return Asset(**data)


@pytest.mark.parametrize(
    ("profile", "message"),
    [
        (
            UserProfile(current_age_years=-1, retirement_age=60, end_age=90),
            "Current age must be non-negative",
        ),
        (
            UserProfile(
                current_age_years=30,
                current_age_months=12,
                retirement_age=60,
                end_age=90,
            ),
            "Current age months must be between 0 and 11",
        ),
        (
            UserProfile(current_age_years=30, retirement_age=-1, end_age=90),
            "Retirement age must be non-negative",
        ),
        (
            UserProfile(current_age_years=30, retirement_age=60, end_age=0),
            "End age must be positive",
        ),
        (
            UserProfile(current_age_years=30, retirement_age=67, end_age=60),
            "End age must be at or after retirement age",
        ),
        (
            UserProfile(
                current_age_years=30,
                current_age_months=6,
                retirement_age=30,
                end_age=30,
            ),
            "End age must be after current age",
        ),
        (
            UserProfile(
                current_age_years=30,
                retirement_age=60,
                end_age=90,
                average_inflation_rate=-1.0,
            ),
            "Average inflation rate must be greater than -100%",
        ),
    ],
)
def test_validate_profile_rejects_invalid_inputs(
    profile: UserProfile, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        _validate_profile(profile)


def test_validate_assets_rejects_empty_assets() -> None:
    with pytest.raises(ValueError, match="At least one asset is required"):
        forecast_wealth(profile=_valid_profile(), assets=[])


def test_validate_assets_rejects_blank_name() -> None:
    asset = _valid_asset(name="   ")

    with pytest.raises(ValueError, match="Asset name must not be empty"):
        _validate_assets([asset])


def test_validate_assets_rejects_duplicate_names_case_insensitive() -> None:
    assets = [_valid_asset(name="Cash"), _valid_asset(name="cash")]

    with pytest.raises(ValueError, match="Duplicate asset name"):
        _validate_assets(assets)


def test_validate_assets_rejects_negative_current_value() -> None:
    asset = _valid_asset(current_value=-1.0)

    with pytest.raises(ValueError, match="current value must be non-negative"):
        _validate_assets([asset])


def test_validate_assets_rejects_negative_monthly_contribution() -> None:
    asset = _valid_asset(monthly_contribution=-10.0)

    with pytest.raises(
        ValueError, match="monthly contribution must be non-negative"
    ):
        _validate_assets([asset])


def test_validate_assets_rejects_invalid_gain_rate() -> None:
    asset = _valid_asset(annual_gain_rate=-1.0)

    with pytest.raises(
        ValueError, match="annual gain rate must be greater than -100%"
    ):
        _validate_assets([asset])


def test_validate_assets_rejects_negative_cost_basis() -> None:
    asset = _valid_asset(initial_cost_basis=-1.0)

    with pytest.raises(ValueError, match="cost basis must be non-negative"):
        _validate_assets([asset])


def test_validate_assets_rejects_negative_bav_retirement_age() -> None:
    asset = _valid_asset(
        asset_type=AssetType.BAV,
        bav_retirement_age=-1,
    )

    with pytest.raises(
        ValueError, match="bAV retirement age must be non-negative"
    ):
        _validate_assets([asset])


def test_validate_assets_rejects_invalid_bav_transfer_ratio() -> None:
    asset = _valid_asset(
        asset_type=AssetType.BAV,
        bav_strategy=BAVStrategy.TRANSFER,
        bav_transfer_etf_ratio=1.5,
    )

    with pytest.raises(
        ValueError, match="bAV transfer ETF ratio must be between 0 and 1"
    ):
        _validate_assets([asset])


def test_validate_assets_rejects_negative_vbl_pension() -> None:
    asset = _valid_asset(
        asset_type=AssetType.VBL_KLASSIK,
        current_value=0.0,
        vbl_monthly_pension=-1.0,
    )

    with pytest.raises(
        ValueError, match="VBL monthly pension must be non-negative"
    ):
        _validate_assets([asset])


def test_validate_assets_rejects_negative_vbl_growth() -> None:
    asset = _valid_asset(
        asset_type=AssetType.VBL_KLASSIK,
        current_value=0.0,
        vbl_monthly_growth_per_working_year=-1.0,
    )

    with pytest.raises(
        ValueError, match="VBL growth per working year must be non-negative"
    ):
        _validate_assets([asset])


def test_validate_assets_rejects_negative_vbl_start_age() -> None:
    asset = _valid_asset(
        asset_type=AssetType.VBL_KLASSIK,
        current_value=0.0,
        vbl_start_age=-1,
    )

    with pytest.raises(ValueError, match="VBL start age must be non-negative"):
        _validate_assets([asset])


def test_validate_assets_rejects_invalid_vbl_tax_rate() -> None:
    asset = _valid_asset(
        asset_type=AssetType.VBL_KLASSIK,
        current_value=0.0,
        vbl_tax_rate=1.5,
    )

    with pytest.raises(
        ValueError, match="VBL tax rate must be between 0 and 1"
    ):
        _validate_assets([asset])


def test_validate_assets_accepts_vbl_without_balance() -> None:
    # A VBLklassik asset carries no balance/contribution and must validate even
    # though those fields are left at their defaults.
    asset = _valid_asset(
        asset_type=AssetType.VBL_KLASSIK,
        current_value=0.0,
        vbl_monthly_pension=1_000.0,
        vbl_start_age=67,
    )

    assert _validate_assets([asset]) == [asset]


def test_bav_transfer_requires_target_assets() -> None:
    profile = _valid_profile()
    assets = [
        Asset(
            name="bAV",
            asset_type=AssetType.BAV,
            current_value=1000.0,
            monthly_contribution=0.0,
            bav_strategy=BAVStrategy.TRANSFER,
            bav_transfer_etf_ratio=0.5,
        ),
        Asset(
            name="Cash",
            asset_type=AssetType.CASH,
            current_value=0.0,
            monthly_contribution=0.0,
        ),
    ]

    with pytest.raises(
        ValueError, match="bAV transfer requires at least one ETF asset"
    ):
        forecast_wealth(profile=profile, assets=assets)


def test_validate_withdrawal_rejects_invalid_inputs() -> None:
    with pytest.raises(
        ValueError, match="Monthly withdrawal must be non-negative"
    ):
        _validate_withdrawal(WithdrawalPlan(monthly_withdrawal=-1.0))

    with pytest.raises(
        ValueError,
        match="Only proportional withdrawal allocation is supported",
    ):
        _validate_withdrawal(
            WithdrawalPlan(
                monthly_withdrawal=100.0, allocation_strategy="lifo"
            )
        )

    with pytest.raises(
        ValueError, match="State pension amount must be non-negative"
    ):
        _validate_withdrawal(
            WithdrawalPlan(
                state_pension=StatePension(
                    current_monthly_amount=-1.0,
                    monthly_growth_per_working_year=0.0,
                    start_age=67,
                )
            )
        )

    with pytest.raises(
        ValueError, match="State pension growth must be non-negative"
    ):
        _validate_withdrawal(
            WithdrawalPlan(
                state_pension=StatePension(
                    current_monthly_amount=1.0,
                    monthly_growth_per_working_year=-1.0,
                    start_age=67,
                )
            )
        )

    with pytest.raises(
        ValueError, match="State pension start age must be between 63 and 67"
    ):
        _validate_withdrawal(
            WithdrawalPlan(
                state_pension=StatePension(
                    current_monthly_amount=1.0,
                    monthly_growth_per_working_year=0.0,
                    start_age=62,
                )
            )
        )

    with pytest.raises(
        ValueError, match="State pension adjustment rate must be above -100%"
    ):
        _validate_withdrawal(
            WithdrawalPlan(
                state_pension=StatePension(
                    current_monthly_amount=1.0,
                    monthly_growth_per_working_year=0.0,
                    start_age=67,
                    adjustment_rate=-1.0,
                )
            )
        )


def test_forecast_handles_withdrawal_when_balances_are_zero() -> None:
    profile = UserProfile(
        current_age_years=67,
        retirement_age=67,
        end_age=68,
        average_inflation_rate=0.0,
    )
    assets = [
        Asset(
            name="Cash",
            asset_type=AssetType.CASH,
            current_value=0.0,
            annual_gain_rate=0.0,
            monthly_contribution=0.0,
        )
    ]
    withdrawal = WithdrawalPlan(monthly_withdrawal=1_000.0)

    result = forecast_wealth(
        profile=profile, assets=assets, withdrawal=withdrawal
    )

    # With no balances to draw on, the withdrawal is funded by borrowing: the
    # asset stays at zero, no tax applies, and the need becomes negative wealth.
    assert result.loc[1, "Cash"] == pytest.approx(0.0)
    assert result.loc[1, "taxes"] == pytest.approx(0.0)
    assert result.loc[1, "net_cashflow"] == pytest.approx(-1_000.0)
    assert result.loc[1, "total"] < 0.0


def test_validate_assets_rejects_contribution_growth_at_minus_100_pct() -> (
    None
):
    asset = _valid_asset(monthly_contribution_growth_rate=-1.0)

    with pytest.raises(
        ValueError, match="contribution growth rate must be greater than -100%"
    ):
        _validate_assets([asset])


def _investment_asset(**overrides: object) -> Asset:
    data: dict[str, object] = {
        "name": "House",
        "asset_type": AssetType.INVESTMENT,
        "current_value": 0.0,
        "investment_kind": InvestmentKind.LONG_TERM,
        "investment_amount": 100_000.0,
        "investment_age": 55,
        "investment_interest_rate": 0.03,
        "investment_monthly_payment": 1_000.0,
    }
    data.update(overrides)
    return Asset(**data)  # type: ignore[arg-type]


def test_validate_assets_accepts_serviceable_loan() -> None:
    assert _validate_assets([_investment_asset()]) == [_investment_asset()]


def test_validate_assets_rejects_negative_investment_amount() -> None:
    asset = _investment_asset(investment_amount=-1.0)

    with pytest.raises(
        ValueError, match="investment amount must be non-negative"
    ):
        _validate_assets([asset])


def test_validate_assets_rejects_negative_investment_age() -> None:
    asset = _investment_asset(investment_age=-1)

    with pytest.raises(
        ValueError, match="investment age must be non-negative"
    ):
        _validate_assets([asset])


def test_validate_assets_rejects_loan_without_payment() -> None:
    asset = _investment_asset(investment_monthly_payment=0.0)

    with pytest.raises(
        ValueError, match="investment monthly payment must be positive"
    ):
        _validate_assets([asset])


def test_validate_assets_rejects_payment_below_first_interest() -> None:
    # 500k at 3% costs ~1 233 in interest in month one, so 1 000 a month never
    # repays the loan.
    asset = _investment_asset(
        investment_amount=500_000.0,
        investment_interest_rate=0.03,
        investment_monthly_payment=1_000.0,
    )

    with pytest.raises(
        ValueError, match="must exceed the first month's interest"
    ):
        _validate_assets([asset])


def test_validate_assets_ignores_loan_terms_for_one_time_purchase() -> None:
    asset = _investment_asset(
        investment_kind=InvestmentKind.ONE_TIME,
        investment_monthly_payment=0.0,
    )

    assert _validate_assets([asset]) == [asset]


def test_validate_assets_rejects_notgroschen_on_non_cash_asset() -> None:
    asset = _valid_asset(notgroschen=True)

    with pytest.raises(
        ValueError, match="can only be a Notgroschen if it is a Cash asset"
    ):
        _validate_assets([asset])


def test_validate_assets_rejects_notgroschen_rate_at_minus_100_pct() -> None:
    asset = _valid_asset(
        asset_type=AssetType.CASH,
        notgroschen=True,
        notgroschen_inflation_rate=-1.0,
    )

    with pytest.raises(
        ValueError, match="Notgroschen inflation rate must be greater"
    ):
        _validate_assets([asset])
