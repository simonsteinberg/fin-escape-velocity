# Wealth Forecast App — Design and Requirements

## Overview

The Wealth Forecast App projects the monthly value of a user's assets from their current age
through age 100. It models asset-specific growth, pre-retirement contributions, and
post-retirement withdrawals, including German capital-gains tax on ETF withdrawals and
bAV-specific payout strategies.

---

## Goals

- Produce a **monthly** forecast per asset and for the total portfolio through age 100.
- Model asset growth using **default annual gain rates**, configurable globally and per asset.
- Support **monthly contributions** to individual assets until retirement.
- Support **monthly withdrawals** from the portfolio starting at retirement, while remaining
  capital continues to grow.
- Provide a NiceGUI-based user interface backed by a Python forecasting engine.

---

## Definitions

| Term | Meaning |
|---|---|
| **Current age** | User's age at the start of the forecast, expressed in whole years plus optional months. |
| **Retirement age** | Age at which contributions stop and withdrawals begin. Default: 67. |
| **End age** | Last age included in the forecast. Default: 100. |
| **Monthly step** | Forecast granularity; one calculation per calendar month. |
| **Cost basis** | Cumulative sum of all contributions made to an ETF asset. Never decreases due to market movement. |
| **Gains** | Current balance minus cost basis; floored at zero (cost basis is never written down). |
| **Gross withdrawal** | Amount deducted from the portfolio before tax. |
| **Net cashflow** | Amount the user actually receives after ETF withdrawal taxes are deducted. |
| **bAV strategy** | Rule that governs how bAV assets pay out (transfer window or monthly gains income). |
| **Transfer window** | Age range over which a bAV balance is transferred into ETF/Cash. |

---

## Architecture

- **Frontend**: NiceGUI-based UI for data entry and result visualisation.
- **Backend**: Python forecasting engine using NumPy and/or pandas.

---

## Extensibility

This app is intended to grow incrementally. Requirements will be added in future iterations,
so the code structure and software architecture must be designed to accommodate change with
minimal rework. Specific expectations:

- **Forecasting engine decoupled from UI.** The engine should be a pure Python module
  that accepts a well-defined input model and returns a well-defined output structure.
  The NiceGUI layer only calls the engine; it does not contain business logic.
- **Per-month hook points.** The monthly calculation loop should be structured so that
  additional per-month adjustments (e.g. inflation deflation of real values, tax on
  accumulation, scenario branching) can be inserted without restructuring the loop.
- **Asset types are extensible.** New asset types (e.g. real estate, bonds, annuities)
  should be addable by implementing a small, well-defined interface rather than modifying
  existing type logic.
- **Tax rules are pluggable.** The ETF tax rule is implemented as a separate, replaceable
  component so that alternative tax regimes (other countries, future law changes) can be
  swapped in or layered alongside the existing rule.
- **Input/output models are versioned.** Use explicit data classes or schemas (e.g. Python
  `dataclasses` or Pydantic models) for all inputs and outputs so that adding a new field
  does not break existing callers.

---

## Inputs

### User Profile

| Field | Default | Notes |
|---|---|---|
| Current age | — | Required; whole years + optional months (e.g. 35y 4m). |
| Retirement age | 67 | Configurable. |
| End age | 100 | Configurable. |
| Currency label | EUR | Display only; no FX conversion. |
| Monthly withdrawal target | — | Net amount the user wants to receive each month in retirement (see §Withdrawal Target Interpretation). |
| Average inflation rate | 0 % | Annual rate used to inflate the retirement withdrawal target from today's currency. |

### Assets

Each asset has:

| Field | Required | Notes |
|---|---|---|
| Name | Yes | Free text, e.g. "ETF MSCI World". |
| Type | Yes | One of: `ETF`, `bAV`, `cash`. |
| Current value | Yes | Starting balance in the chosen currency. |
| Annual gain rate | No | Falls back to the type default if omitted. |

#### bAV-specific fields

| Field | Required | Notes |
|---|---|---|
| bAV strategy | Yes (for bAV) | `transfer` or `income`. |
| Transfer start age | If strategy = transfer | Age in years when the transfer window begins. |
| Transfer end age | If strategy = transfer | Age in years when the transfer window ends. |
| Transfer ETF ratio | If strategy = transfer | Share of the net transfer allocated to ETF; remainder goes to Cash. |

### Contributions (pre-retirement)

