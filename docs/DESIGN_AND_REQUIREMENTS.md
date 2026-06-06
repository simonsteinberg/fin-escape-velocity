# Wealth Forecast App — Design and Requirements

> **Status:** living document describing the *current* implementation of `finev`,
> reflecting what the code actually does today. Engineering rationale
> is in [SOFTWARE_ENGINEERING.md](../SOFTWARE_ENGINEERING.md); the operational
> checklist is in [CLAUDE.md](../CLAUDE.md).

---

## 1. Overview

Fin-Escape-Velocity (`finev`) is a German personal-finance forecasting tool. It
projects the monthly value of a user's assets from their current age through an
end age (default 100), accounting for:

- asset-specific compound growth,
- pre-retirement monthly contributions,
- post-retirement monthly withdrawals (net-target, grossed up for tax),
- German **Abgeltungssteuer** (capital-gains tax) + **Soli** on ETF gains, with
  the annual tax-free allowance (*Sparerpauschbetrag*) and partial exemption
  (*Teilfreistellung*),
- occupational pension (**bAV**) transfer/payout strategies,
- statutory state pension (**DRV**) income that offsets withdrawals,
- inheritance events with **Erbschaftsteuer** by heir class.

It ships as both a NiceGUI web app and a CLI, backed by a single pure forecasting
engine.

---

## 2. Goals and non-goals

### Goals

- Produce a **deterministic, monthly** forecast per asset and for the total
  portfolio, from current age through end age inclusive.
- Keep all domain math in a pure engine that is unit-testable without a UI.
- Drive every German tax constant from configuration, not code, so rule changes
  are data edits.
- Remain easy to extend: new asset types, per-month adjustments, and alternative
  tax regimes should slot in without rewriting the monthly loop.

### Non-goals (current iteration)

- No Monte-Carlo / stochastic modelling — growth rates are deterministic.
- No FX conversion — the currency field is a display label only.
- No multi-user accounts or server-side persistence beyond a local JSON state
  cache.
- No real-time market data; all inputs are user-supplied or configured.

---

## 3. Definitions

| Term | Meaning |
|---|---|
| **Current age** | Age at forecast start, in whole years plus optional months (0–11). |
| **Retirement age** | Age at which contributions stop and withdrawals begin (default 67). |
| **End age** | Last age included in the forecast (default 100). |
| **Monthly step** | Forecast granularity: one calculation per month. |
| **Cost basis** | Sum of contributions/capital paid into an asset; grows with contributions, shrinks proportionally on withdrawal, never written down by market loss. |
| **Gains** | `balance − cost_basis`; the taxable component of a withdrawal. |
| **Gross withdrawal** | Amount removed from the portfolio before tax. |
| **Net cashflow** | What the user actually receives/contributes after taxes in a month. |
| **bAV** | *Betriebliche Altersvorsorge* — occupational pension. |
| **bAV strategy** | How a bAV pays out: `transfer` (move balance to ETF/Cash over a window) or `income` (pay monthly gains). |
| **DRV** | *Deutsche Rentenversicherung* — the statutory state-pension system. |
| **Erbschaftsteuer** | German inheritance tax, by heir class and Freibetrag. |
| **Teilfreistellung** | Partial tax exemption on equity-fund gains (30%). |
| **Sparerpauschbetrag** | Annual capital-gains tax-free allowance (€1,000). |

---

## 4. Architecture

The domain flows in one direction:

```
models → config / forecast / pension → ui_state / ui_view → ui / cli / app
```

Business logic stays in the pure engine modules. The presentation modules
(`ui.py`, `cli.py`, `app.py`) only call the engine and render results — they
contain no domain math.

