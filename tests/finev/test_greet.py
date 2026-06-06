import runpy
import warnings
from importlib.metadata import version

from finev.greet import get_version, main


def test_get_version_matches_installed_metadata() -> None:
    # Reads real package metadata (not the "0.0.0" fallback) when installed.
    assert get_version() == version("finev")


def test_main_prints_expected_message(capsys) -> None:
    main()
    captured = capsys.readouterr()
    assert captured.out.strip() == f"Hello finev (version {get_version()})"


def test_module_entrypoint_prints_expected_message(capsys) -> None:
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message=r"'finev\.greet' found in sys\.modules",
            category=RuntimeWarning,
        )
        runpy.run_module("finev.greet", run_name="__main__")
    captured = capsys.readouterr()
    assert captured.out.strip() == f"Hello finev (version {get_version()})"
