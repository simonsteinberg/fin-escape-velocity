import errno

import pytest

from finev import app


def test_candidate_ports_increments() -> None:
    assert app._candidate_ports(8081, 3) == [8081, 8082, 8083]


def test_main_rejects_non_integer_port(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WEALTH_APP_PORT", "abc")
    monkeypatch.setattr(app, "register_routes", lambda: None)

    with pytest.raises(ValueError, match="WEALTH_APP_PORT must be an integer"):
        app.main()


def test_main_rejects_non_positive_port(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WEALTH_APP_PORT", "0")
    monkeypatch.setattr(app, "register_routes", lambda: None)

    with pytest.raises(
        ValueError, match="WEALTH_APP_PORT must be a positive integer"
    ):
        app.main()


def test_main_retries_on_address_in_use_then_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WEALTH_APP_PORT", "8000")
    monkeypatch.setattr(app, "register_routes", lambda: None)
    monkeypatch.setattr(
        app, "_candidate_ports", lambda start_port, max_attempts: [8000, 8001]
    )
    calls: list[int] = []

    def fake_run(**kwargs) -> None:
        calls.append(int(kwargs["port"]))
        if len(calls) == 1:
            raise OSError(errno.EADDRINUSE, "Address already in use")

    monkeypatch.setattr(app.ui, "run", fake_run)

    app.main()

    assert calls == [8000, 8001]


def test_main_raises_after_exhausting_candidate_ports(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WEALTH_APP_PORT", "8000")
    monkeypatch.setattr(app, "register_routes", lambda: None)
    monkeypatch.setattr(
        app, "_candidate_ports", lambda start_port, max_attempts: [8000, 8001]
    )

    def fake_run(**kwargs) -> None:
        raise OSError(errno.EADDRINUSE, "Address already in use")

    monkeypatch.setattr(app.ui, "run", fake_run)

    with pytest.raises(
        RuntimeError,
        match="No available port found starting at 8000 after 2 attempts",
    ):
        app.main()