| Module | Role | Pure? |
|---|---|---|
| [`models.py`](../src/finev/models.py) | Domain types (`UserProfile`, `Asset`, `StatePension`, `WithdrawalPlan`) and enums (`AssetType`, `BAVStrategy`, `AllocationStrategy`, `InheritanceRelationship`); default gain rates. | ✅ |
| [`config.py`](../src/finev/config.py) | Loads and validates `config.json` into frozen typed dataclasses; exposes ETF/DRV/Erbschaftsteuer parameters and derived rates. | ✅ |
| [`forecast.py`](../src/finev/forecast.py) | The calculation engine: validates inputs, builds an immutable per-run context, runs the monthly pipeline, returns a pandas `DataFrame`. | ✅ |
| [`pension.py`](../src/finev/pension.py) | DRV state-pension **display** estimates (growth-per-working-year, early-retirement penalty, pension at start). No I/O. | ✅ |
| [`ui_state.py`](../src/finev/ui_state.py) | UI defaults, JSON state persistence, value coercion/clamping, row normalization, row→`Asset` conversion. No NiceGUI dependency. | ✅ |
| [`ui_view.py`](../src/finev/ui_view.py) | Presentation helpers: currency formatting, chart/table option shaping, yearly display frame. No NiceGUI dependency. | ✅ |
| [`ui.py`](../src/finev/ui.py) | NiceGUI page. The `_WealthPage` controller holds widget refs + state and binds event handlers as methods; `build_wealth_page()` is the thin entry point. | ❌ (presentation) |
| [`app.py`](../src/finev/app.py) | NiceGUI server launcher; auto-selects a free port in 8081–8130; honours `WEALTH_APP_PORT`. | ❌ (I/O) |
| [`cli.py`](../src/finev/cli.py) | Console entry point: builds a default scenario, prints a yearly summary table. | ❌ (I/O) |

`config.json` is the authoritative source for all German tax constants. When a
tax rule changes, edit the JSON — not the Python.

### Engine internals

`forecast_wealth()` is structured as an ordered pipeline of small pure step
functions over a shared mutable `_MonthlyState`, parameterised by an immutable
`_EngineParams`:

1. `_apply_inheritance` — credit net inheritance proceeds due this month.
2. `_apply_contributions` *(pre-retirement)* **or** `_apply_withdrawal` *(post-retirement)*.
3. `_apply_bav_transfer` — move an in-window slice of each TRANSFER bAV to ETF/Cash.
4. `_apply_bav_income` — pay out monthly gains from INCOME bAV (freezes its principal).
5. `_apply_growth` — compound each balance by its monthly rate (skipping frozen assets).

This shape realises the design intent that new per-month adjustments and asset
types slot in as additional steps/handlers rather than edits to a monolithic loop.

---

## 5. Inputs

### 5.1 User profile (`UserProfile`)

| Field | Default | Notes |
|---|---|---|
| Current age (years) | — (40 in UI) | Required; whole years. |
| Current age (months) | 0 | 0–11; fractional start offset. |
| Retirement age | 67 | Contributions stop / withdrawals begin. |
| End age | 100 | Must be ≥ retirement age and > current age. |
| Currency | `EUR` | Display label only; no FX. |
| Average inflation rate | 2% (UI) / 0.02 (model) | Annual; inflates withdrawal targets and state pension. Must be > −100%. |
| Debt interest rate | 8% (UI) / 0.08 (model) | Annual rate charged on negative total wealth (debt); compounds monthly. Must be ≥ 0. |

### 5.2 State pension (`StatePension` + UI-derived display)

| Field | Required | Notes |
|---|---|---|
| Current monthly amount (today-value) | Yes | Gross monthly state pension if the user stopped working today. |
| Annual income | Yes (UI) | Drives the read-only pension-points estimate. |
| Monthly growth per working year | Derived | Extra gross monthly pension per additional working year. Computed in `pension.py` from annual income and DRV params; shown read-only. |
| Start age | Yes | Must be **63–67** inclusive. |
| Tax rate | Optional | Defaults to `DRV_BRUTTO_RENTE_STEUERSATZ` when omitted; must be in `[0, 1)`. |

DRV parameters (from `config.json`): `DRV_RENTENABSCHLAG_PRO_JAHR` (early-retirement
penalty per year), `DRV_RENTE_PRO_RENTENPUNKT_EURO`, `DRV_DURCHSCHNITTS_JAHRESENTGELT_EURO`,
`DRV_MAXIMALE_RENTENPUNKTE_PRO_JAHR`, `DRV_BRUTTO_RENTE_STEUERSATZ`.