A monthly contribution amount per asset, applied from the current age until retirement.
Contributions may be zero.

### Withdrawals (post-retirement)

- A single **net monthly withdrawal target** (e.g. 3,000 EUR) starting at retirement.
- The engine computes the required gross withdrawal to deliver that net amount after ETF
  taxes (see §ETF Withdrawal Tax).
- Allocation strategy (default): **proportional to asset balances** at the time of each
  withdrawal.
- The net withdrawal target is specified in **today's currency** and is inflated using the
  average inflation rate (see §Inflation Adjustment).

#### Withdrawal Target Interpretation

The withdrawal input is treated as the **net amount the user wants to receive**. The engine
gross-ups the withdrawal as needed to cover ETF capital-gains taxes, so the portfolio is
debited by the gross amount while the user receives the net amount.

> **Example:** Target net = 3,000 EUR; if 40 % of withdrawals come from ETFs with a 40 %
> gains ratio, the required gross withdrawal is higher than 3,000 EUR. The engine iterates
> (or solves analytically) to find the gross amount that yields exactly 3,000 EUR net.

#### Inflation Adjustment

The net withdrawal target is defined in **today's currency**. For each retirement month,
inflate the target using the user-specified average inflation rate:

```
inflated_target = base_target × (1 + average_inflation_rate)^(months_since_current_age / 12)
```

> **Example:** Base target = 3,000 EUR, average inflation rate = 2 %, retirement age = 67,
> current age = 40 (27 years). First retirement year target:
> 3,000 × (1 + 0.02)^27 = 5,120 EUR per month.

---

## Default Annual Gain Rates

| Asset type | Default annual gain rate |
|---|---|
| ETF | 6.0 % |
| Pension / bAV | 4.0 % |
| Cash / daily account | 0.5 % |

These defaults are configurable at a global level and may be overridden per asset.

---

## Forecast Rules

### 1 — Forecast Horizon

Start at the first month of the user's current age and compute monthly values through the
month in which the user reaches the end age (inclusive). Fractional current age (e.g. 35y 4m)
means the forecast begins 4 months into the user's 36th year; age labels in the output
reflect this offset.

### 2 — Monthly Growth Rate

Convert the annual gain rate to a monthly equivalent:

```
monthly_rate = (1 + annual_rate)^(1/12) − 1
```

### 3 — Per-Month Calculation Order

For each asset, in each month:

1. **Add contribution** (pre-retirement months) **or deduct gross withdrawal share**
   (post-retirement months) from the balance.
2. **Apply monthly growth** to the resulting balance.

> Growth is applied *after* the cash-flow event, so a contribution made in month *t* earns
> growth starting in that same month.

### 4 — Withdrawal Allocation

The gross withdrawal is split across assets proportionally to their balances at the start of
the month (before the withdrawal is applied). If an asset's balance would be driven below
zero, it is floored at zero and the shortfall is redistributed proportionally among the
remaining assets. If total portfolio value is insufficient to cover the gross withdrawal,
all balances floor at zero and the shortfall is reported but not carried forward.

### 5 — ETF Withdrawal Tax

Tax applies **only to the ETF portion** of withdrawals. For each ETF asset:

1. **Track cost basis**: increase by each monthly contribution; never decrease due to
   market movement.
2. **Gains ratio** for a given month: `gains_ratio = max(0, (balance − cost_basis) / balance)`,
   where `balance > 0`; ratio is 0 when balance ≤ 0.
3. **Gains portion** of the gross withdrawal from this ETF:
   `gains_portion = gross_withdrawal_share × gains_ratio`
4. **Taxable gains**: `taxable_gains = gains_portion × 0.70`
   (partial exemption / *Teilfreistellung* of 30 %)
5. **Tax**: `tax = taxable_gains × 0.2625`
   (25 % *Kapitalertragssteuer* + 5 % *Solidaritätszuschlag* on the tax = 26.25 % effective)
6. **Net cashflow from this ETF**: `gross_withdrawal_share − tax`

> **Worked example** (single ETF, gross withdrawal = 1,000 EUR, gains ratio = 40 %):
> - Gains portion: 400 EUR
> - Taxable gains: 280 EUR (70 % of 400 EUR)
> - Tax: 73.50 EUR (26.25 % of 280 EUR)
> - Net cashflow: 926.50 EUR

