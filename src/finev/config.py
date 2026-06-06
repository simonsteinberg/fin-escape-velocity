"""Load and validate configuration values used by forecasts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from finev.models import InheritanceRelationship

CONFIG_PATH = Path(__file__).with_name("config.json")
MAX_EARLY_RETIREMENT_YEARS = 4

# Ordered taxable-amount thresholds for the Erbschaftsteuer brackets.
_ERBSCHAFTSTEUER_THRESHOLDS = [
    75_000.0,
    300_000.0,
    600_000.0,
    6_000_000.0,
    13_000_000.0,
    26_000_000.0,
]


@dataclass(frozen=True)
class DrvConfig:
    """Configuration for state pension (DRV) calculations."""

    rentenabschlag_pro_jahr: float
    rente_pro_rentenpunkt_euro: float
    durchschnitts_jahresentgelt_euro: float
    maximale_rentenpunkte_pro_jahr: float
    brutto_rente_steuersatz: float


@dataclass(frozen=True)
class VblConfig:
    """Configuration for VBLklassik occupational pension calculations.

    Attributes:
        rente_pro_punkt_euro: Gross monthly pension per Versorgungspunkt, for
            life (the VBL point value, e.g. ``4.0`` €/point).
        brutto_rente_steuersatz: Default flat tax rate applied to the gross VBL
            pension (it is fully income-taxed under § 22 Nr. 5 EStG). Used when an
            asset does not override it.
    """

    rente_pro_punkt_euro: float
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
class InsolvencyConfig:
    """Configuration for the Privatinsolvenz (personal insolvency) floor.

    Attributes:
        schwelle_euro: The most negative total wealth a forecast may reach. Once
            the debt would drive total wealth below ``-schwelle_euro`` it is
            capped here (Privatinsolvenz); the total stays at the floor unless a
            later inheritance repays the capped debt.
    """

    schwelle_euro: float


@dataclass(frozen=True)
class InheritanceTaxBrackets:
    """Flat tax rates for each Erbschaftsteuer bracket.

    German Erbschaftsteuer is not a marginal tax: the applicable rate is applied
    to the entire taxable amount (gross minus Freibetrag).  The bracket is
    determined by which range the taxable amount falls into.
    """

    bis_75k: float
    bis_300k: float
    bis_600k: float
    bis_6m: float
    bis_13m: float
    bis_26m: float
    ueber_26m: float

    def rate_for(self, taxable_amount: float) -> float:
        """Return the flat tax rate that applies to *taxable_amount*.

        Args:
            taxable_amount: Amount after subtracting the Freibetrag.

        Returns:
            Applicable flat rate as a decimal fraction.
        """
        rates = [
            self.bis_75k,
            self.bis_300k,
            self.bis_600k,
            self.bis_6m,
            self.bis_13m,
            self.bis_26m,
            self.ueber_26m,
        ]
        # There are 7 rates but only 6 thresholds: the final rate applies to any
        # amount above the last threshold, so the lengths differ by design.
        for threshold, rate in zip(
            _ERBSCHAFTSTEUER_THRESHOLDS, rates, strict=False
        ):
            if taxable_amount <= threshold:
                return rate
        return rates[-1]


@dataclass(frozen=True)
class InheritanceTaxRelationship:
    """Freibetrag and tax brackets for a specific heir relationship.

    Attributes:
        freibetrag_euro: Tax-free allowance in euros.
        brackets: Applicable tax rates per bracket.
    """

    freibetrag_euro: float
    brackets: InheritanceTaxBrackets


@dataclass(frozen=True)
class InheritanceTaxConfig:
    """Inheritance tax configuration for all heir relationship types.

    Attributes:
        ehegatte: Ehegatten / eingetragene Lebenspartner (Klasse I, 500 000 €).
        kind: Kinder und Stiefkinder (Klasse I, 400 000 €).
        enkel: Enkel (Klasse I, 200 000 €).
        elternteil: Eltern (Klasse I, 100 000 €).
        klasse_ii: Geschwister, Nichten, Neffen etc. (Klasse II, 20 000 €).
        klasse_iii: Alle übrigen Erben (Klasse III, 20 000 €).
    """

    ehegatte: InheritanceTaxRelationship
    kind: InheritanceTaxRelationship
    enkel: InheritanceTaxRelationship
    elternteil: InheritanceTaxRelationship
    klasse_ii: InheritanceTaxRelationship
    klasse_iii: InheritanceTaxRelationship

    def compute_tax(
        self,
        gross_amount: float,
        relationship: InheritanceRelationship,
    ) -> float:
        """Return the Erbschaftsteuer for a given gross inheritance.

        Args:
            gross_amount: Total inherited amount before tax.
            relationship: Heir relationship determining Freibetrag and brackets.

        Returns:
            Tax amount in the same currency as *gross_amount*.

        Raises:
            KeyError: If *relationship* is not a recognised relationship.
        """
        rel_map: dict[InheritanceRelationship, InheritanceTaxRelationship] = {
            InheritanceRelationship.EHEGATTE: self.ehegatte,
            InheritanceRelationship.KIND: self.kind,
            InheritanceRelationship.ENKEL: self.enkel,
            InheritanceRelationship.ELTERNTEIL: self.elternteil,
            InheritanceRelationship.KLASSE_II: self.klasse_ii,
            InheritanceRelationship.KLASSE_III: self.klasse_iii,
        }
        if relationship not in rel_map:
            raise KeyError(
                f"Unknown inheritance relationship: {relationship!r}"
            )
        rel = rel_map[relationship]
        taxable = max(gross_amount - rel.freibetrag_euro, 0.0)
        if taxable == 0.0:
            return 0.0
        return taxable * rel.brackets.rate_for(taxable)


@dataclass(frozen=True)
class FinevConfig:
    """Typed configuration values used across the forecast."""

    drv: DrvConfig
    vbl: VblConfig
    etf: EtfTaxConfig
    inheritance_tax: InheritanceTaxConfig
    insolvency: InsolvencyConfig

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


def _parse_brackets(
    raw: dict[str, Any], klasse: str
) -> InheritanceTaxBrackets:
    """Parse one Erbschaftsteuer bracket set for a given tax class.

    Args:
        raw: Decoded config JSON object.
        klasse: Tax-class token used in the config keys (``"I"``, ``"II"`` or
            ``"III"``), e.g. ``ERBSCHAFTSTEUER_KLASSE_<klasse>_BIS_75K``.

    Returns:
        Parsed bracket rates for the class.
    """
    prefix = f"ERBSCHAFTSTEUER_KLASSE_{klasse}"
    return InheritanceTaxBrackets(
        bis_75k=_require_float(raw, f"{prefix}_BIS_75K"),
        bis_300k=_require_float(raw, f"{prefix}_BIS_300K"),
        bis_600k=_require_float(raw, f"{prefix}_BIS_600K"),
        bis_6m=_require_float(raw, f"{prefix}_BIS_6M"),
        bis_13m=_require_float(raw, f"{prefix}_BIS_13M"),
        bis_26m=_require_float(raw, f"{prefix}_BIS_26M"),
        ueber_26m=_require_float(raw, f"{prefix}_UEBER_26M"),
    )


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
    vbl = VblConfig(
        rente_pro_punkt_euro=_require_float(raw, "VBL_RENTE_PRO_PUNKT_EURO"),
        brutto_rente_steuersatz=_require_float(
            raw, "VBL_BRUTTO_RENTE_STEUERSATZ"
        ),
    )
    etf = EtfTaxConfig(
        abgeltungssteuer=_require_float(raw, "ETF_ABGELTUNGSSTEUER"),
        solidaritaetszuschlag=_require_float(raw, "ETF_SOLIDARITAETSZUSCHLAG"),
        kirchensteuer=_require_float(raw, "ETF_KIRCHENSTEUER"),
        steuerfreibetrag_euro=_require_float(raw, "ETF_STEUERFREIBETRAG_EURO"),
        teilfreistellung=_require_float(raw, "ETF_TEILFREISTELLUNG"),
    )
    klasse_i_brackets = _parse_brackets(raw, "I")
    klasse_ii_brackets = _parse_brackets(raw, "II")
    klasse_iii_brackets = _parse_brackets(raw, "III")
    inheritance_tax = InheritanceTaxConfig(
        ehegatte=InheritanceTaxRelationship(
            freibetrag_euro=_require_float(
                raw, "ERBSCHAFTSTEUER_EHEGATTE_FREIBETRAG_EURO"
            ),
            brackets=klasse_i_brackets,
        ),
        kind=InheritanceTaxRelationship(
            freibetrag_euro=_require_float(
                raw, "ERBSCHAFTSTEUER_KIND_FREIBETRAG_EURO"
            ),
            brackets=klasse_i_brackets,
        ),
        enkel=InheritanceTaxRelationship(
            freibetrag_euro=_require_float(
                raw, "ERBSCHAFTSTEUER_ENKEL_FREIBETRAG_EURO"
            ),
            brackets=klasse_i_brackets,
        ),
        elternteil=InheritanceTaxRelationship(
            freibetrag_euro=_require_float(
                raw, "ERBSCHAFTSTEUER_ELTERNTEIL_FREIBETRAG_EURO"
            ),
            brackets=klasse_i_brackets,
        ),
        klasse_ii=InheritanceTaxRelationship(
            freibetrag_euro=_require_float(
                raw, "ERBSCHAFTSTEUER_KLASSE_II_FREIBETRAG_EURO"
            ),
            brackets=klasse_ii_brackets,
        ),
        klasse_iii=InheritanceTaxRelationship(
            freibetrag_euro=_require_float(
                raw, "ERBSCHAFTSTEUER_KLASSE_III_FREIBETRAG_EURO"
            ),
            brackets=klasse_iii_brackets,
        ),
    )
    insolvency = InsolvencyConfig(
        schwelle_euro=_require_float(raw, "PRIVATINSOLVENZ_SCHWELLE_EURO"),
    )
    return FinevConfig(
        drv=drv,
        vbl=vbl,
        etf=etf,
        inheritance_tax=inheritance_tax,
        insolvency=insolvency,
    )


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

    _require_positive(
        config.vbl.rente_pro_punkt_euro, "VBL_RENTE_PRO_PUNKT_EURO"
    )
    _require_fraction(
        config.vbl.brutto_rente_steuersatz, "VBL_BRUTTO_RENTE_STEUERSATZ"
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

    _require_positive(
        config.insolvency.schwelle_euro, "PRIVATINSOLVENZ_SCHWELLE_EURO"
    )

    for name, rel in [
        ("ehegatte", config.inheritance_tax.ehegatte),
        ("kind", config.inheritance_tax.kind),
        ("enkel", config.inheritance_tax.enkel),
        ("elternteil", config.inheritance_tax.elternteil),
        ("klasse_ii", config.inheritance_tax.klasse_ii),
        ("klasse_iii", config.inheritance_tax.klasse_iii),
    ]:
        _require_non_negative(
            rel.freibetrag_euro, f"ERBSCHAFTSTEUER {name} freibetrag"
        )
        for attr in (
            "bis_75k",
            "bis_300k",
            "bis_600k",
            "bis_6m",
            "bis_13m",
            "bis_26m",
            "ueber_26m",
        ):
            _require_fraction(
                getattr(rel.brackets, attr),
                f"ERBSCHAFTSTEUER {name} bracket {attr}",
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