The UI shows three read-only displays: the computed monthly growth per working
year, the estimated early-retirement penalty for the chosen start age, and the
estimated net pension at start. The penalty is shown separately but applied to
the gross pension by the engine (see §7.6).

### 5.3 Assets (`Asset`)

Each asset row carries a name, a type (`ETF`, `bAV`, `Cash`, `Inheritance`), a
current value, an optional annual gain-rate override, a monthly contribution, and
an `active` toggle. ETF/Cash/bAV also carry *unrealized gains* in the UI, which is
converted to an `initial_cost_basis = current_value − unrealized_gains`.

**bAV-specific fields:** `bav_strategy` (`transfer`/`income`),
`bav_transfer_start_age`, `bav_transfer_end_age`, `bav_transfer_etf_ratio`
(share to ETF; remainder to Cash). For `income`, the start age is the
"withdraw start age".

**Inheritance-specific fields:** `inheritance_gross_amount`, `inheritance_age`
(year the event occurs), `inheritance_relationship` (heir class).

#### Default annual gain rates (`models.DEFAULT_ANNUAL_GAIN_RATES`)

| Asset type | Default annual gain rate |
|---|---|
| ETF | 5.0% |
| bAV | 2.0% |
| Cash | 0.5% |
| Inheritance | 0.0% (no running balance) |

Defaults are configurable per-asset in the UI; the type default is used when no
override is given.

### 5.4 Withdrawals (`WithdrawalPlan`)

- A single **net monthly withdrawal target**, interpreted as the amount the user
  wants to *receive* (the engine grosses it up for ETF tax).
- Allocation strategy: **proportional** to withdrawable asset balances. (The
  `AllocationStrategy` enum exists for future strategies; only `PROPORTIONAL` is
  currently valid.)
- The target is specified in **today's currency** and inflated to each retirement
  month.
- An optional `StatePension` whose net amount offsets the target each month.

---

## 6. Configuration (`config.json`)

Validated on load into frozen dataclasses (`FinevConfig` → `DrvConfig`,
`EtfTaxConfig`, `InheritanceTaxConfig`). Fractions are range-checked `[0,1]`,
euro amounts checked non-negative/positive as appropriate.

**ETF tax** — effective rate = `abgeltungssteuer × (1 + soli + kirchensteuer)`
(currently 25% × 1.055 = **26.25%**); taxable share = `1 − teilfreistellung`
(currently **70%**); annual allowance = **€1,000**.

**Erbschaftsteuer** — per heir class (I/II/III) a Freibetrag plus a **flat**
(non-marginal) rate chosen by which bracket the taxable amount (gross − Freibetrag)
falls into. Thresholds: 75k / 300k / 600k / 6M / 13M / 26M.

| Relationship | Class | Freibetrag |
|---|---|---|
| Ehegatte / Lebenspartner | I | €500,000 |
| Kind / Stiefkind | I | €400,000 |
| Enkel | I | €200,000 |
| Elternteil | I | €100,000 |
| Klasse II (Geschwister, Nichten, Neffen…) | II | €20,000 |
| Klasse III (übrige) | III | €20,000 |

**Privatinsolvenz** — `PRIVATINSOLVENZ_SCHWELLE_EURO` (currently **€100,000**, a
positive amount) is the most negative total wealth a forecast may reach. It is a
config-only constant (no UI control). See §7.10.

---

## 7. Forecast rules

### 7.1 Horizon and timeline

Ages are tracked in months. The forecast runs from `start_age_months`
(`current_age_years × 12 + current_age_months`) through `end_age × 12` inclusive.
Month 0 is the seeded starting state (no cashflow applied); month ≥ 1 runs the
full pipeline. A fractional current age shifts the month-in-year of every row.

### 7.2 Monthly growth rate

