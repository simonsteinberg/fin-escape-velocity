"""Load and validate configuration values used by forecasts."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import json
from pathlib import Path
from typing import Any


CONFIG_PATH = Path(__file__).with_name("config.json")
MAX_EARLY_RETIREMENT_YEARS = 4


@dataclass(frozen=True)
class DrvConfig:
    """Configuration for state pension (DRV) calculations."""

    rentenabschlag_pro_jahr: float
    rente_pro_rentenpunkt_euro: float
    durchschnitts_jahresentgelt_euro: float
    maximale_rentenpunkte_pro_jahr: float
    brutto_rente_steuersatz: float


@dataclass(frozen=True)
class EtfTaxConfig:
    """Configuration for ETF taxation."""

    abgeltungssteuer: float
    solidaritaetszuschlag: float
    kirchensteuer: float
    steuerfreibetrag_euro: float
    teilfreistellung: float

    @property
    def effective_tax_rate(self) -> float:
        """Return the effective tax rate on taxable ETF gains."""
        return self.abgeltungssteuer * (
            1 + self.solidaritaetszuschlag + self.kirchensteuer
        )

    @property
    def taxable_share(self) -> float:
        """Return the share of ETF gains that is taxable."""
        return 1 - self.teilfreistellung


@dataclass(frozen=True)
class InheritanceTaxConfig:
    """Configuration for inheritance tax thresholds and rates."""

    freibetrag_euro: float
    satz_i_bis_75k_euro: float
    satz_i_bis_300k_euro: float
    satz_i_bis_600k_euro: float
    satz_i_bis_6m_euro: float


@dataclass(frozen=True)
class FinevConfig:
    """Typed configuration values used across the forecast."""

    drv: DrvConfig
    etf: EtfTaxConfig
    inheritance_tax: InheritanceTaxConfig

    @property
    def capital_gains_tax_rate(self) -> float:
        """Return the effective capital gains tax rate."""
        return self.etf.effective_tax_rate


def load_config(path: Path | None = None) -> FinevConfig:
    """Load and validate configuration from a JSON file."""
    config_path = path or CONFIG_PATH
    with config_path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)
    if not isinstance(raw, dict):
        raise ValueError("Config file must contain a JSON object.")
    config = _parse_config(raw)
    _validate_config(config)
    return config


@lru_cache(maxsize=1)
def get_config() -> FinevConfig:
    """Return the cached configuration values."""
    return load_config()


def _parse_config(raw: dict[str, Any]) -> FinevConfig:
    drv = DrvConfig(
        rentenabschlag_pro_jahr=_require_float(
            raw, "DRV_RENTENABSCHLAG_PRO_JAHR"
        ),
        rente_pro_rentenpunkt_euro=_require_float(
            raw, "DRV_RENTE_PRO_RENTENPUNKT_EURO"
        ),
        durchschnitts_jahresentgelt_euro=_require_float(
            raw, "DRV_DURCHSCHNITTS_JAHRESENTGELT_EURO"
        ),
        maximale_rentenpunkte_pro_jahr=_require_float(
            raw, "DRV_MAXIMALE_RENTENPUNKTE_PRO_JAHR"
        ),
        brutto_rente_steuersatz=_require_float(
            raw, "DRV_BRUTTO_RENTE_STEUERSATZ"
        ),
    )
    etf = EtfTaxConfig(
        abgeltungssteuer=_require_float(raw, "ETF_ABGELTUNGSSTEUER"),
        solidaritaetszuschlag=_require_float(raw, "ETF_SOLIDARITAETSZUSCHLAG"),
        kirchensteuer=_require_float(raw, "ETF_KIRCHENSTEUER"),
        steuerfreibetrag_euro=_require_float(raw, "ETF_STEUERFREIBETRAG_EURO"),
        teilfreistellung=_require_float(raw, "ETF_TEILFREISTELLUNG"),
    )
    inheritance_tax = InheritanceTaxConfig(
        freibetrag_euro=_require_float(raw, "ERBSCHAFTSTEUER_FREIBETRAG_EURO"),
        satz_i_bis_75k_euro=_require_float(
            raw, "ERBSCHAFTSTEUER_SATZ_I_BIS_75K_EURO"
        ),
        satz_i_bis_300k_euro=_require_float(
            raw, "ERBSCHAFTSTEUER_SATZ_I_BIS_300K_EURO"
        ),
        satz_i_bis_600k_euro=_require_float(
            raw, "ERBSCHAFTSTEUER_SATZ_I_BIS_600K_EURO"
        ),
        satz_i_bis_6m_euro=_require_float(
            raw, "ERBSCHAFTSTEUER_SATZ_I_BIS_6M_EURO"
        ),
    )
    return FinevConfig(drv=drv, etf=etf, inheritance_tax=inheritance_tax)


def _require_float(raw: dict[str, Any], key: str) -> float:
    if key not in raw:
        raise KeyError(f"Config missing required key: {key}")
    value = raw[key]
    if not isinstance(value, (int, float)):
        raise ValueError(f"Config value for {key} must be a number.")
    return float(value)


def _validate_config(config: FinevConfig) -> None:
    _require_fraction(
        config.drv.rentenabschlag_pro_jahr, "DRV_RENTENABSCHLAG_PRO_JAHR"
    )
    _require_positive(
        config.drv.rente_pro_rentenpunkt_euro, "DRV_RENTE_PRO_RENTENPUNKT_EURO"
    )
    _require_positive(
        config.drv.durchschnitts_jahresentgelt_euro,
        "DRV_DURCHSCHNITTS_JAHRESENTGELT_EURO",
    )
    _require_positive(
        config.drv.maximale_rentenpunkte_pro_jahr,
        "DRV_MAXIMALE_RENTENPUNKTE_PRO_JAHR",
    )
    _require_fraction(
        config.drv.brutto_rente_steuersatz, "DRV_BRUTTO_RENTE_STEUERSATZ"
    )

    if 1 - config.drv.rentenabschlag_pro_jahr * MAX_EARLY_RETIREMENT_YEARS < 0:
        raise ValueError(
            "DRV_RENTENABSCHLAG_PRO_JAHR is too high for the minimum pension age."
        )

    _require_fraction(config.etf.abgeltungssteuer, "ETF_ABGELTUNGSSTEUER")
    _require_fraction(
        config.etf.solidaritaetszuschlag, "ETF_SOLIDARITAETSZUSCHLAG"
    )
    _require_fraction(config.etf.kirchensteuer, "ETF_KIRCHENSTEUER")
    _require_non_negative(
        config.etf.steuerfreibetrag_euro, "ETF_STEUERFREIBETRAG_EURO"
    )
    _require_fraction(config.etf.teilfreistellung, "ETF_TEILFREISTELLUNG")

    _require_fraction(config.etf.effective_tax_rate, "ETF effective tax rate")
    _require_fraction(config.etf.taxable_share, "ETF taxable share")

    _require_non_negative(
        config.inheritance_tax.freibetrag_euro,
        "ERBSCHAFTSTEUER_FREIBETRAG_EURO",
    )
    _require_fraction(
        config.inheritance_tax.satz_i_bis_75k_euro,
        "ERBSCHAFTSTEUER_SATZ_I_BIS_75K_EURO",
    )
    _require_fraction(
        config.inheritance_tax.satz_i_bis_300k_euro,
        "ERBSCHAFTSTEUER_SATZ_I_BIS_300K_EURO",
    )
    _require_fraction(
        config.inheritance_tax.satz_i_bis_600k_euro,
        "ERBSCHAFTSTEUER_SATZ_I_BIS_600K_EURO",
    )
    _require_fraction(
        config.inheritance_tax.satz_i_bis_6m_euro,
        "ERBSCHAFTSTEUER_SATZ_I_BIS_6M_EURO",
    )


def _require_fraction(value: float, name: str) -> None:
    if not 0 <= value <= 1:
        raise ValueError(f"{name} must be between 0 and 1 (inclusive).")


def _require_positive(value: float, name: str) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be greater than 0.")


def _require_non_negative(value: float, name: str) -> None:
    if value < 0:
        raise ValueError(f"{name} must be non-negative.")
