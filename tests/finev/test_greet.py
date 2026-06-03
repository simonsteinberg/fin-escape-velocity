import runpy
import warnings

from finev.greet import get_version, main


def test_get_version() -> None:
    assert get_version() == "0.0.0"


def test_main_prints_expected_message(capsys) -> None:
    main()
    captured = capsys.readouterr()
    assert captured.out.strip() == "Hello finev (version 0.0.0)"


def test_module_entrypoint_prints_expected_message(capsys) -> None:
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message=r"'finev\.greet' found in sys\.modules",
            category=RuntimeWarning,
        )
        runpy.run_module("finev.greet", run_name="__main__")
    captured = capsys.readouterr()
    assert captured.out.strip() == "Hello finev (version 0.0.0)"