`monthly_rate = (1 + annual_rate)^(1/12) − 1`, applied **after** the month's
cashflow events so a contribution earns growth in the same month.

### 7.3 Contributions (pre-retirement)

Each active, non-inheritance asset receives its monthly contribution, added to
both balance and cost basis; the sum is recorded as positive net cashflow.

### 7.4 Withdrawals (post-retirement)

1. Inflate the base net target to the current month.
2. Subtract the **net state pension** for the month; floor at 0.
3. Determine **withdrawable** assets: ETF and Cash always; bAV only once its
   transfer/withdraw start age is reached.
4. **Gross up** the net target to cover ETF capital-gains tax on the taxable
   gains portion, accounting for any remaining annual allowance (`_gross_up_withdrawal`).
5. Allocate the grossed-up amount **proportionally** by balance across
   withdrawable assets, capped at the total available (each balance floors at 0).
6. Reduce each asset's cost basis proportionally to the fraction withdrawn.
7. Tax the ETF taxable gains beyond the remaining allowance at the effective
   rate; record taxes and net cashflow.
8. If the assets could not cover the full net target, the unmet remainder is
   **borrowed**: it is added to the running debt and recorded as net cashflow, so
   total wealth is allowed to go below zero (see §7.10).

### 7.5 ETF withdrawal tax

Applies only to the ETF gains portion of a withdrawal:

- gains ratio (per ETF, balance > 0): `max(0, (balance − cost_basis) / balance)`
- taxable gains: `gains_portion × taxable_share` (×0.70)
- the annual allowance (€1,000) is consumed first each calendar year; only the
  excess is taxed
- tax: `taxable_after_allowance × effective_rate` (×0.2625)

The allowance resets at the start of each forecast year.

### 7.6 State pension

For months at/after the start age:

```
accrued       = current_monthly + working_years × growth_per_working_year
gross(month)  = accrued × inflation_multiplier(month) × (1 − rentenabschlag × (67 − start_age))
net(month)    = gross(month) × (1 − tax_rate)
```

`working_years` is derived from current→retirement age. `tax_rate` defaults to
`DRV_BRUTTO_RENTE_STEUERSATZ`. The net amount reduces the withdrawal target
(§7.4 step 2). The display-only estimates in `pension.py` mirror this for the UI
but are computed independently.

### 7.7 bAV strategies

- **Transfer:** between `bav_transfer_start_age` and `bav_transfer_end_age`
  (inclusive, to the last month of the end-age year), transfer an equal monthly
  fraction (`1 / remaining_months`) of the bAV balance. The gains portion is
  taxed at the full effective rate (no Teilfreistellung), and the net transfer is
  split to ETF/Cash by `bav_transfer_etf_ratio`. A transfer requires at least one
  ETF target (if ratio > 0) and one Cash target (if ratio < 1).
- **Income:** from the withdraw start age, pay out the bAV's monthly gains as
  income, taxed at the full effective rate; the principal is **frozen** (does not
  compound) in payout months. Before the start age, it compounds normally.

### 7.8 Inheritance

At the configured `inheritance_age` (in the matching month), an active inheritance
asset with a positive gross amount triggers an event: Erbschaftsteuer is computed
by relationship (§6), and the **net** proceeds are credited to ETF assets (or
Cash if no ETF exists), increasing both balance and cost basis. Inheritance
assets hold no running balance and are excluded from output columns.

### 7.9 Asset activation toggle

Deactivating an asset (`active = false`) excludes it from contributions,
withdrawal allocation, transfers, and as a transfer/inheritance target — it is
treated as a zero balance — while its row and configuration remain in the UI and
persisted cache, so it can be re-activated to compare scenarios.

### 7.10 Debt and Privatinsolvenz (negative total wealth)

When a month's withdrawal exceeds the available assets, the unmet net need is
booked as **debt** — a running, non-negative balance held in engine state. Total
wealth is the asset sum **minus** this debt, so it may go negative once assets
are exhausted. Each month any outstanding debt compounds by the monthly
equivalent of the profile's `debt_interest_rate` (`_apply_debt_interest`). Net
inheritance proceeds **repay** outstanding debt before the remainder is invested.
Debt is not a separate output column; it is reflected only in a reduced (possibly
negative) `total`.

