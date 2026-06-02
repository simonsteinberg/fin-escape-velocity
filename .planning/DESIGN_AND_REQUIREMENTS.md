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

### State Pension

| Field | Required | Notes |
|---|---|---|
| Current monthly state pension (today-value at age 67) | Yes | Monthly gross state pension in today's currency if the user stopped working today. |
| Annual income (for pension points) | Yes | User-entered annual gross income. Used to compute pension points and the derived monthly growth per working year (display-only). |
| Monthly state pension growth per working year | Optional | Additional gross monthly pension earned for each year the user keeps working until retirement. If omitted, the UI computes an estimate from "Annual income" using configurable DRV parameters (see Configuration). This value is shown as a read-only display in the UI.
| State pension start age | Yes | Must be between 63 and 67 (inclusive). |

State pension taxation and reduction rules are driven from configuration (see §Configuration). Key DRV parameters include:

- `DRV_RENTENABSCHLAG_PRO_JAHR` — early-retirement penalty per year (fraction, e.g. 0.036 for 3.6 %/year);
- `DRV_RENTE_PRO_RENTENPUNKT_EURO` — euro value of one pension point (monthly);
- `DRV_DURCHSCHNITTS_JAHRESENTGELT_EURO` — reference annual income used to compute pension points;
- `DRV_MAXIMALE_RENTENPUNKTE_PRO_JAHR` — cap on pension points per year;
- `DRV_BRUTTO_RENTE_STEUERSATZ` — flat tax rate applied to gross pension (fraction).

The UI behaviour:

- The user may enter an explicit "Monthly state pension growth per working year" value, or provide their annual income. When annual income is provided (or both), the UI computes and displays a read-only estimate of the monthly growth per working year using the DRV parameters and shows it to the user.
- The UI additionally displays an estimated early-retirement penalty (read-only) for the selected state pension start age. The penalty is shown separately for clarity but is applied to the final gross pension in the forecast engine (see §Forecast Rules — State Pension reduction).

The forecast engine applies the configured tax rate and the early-retirement reduction when computing the net state pension used to reduce retirement withdrawal targets.
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
| Withdraw start age | If strategy = income | Age in years when monthly income payments begin. Before this age the bAV balance continues to compound at the configured annual gain rate and no income is paid out. |

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
| ETF | 5.0 % |
| Pension / bAV | 2.0 % |
| Cash / daily account | 0.5 % |

These defaults are configurable at a global level (via src/finev/config.json) and may be overridden per asset in the UI.
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
   - From the configured **withdraw start age** onwards, pay out the bAV monthly gains as income. Before that age the balance continues to compound at the annual gain rate and no income is paid.
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

### FR8 — State Pension Integration

The app supports a state pension stream that starts between age 63 and 67. Before start,
state pension is 0. From start onward, monthly state pension is:

```
gross_state_pension(month) =
  (
    current_state_pension_at_age_67_today
    + (working_years_until_retirement × pension_growth_per_working_year)
  ) × inflation_multiplier(month)
```

where `working_years_until_retirement` is derived from current age to retirement age.

You can choose to start your state penstion retirement earlier than 67, but the pension amount will be reduced by (100 x DRV_RENTENABSCHLAG_PRO_JAHR) % for each yeat of early retirement. For example, with the current DRV_RENTENABSCHLAG_PRO_JAHR of 3.6 %, starting the pension at 65 (2 years early) results in a reduction of 7.2 %.

```
gross_state_pension_reduced(month) =
  gross_state_pension(month) * (1 - DRV_RENTENABSCHLAG_PRO_JAHR × (67 - state_pension_start_age))
```

The net state pension is:

```
net_state_pension(month) = gross_state_pension_reduced(month) × (1 − DRV_BRUTTO_RENTE_STEUERSATZ)
```

For retirement months, the withdrawal target is reduced by net state pension and floored
at zero before ETF gross-up and allocation:

```
effective_withdrawal_target(month) =
  max(0, inflated_withdrawal_target(month) − net_state_pension(month))
```

# FR9 - Inheritance

(Planned: inheritance handling and probate-time transfers. Left intentionally terse for the current iteration.)

