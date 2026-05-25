import pandas as pd

from finev.ui import _yearly_display_frame


def test_yearly_display_frame_samples_every_12_months() -> None:
    data = pd.DataFrame(
        {
            "month_index": list(range(0, 25)),
            "age_years": [40] * 25,
            "age_months": list(range(0, 25)),
            "total": [float(value) for value in range(25)],
        }
    )

    result = _yearly_display_frame(data)

    assert result["month_index"].tolist() == [0, 12, 24]
    assert result["year_index"].tolist() == [0, 1, 2]
    assert result.index.tolist() == [0, 1, 2]


def test_yearly_display_frame_handles_empty() -> None:
    result = _yearly_display_frame(pd.DataFrame())

    assert result.empty
