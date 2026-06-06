import pytest

from finev.config import get_config


def test_config_loads_expected_values() -> None:
    config = get_config()

    assert config.drv.rentenabschlag_pro_jahr == pytest.approx(0.036)
    assert config.drv.brutto_rente_steuersatz == pytest.approx(0.16)
    assert config.vbl.rente_pro_punkt_euro == pytest.approx(4.0)
    assert config.vbl.brutto_rente_steuersatz == pytest.approx(0.16)
    assert config.etf.taxable_share == pytest.approx(0.7)
    assert config.etf.steuerfreibetrag_euro == pytest.approx(1000.0)
    assert config.capital_gains_tax_rate == pytest.approx(0.25 * (1 + 0.055))
    assert config.insolvency.schwelle_euro == pytest.approx(100_000.0)


def test_inheritance_tax_below_freibetrag_returns_zero() -> None:
    config = get_config()
    # Kind Freibetrag = 400 000 €; 100 000 € is below it.
    assert config.inheritance_tax.compute_tax(
        100_000.0, "kind"
    ) == pytest.approx(0.0)


def test_inheritance_tax_klasse_i_brackets() -> None:
    config = get_config()
    # Kind: taxable = 500 000 - 400 000 = 100 000 € -> bis 300 000 bracket -> 11%
    assert config.inheritance_tax.compute_tax(
        500_000.0, "kind"
    ) == pytest.approx(100_000.0 * 0.11)
    # Kind: taxable = 1 000 000 - 400 000 = 600 000 € -> bis 600 000 bracket -> 15%
    # (600 000 <= 600 000, so it falls in the bis_600k bracket, not bis_6m)
    assert config.inheritance_tax.compute_tax(
        1_000_000.0, "kind"
    ) == pytest.approx(600_000.0 * 0.15)


def test_inheritance_tax_ehegatte_freibetrag() -> None:
    config = get_config()
    # Ehegatte Freibetrag = 500 000 €; gross = 500 000 € -> zero tax.
    assert config.inheritance_tax.compute_tax(
        500_000.0, "ehegatte"
    ) == pytest.approx(0.0)


def test_inheritance_tax_klasse_ii() -> None:
    config = get_config()
    # Klasse II Freibetrag = 20 000 €; gross = 100 000 €; taxable = 80 000 €.
    # bis 300 000 bracket -> 20%
    assert config.inheritance_tax.compute_tax(
        100_000.0, "klasse_ii"
    ) == pytest.approx(80_000.0 * 0.20)


def test_inheritance_tax_klasse_iii() -> None:
    config = get_config()
    # Klasse III Freibetrag = 20 000 €; gross = 100 000 €; taxable = 80 000 €.
    # bis 300 000 bracket -> 30%
    assert config.inheritance_tax.compute_tax(
        100_000.0, "klasse_iii"
    ) == pytest.approx(80_000.0 * 0.30)


def test_inheritance_tax_unknown_relationship_raises() -> None:
    config = get_config()
    with pytest.raises(KeyError):
        config.inheritance_tax.compute_tax(100_000.0, "unknown")