When the withdrawal input is a net target, the engine must gross-up accordingly (see
§Withdrawal Target Interpretation).

### 6 — Cost Basis on Withdrawal

When an ETF asset is drawn down, reduce the cost basis proportionally:

```
cost_basis_reduction = gross_withdrawal_share × (cost_basis / balance)
```

This ensures the gains ratio reflects accumulated gains correctly in subsequent months.

### 7 — bAV Strategies

Two bAV strategies are supported:

1. **Transfer window**
   - Between the configured start/end ages, transfer an equal monthly fraction of the
     remaining bAV balance into ETF/Cash.
   - Tax applies to **100 % of the gains portion** at **26.25 %**.
   - The net transfer (after tax) is allocated to ETF and Cash based on the ETF ratio.

2. **Monthly gains income**
   - Starting at retirement, pay out the bAV monthly gains as income.
   - Tax applies to **100 % of the gains portion** at **26.25 %**.
   - The bAV balance does **not** grow from gains in months where income is paid out.

---

## Outputs

Each monthly record contains:

| Field | Description |
|---|---|
| Month index | Integer (0 = first forecast month). |
| Calendar month / year | Derived from current age and forecast start. |
| User age | Years + months at that point. |
| Per-asset balance | Balance for each asset after growth is applied. |
| Per-asset cost basis | ETF assets only; used for tax calculations. |
| Total portfolio balance | Sum of all asset balances. |
| Gross cashflow | Positive = total contributions; negative = total gross withdrawal. |
| Net cashflow | Same as gross cashflow for non-ETF months; reduced by ETF taxes in retirement. |
| Tax paid | Total tax deducted in the month (ETF + bAV). |

An optional **annual summary** (total portfolio value at year-end) may be derived from the
monthly data without additional calculation.

---

## Functional Requirements

### FR1 — Basic Forecast

Given a list of assets with current values, the app produces a monthly forecast of each
asset's balance and the total portfolio value from the current age through the end age,
using type-default gain rates where the user has not provided a rate.

### FR2 — Pre-retirement Contributions

The user can specify a monthly contribution per asset. Contributions are applied each month
from the current age up to (but not including) the retirement month and are reflected in the
forecast.

### FR3 — Post-retirement Withdrawals

Starting from the retirement month, the user's net monthly withdrawal target is deducted from
the portfolio. The gross withdrawal is allocated proportionally across assets; remaining
capital continues to grow. No asset balance may go below zero.

### FR4 — ETF Withdrawal Tax (German)

Withdrawals from ETF assets are subject to the German capital-gains tax rule: 26.25 % is
applied to 70 % of the gains portion of each ETF withdrawal. The tax reduces net cashflow,
and the withdrawal is grossed up so the user receives the specified net target.

### FR5 — Configurable Defaults

The user can override global default gain rates and set individual gain rates per asset
without affecting assets for which no override is provided.

### FR6 — Inflation-Adjusted Withdrawals

The user can specify an average inflation rate. The net monthly withdrawal target is
inflated from today's currency to each retirement month using compound inflation before
gross-up and withdrawal allocation.

### FR7 — bAV Strategies

The app supports bAV transfer windows (with configurable ages and ETF ratio) and bAV
monthly-gains income. bAV gains are fully taxable at 26.25 % in both strategies.

---

## Acceptance Criteria

| # | Criterion |
|---|---|
| AC1 | The forecast covers every calendar month from the current age to the end age inclusive, with per-asset and total portfolio values in each record. |
| AC2 | Contributions are applied in the correct month order (contribution then growth) for all pre-retirement months and stop in the retirement month. |
| AC3 | Withdrawals begin in the retirement month; no asset balance goes below zero; shortfalls are reported. |
| AC4 | ETF withdrawal tax is calculated per the formula in §Rule 5; the net cashflow field reflects the tax deduction. |
| AC5 | The gross withdrawal is computed such that the resulting net cashflow equals the user's specified net target. |
| AC6 | Cost basis for each ETF asset is updated correctly on contribution and on withdrawal. |
| AC7 | Where no gain rate is provided for an asset, the type default is used; user-provided overrides take precedence. |
| AC8 | Retirement withdrawals are inflated from today's currency using the specified average inflation rate before gross-up. |
| AC9 | bAV transfer windows allocate net balances to ETF/Cash and apply full-gains tax; bAV income pays out monthly gains with tax and no reinvestment. |
