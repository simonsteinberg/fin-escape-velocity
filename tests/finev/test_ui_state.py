"""Unit tests for asset-row editing logic extracted from the UI closure."""

from __future__ import annotations

from finev.models import AssetType, BAVStrategy, InheritanceRelationship
from finev.ui_state import (
    apply_type_change_defaults,
    coerce_asset_field,
    default_gain_pct,
    new_asset_row,
)


def test_new_asset_row_defaults() -> None:
    row = new_asset_row()
    assert row["type"] == AssetType.ETF.value
    assert row["active"] is True
    assert row["annual_gain_rate_pct"] == default_gain_pct(AssetType.ETF)


def test_type_change_updates_default_gain_rate_when_not_customised() -> None:
    # Row currently ETF with ETF's default rate -> switching to CASH should
    # adopt CASH's default (the user had not customised it).
    row = {
        "type": AssetType.ETF.value,
        "annual_gain_rate_pct": default_gain_pct(AssetType.ETF),
    }
    apply_type_change_defaults(row, AssetType.CASH)
    assert row["annual_gain_rate_pct"] == default_gain_pct(AssetType.CASH)


def test_type_change_preserves_customised_gain_rate() -> None:
    row = {"type": AssetType.ETF.value, "annual_gain_rate_pct": 12.3}
    apply_type_change_defaults(row, AssetType.CASH)
    assert row["annual_gain_rate_pct"] == 12.3


def test_type_change_seeds_inheritance_fields() -> None:
    row = {"type": AssetType.ETF.value}
    apply_type_change_defaults(row, AssetType.INHERITANCE)
    assert row["inheritance_gross_amount"] == 0.0
    assert row["inheritance_age"] == 67
    assert (
        row["inheritance_relationship"] == InheritanceRelationship.KIND.value
    )


def test_coerce_clamps_etf_ratio_and_ages() -> None:
    assert coerce_asset_field({}, "bav_transfer_etf_ratio_pct", 150) == 100.0
    assert coerce_asset_field({}, "bav_transfer_etf_ratio_pct", -5) == 0.0
    assert coerce_asset_field({}, "bav_retirement_age", -3) == 0


def test_coerce_unrealized_gains_clamped_to_current_value() -> None:
    row = {"current_value": 1000.0}
    assert coerce_asset_field(row, "unrealized_gains", 5000) == 1000.0
    assert coerce_asset_field(row, "unrealized_gains", -10) == 0.0


def test_coerce_invalid_enum_falls_back_to_default() -> None:
    assert (
        coerce_asset_field({}, "bav_strategy", "bogus")
        == BAVStrategy.TRANSFER.value
    )
    assert (
        coerce_asset_field({}, "inheritance_relationship", "bogus")
        == InheritanceRelationship.KIND.value
    )


def test_coerce_passes_through_unhandled_field() -> None:
    assert coerce_asset_field({}, "name", "My ETF") == "My ETF"