**Privatinsolvenz floor.** As the last step of each month, the debt is capped so
that total wealth cannot fall below `-PRIVATINSOLVENZ_SCHWELLE_EURO` (§6):
`_apply_insolvency_floor` sets `debt = min(debt, asset_total + floor)`. Because
the cap is applied to the carried-over state (not just the output row), a capped
debt **stops compounding** — so it stays pinned at the floor while insolvent, yet
a later inheritance large enough to repay the capped debt can lift the forecast
back into the green. A forecast may therefore enter Privatinsolvenz, escape via
an inheritance, and re-enter it later; the total stays at the floor for any span
where no rescue follows, including permanently once none can.

---

## 8. Outputs

`forecast_wealth()` returns a pandas `DataFrame`, one row per month, with columns:

| Column | Description |
|---|---|
| `month_index` | 0-based month from forecast start. |
| `age_years`, `age_months` | User age at that row. |
| `net_cashflow` | Net received (−)/contributed (+) that month, after taxes. |
| `taxes` | Total tax deducted that month (ETF + bAV + inheritance). |
| *per-asset* | Balance for each non-inheritance asset (column = asset name). |
| `total` | Sum of all non-inheritance asset balances, minus any outstanding debt; may be negative but never below the Privatinsolvenz floor (§7.10). |

Presentation layers derive a **yearly** view (`ui_view.yearly_display_frame`,
every 12th month; `cli.summarize_yearly`, aggregated per age-year) for the chart,
table, and console output.

---

## 9. User interfaces

### 9.1 Web app (NiceGUI)

`mise run app` launches `python -m finev.app`, which serves the page at `/` on the
first free port from 8081 (override with `WEALTH_APP_PORT`). The page
(`_WealthPage`) has a left sidebar (Profile, State pension, Assets cards with an
add/reset control and per-row editors) and a right panel (summary label, ECharts
line chart, yearly table). Edits are debounced (~0.5s) before re-running the
forecast; structural changes (type/strategy/active/relationship, add/remove,
reset) re-render immediately. UI state is persisted to a local JSON cache
(`.cache/finev/wealth_state.json`, or `WEALTH_APP_STATE_PATH`).

### 9.2 CLI

`mise run run` runs `cli.run()`: a default scenario (age 40→100, ETF/bAV/Cash,
€3,000/mo withdrawal) printed as a yearly summary table of per-asset balances,
total, taxes, and net cashflow.

---

## 10. Functional requirements

| # | Requirement |
|---|---|
| FR1 | Monthly forecast of each asset balance and the portfolio total from current age to end age, using type-default gain rates where no override is given. |
| FR2 | Pre-retirement monthly contributions per asset, applied (contribution then growth) until the retirement month. |
| FR3 | Post-retirement net withdrawal target deducted proportionally across withdrawable assets; individual balances floor at zero, while any unmet need is borrowed so total wealth may go negative. |
| FR4 | German ETF capital-gains tax (26.25% on 70% of gains) with the €1,000 annual allowance; net cashflow reflects tax; withdrawals are grossed up to the net target. |
| FR5 | Configurable default gain rates with per-asset overrides. |
| FR6 | Inflation-adjusted withdrawal targets from today's currency to each retirement month. |
| FR7 | bAV transfer windows (configurable ages + ETF ratio) and bAV monthly-gains income; bAV gains fully taxed at 26.25%. |
| FR8 | State-pension stream starting at age 63–67, with earned growth, inflation, early-retirement reduction, and configured tax rate; net pension offsets withdrawals. |
| FR9 | Inheritance events at a configured age, taxed by Erbschaftsteuer class/Freibetrag; net proceeds credited to ETF (then Cash). |
| FR10 | Per-asset activation toggle for what-if scenarios; deactivated assets excluded from calculations but preserved and persisted. |
| FR11 | Inputs validated at the boundary (`forecast.py` validators, `config.py` on load, `ui_state` coercion); invalid inputs fail loudly. |
| FR12 | When withdrawals exhaust the assets, the unmet need is borrowed so total wealth can go negative; the debt compounds monthly at the configured annual debt interest rate and is repaid by net inheritance proceeds. |
| FR13 | Total wealth is floored at the configured Privatinsolvenz threshold (`-PRIVATINSOLVENZ_SCHWELLE_EURO`); the capped debt stops compounding, so a later inheritance can repay it and lift the forecast back out of insolvency, and the total stays at the floor for any span without such a rescue. |