### FR10 — Asset activation toggle (what-if / scenario)

Each asset row in the UI shall expose an activation toggle (hide/show). When an asset is deactivated:

- It is excluded from contribution and withdrawal allocation calculations (treated as zero balance for the forecast) but the row remains visible in the UI for editing.
- Its settings and values are preserved so the user may re-activate the asset to see the effect on the forecast.
- The UI toggle state is persisted in cached UI state.

This enables quick "what-if" scenario analysis without removing assets from the configuration.

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
| AC9 | bAV transfer windows allocate net balances to ETF/Cash and apply full-gains tax; bAV income pays out monthly gains with tax and no reinvestment, starting from the configured withdraw start age (not from retirement). Before the withdraw start age the bAV INCOME balance compounds at the annual gain rate. |
| AC10 | State pension start age is validated to 63..67 and the configured DRV tax rate (`DRV_BRUTTO_RENTE_STEUERSATZ`) and early-retirement penalty (`DRV_RENTENABSCHLAG_PRO_JAHR`) are applied by the forecast engine when computing the net state pension that reduces retirement withdrawals. |
| AC11 | State pension amount reflects both earned growth until retirement and monthly inflation adjustment over forecast time. |
| AC12 | The UI exposes an annual income input and shows a read-only computed "monthly growth per working year" (derived from DRV parameters) and a separate estimated early-retirement penalty display; these are persisted where appropriate. |
| AC13 | Asset activation toggle: deactivating an asset excludes it from contributions and withdrawal allocation while preserving its row and persisted configuration; re-activating restores it to calculations. |
| AC14 | bAV withdrawal rules: no withdrawals may be taken from a bAV asset before its configured transfer/withdraw start age; the withdrawal allocation logic ignores bAV balances until they become withdrawable (transfer or income start). |

---

## Implementation Plan — State Pension & UI

1. Add a typed configuration loader (src/finev/config.py) that parses src/finev/config.json and exposes DRV and global defaults to the forecast engine and UI. Validate numeric ranges on load.
2. Extend domain model (src/finev/models.py) to include an `active: bool` flag on Asset and include state-pension related fields in WithdrawalPlan/StatePension as needed.
3. Modify the forecast engine (src/finev/forecast.py):
   - Use configuration values for DRV parameters and global defaults.
   - Compute net state pension per month by combining current pension, growth-until-retirement (config-driven or user-provided), inflation, early-retirement reduction, and configured pension tax rate. The early-retirement reduction is applied to the final gross pension amount (not to the per-year growth display).
   - Exclude assets marked inactive from contribution and withdrawal allocation calculations (treat balance as 0 for allocation purposes) while keeping their row state persisted.
   - Ensure bAV assets are excluded from withdrawal allocation until their transfer/withdraw start age is reached; transfers still move bAV balances to ETF/Cash during the configured window when in TRANSFER mode.
4. Update the NiceGUI UI (src/finev/ui.py):
   - Add an "active" toggle control (hide/show icon) on the left of each asset row to enable/disable the asset for forecasting. Persist this flag in the cached state file.
   - Add an annual income input under Profile and persist it; show a read-only computed monthly growth per working year and an estimated early-retirement penalty display in the Profile card. The read-only growth value is used as the default growth input for the pension if the user does not provide one explicitly.
   - Adjust bAV mode labels and inputs: show "Withdraw start age" when mode=INCOME and "Transfer start/end" when mode=TRANSFER; ensure the UI communicates that withdrawals from bAV are gated by the start age.
5. Add unit and integration tests:
   - Config loader validation and default fallbacks.
   - Pension computation: growth-from-income path, explicit growth path, early-retirement penalty application (final reduction), and tax application using configured DRV_BRUTTO_RENTE_STEUERSATZ.
   - Asset activation behavior: deactivated assets ignored in allocations and contributions; persisted toggle state.
   - bAV withdrawal gating: verify no bAV withdrawals before start age and correct transfer behavior during window.
6. Update documentation and the Acceptance Criteria in this document. Run formatting, lint, and test suites, and perform manual UI verification.


