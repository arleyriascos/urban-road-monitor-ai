import pytest

from app.config import Settings


def test_uses_defaults_without_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("APP_ENV", "BACKEND_URL", "INTERNAL_TOKEN"):
        monkeypatch.delenv(name, raising=False)

    settings = Settings(_env_file=None)

    assert settings.app_env == "development"
    assert settings.backend_url == "http://localhost:3000"
    assert settings.internal_token is None


def test_reads_values_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("BACKEND_URL", "https://backend.example.com")
    monkeypatch.setenv("INTERNAL_TOKEN", "secret-value")

    settings = Settings(_env_file=None)

    assert settings.app_env == "production"
    assert settings.backend_url == "https://backend.example.com"
    assert settings.internal_token is not None
    assert settings.internal_token.get_secret_value() == "secret-value"


def test_hides_the_token_when_printed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INTERNAL_TOKEN", "secret-value")

    settings = Settings(_env_file=None)

    assert "secret-value" not in repr(settings)
    assert "secret-value" not in str(settings)


def test_rejects_an_unknown_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "staging")

    with pytest.raises(ValueError):
        Settings(_env_file=None)