---

## 11. Acceptance criteria

| # | Criterion |
|---|---|
| AC1 | Forecast covers every month from current to end age inclusive, with per-asset and total values per row. |
| AC2 | Contributions applied in order (contribution then growth) for all pre-retirement months; stop at retirement. |
| AC3 | Withdrawals begin at the retirement month; individual asset balances floor at zero, and any unmet need accrues as debt that drives total wealth negative and compounds at the debt interest rate, but never below the Privatinsolvenz floor. |
| AC12 | Total wealth never drops below `-PRIVATINSOLVENZ_SCHWELLE_EURO`; a forecast can enter the floor, escape via a later inheritance that repays the capped debt, and re-enter it, staying pinned at the floor whenever no rescue follows. |
| AC4 | ETF withdrawal tax matches §7.5 (allowance before tax); net cashflow reflects the deduction. |
| AC5 | Gross withdrawal is computed so net cashflow equals the user's net target (subject to available balance). |
| AC6 | Cost basis updates correctly on contribution and proportionally on withdrawal. |
| AC7 | Type-default gain rate used where no override is given; overrides take precedence. |
| AC8 | Retirement withdrawals inflated from today's currency before gross-up and allocation. |
| AC9 | bAV transfer allocates net balance to ETF/Cash with full-gains tax; bAV income pays monthly gains (no reinvestment) from the withdraw start age, compounding before it. |
| AC10 | State pension start age validated to 63–67; configured tax rate and early-retirement penalty applied by the engine. |
| AC11 | State pension reflects earned growth until retirement and monthly inflation over forecast time. |
| AC12 | UI shows read-only computed monthly growth per working year, an estimated early-retirement penalty, and net pension at start. |
| AC13 | Deactivating an asset excludes it from contributions/allocation/transfers while preserving its row and persisted config; reactivation restores it. |
| AC14 | No withdrawals from a bAV before its transfer/withdraw start age; allocation ignores bAV until withdrawable. |
| AC15 | Inheritance below the Freibetrag is tax-free; above it the correct flat bracket rate by class applies; inactive inheritance is not injected. |

Each criterion is exercised by the test suite under [`tests/finev/`](../tests/finev/)
(notably `test_forecast.py`, `test_forecast_golden.py`, `test_validation.py`,
`test_config.py`, `test_pension.py`, `test_ui_*.py`).

---

## 12. Extensibility and design constraints

- **Engine/UI separation:** presentation modules must contain no domain math;
  business logic stays in `forecast`/`config`/`pension`.
- **Per-month hook points:** new monthly adjustments are added as pipeline steps
  in `forecast_wealth`, not as edits to a monolithic loop.
- **Asset types:** adding a type means adding handling to the relevant step
  functions (and UI rows), not branching everywhere.
- **Pluggable tax rules:** ETF, DRV, and Erbschaftsteuer parameters are
  config-driven and replaceable; alternative regimes are a config/dataclass swap.
- **Typed models at the boundary:** inputs/outputs are explicit frozen dataclasses
  and enums; illegal states (e.g. unknown strategy/relationship) are rejected at
  validation time.

---

## 13. Quality gates

Reproducible via `mise` tasks (the same gates CI runs): `format-check`, `lint`
(Ruff), `typecheck` (mypy, strict-ish), `test` (pytest), and `coverage`
(minimum **58%**). `mise run check` runs them together. See
[CLAUDE.md](../CLAUDE.md) for the pre-commit and PR workflow.
