import pytest

from finev.config import get_config


def test_config_loads_expected_values() -> None:
    config = get_config()

    assert config.drv.rentenabschlag_pro_jahr == pytest.approx(0.036)
    assert config.drv.brutto_rente_steuersatz == pytest.approx(0.16)
    assert config.etf.taxable_share == pytest.approx(0.7)
    assert config.etf.steuerfreibetrag_euro == pytest.approx(1000.0)
    assert config.capital_gains_tax_rate == pytest.approx(0.25 * (1 + 0.055))
