"""Rendering tests for the per-type asset-row editor.

``_render_asset_row`` builds a different set of widgets for every asset type,
and none of the handler-level tests touch that branching. These build the
widget tree in a headless NiceGUI client (no browser, no server) and assert on
the labels that come out, so a type whose inputs silently stop rendering fails
the suite instead of the eye.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from nicegui import Client

from finev.i18n import make_translator
from finev.models import AssetType
from finev.ui import _render_asset_row
from finev.ui_state import new_asset_row


def _rendered_labels(**row_overrides: Any) -> list[str]:
    """Return the input labels a row renders, in creation order.

    Args:
        **row_overrides: Fields to override on a fresh default asset row.

    Returns:
        The ``label`` prop of every widget the row created, plus the text of
        text-carrying elements (checkbox captions).
    """
    row = new_asset_row()
    row.update(row_overrides)
    labels: list[str] = []

    def page() -> None:
        _render_asset_row(
            0,
            row,
            lambda *_args: None,
            lambda *_args: None,
            make_translator("en"),
        )

    async def build() -> None:
        client = Client(page, request=None)
        with client:
            page()
        for element in client.elements.values():
            label = element._props.get("label")
            if label:
                labels.append(str(label))
            text = getattr(element, "text", None)
            if text:
                labels.append(str(text))

    asyncio.run(build())
    return labels


@pytest.mark.parametrize(
    ("asset_type", "expected"),
    [
        (
            AssetType.ETF,
            ["Current value", "Monthly contribution"],
        ),
        (
            AssetType.CASH,
            ["Current value", "Monthly contribution"],
        ),
        (AssetType.INHERITANCE, ["Gross amount", "Age at receipt"]),
        (AssetType.VBL_KLASSIK, ["Input", "Pension start age"]),
        (AssetType.INVESTMENT, ["Purchase price", "Age at purchase"]),
    ],
)
def test_row_renders_its_type_specific_inputs(
    asset_type: AssetType, expected: list[str]
) -> None:
    labels = _rendered_labels(type=asset_type.value)

    assert "Name" in labels
    assert "Type" in labels
    for label in expected:
        assert label in labels


def test_contribution_adaption_renders_for_every_paying_type() -> None:
    # ETF, bAV and Cash all take contributions, so all three must offer the
    # adaption input next to it (this is what lets the daily account save).
    for asset_type in (AssetType.ETF, AssetType.BAV, AssetType.CASH):
        labels = _rendered_labels(type=asset_type.value)
        assert "Annual contribution change (%)" in labels, asset_type


def test_investment_shows_loan_fields_only_when_financed() -> None:
    one_time = _rendered_labels(
        type=AssetType.INVESTMENT.value, investment_kind="one_time"
    )
    financed = _rendered_labels(
        type=AssetType.INVESTMENT.value, investment_kind="long_term"
    )

    assert "Loan interest (% p.a.)" not in one_time
    assert "Monthly repayment" not in one_time
    assert "Loan interest (% p.a.)" in financed
    assert "Monthly repayment" in financed


def test_notgroschen_box_is_cash_only() -> None:
    cash = _rendered_labels(type=AssetType.CASH.value)
    etf = _rendered_labels(type=AssetType.ETF.value)

    assert "Emergency fund (Notgroschen)" in cash
    assert "Emergency fund (Notgroschen)" not in etf


def test_notgroschen_reveals_its_options_one_step_at_a_time() -> None:
    plain = _rendered_labels(type=AssetType.CASH.value)
    buffer_ = _rendered_labels(type=AssetType.CASH.value, notgroschen=True)
    adapting = _rendered_labels(
        type=AssetType.CASH.value,
        notgroschen=True,
        notgroschen_keep_inflation=True,
    )

    # The adaption choice appears only once the row is a buffer, and the rate
    # only once that adaption is actually kept.
    assert "Keep inflation adaption in retirement" not in plain
    assert "Keep inflation adaption in retirement" in buffer_
    assert "Retirement adaption (% p.a.)" not in buffer_
    assert "Retirement adaption (% p.a.)" in adapting
