import pytest
from pydantic import ValidationError

from app.config import Settings

TOKEN = "0123456789abcdef" * 4


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("APP_ENV", "BACKEND_URL", "INTERNAL_TOKEN", "MAX_SNAP_DISTANCE_M"):
        monkeypatch.delenv(name, raising=False)


def test_uses_defaults_without_environment() -> None:
    settings = Settings(_env_file=None)

    assert settings.app_env == "development"
    assert settings.backend_url == "http://localhost:3000"
    assert settings.internal_token is None
    assert settings.max_snap_distance_m == 200.0


def test_reads_values_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("BACKEND_URL", "https://backend.example.com")
    monkeypatch.setenv("INTERNAL_TOKEN", TOKEN)
    monkeypatch.setenv("MAX_SNAP_DISTANCE_M", "150")

    settings = Settings(_env_file=None)

    assert settings.app_env == "production"
    assert settings.backend_url == "https://backend.example.com"
    assert settings.internal_token is not None
    assert settings.internal_token.get_secret_value() == TOKEN
    assert settings.max_snap_distance_m == 150.0


def test_hides_the_token_when_printed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INTERNAL_TOKEN", TOKEN)

    settings = Settings(_env_file=None)

    assert TOKEN not in repr(settings)
    assert TOKEN not in str(settings)


def test_rejects_an_unknown_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "staging")

    with pytest.raises(ValueError):
        Settings(_env_file=None)


@pytest.mark.parametrize("empty", ["", "   "])
def test_an_empty_token_means_not_configured(monkeypatch: pytest.MonkeyPatch, empty: str) -> None:
    monkeypatch.setenv("INTERNAL_TOKEN", empty)

    assert Settings(_env_file=None).internal_token is None


def test_removes_spaces_around_the_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INTERNAL_TOKEN", f"  {TOKEN}\n")

    token = Settings(_env_file=None).internal_token
    assert token is not None
    assert token.get_secret_value() == TOKEN


def test_rejects_a_token_that_is_too_short(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INTERNAL_TOKEN", "short-token")

    with pytest.raises(ValidationError, match="at least 32 characters"):
        Settings(_env_file=None)


def test_removes_the_trailing_slash_of_the_backend_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BACKEND_URL", "  https://backend.example.com/  ")

    assert Settings(_env_file=None).backend_url == "https://backend.example.com"


@pytest.mark.parametrize(
    ("url", "message"),
    [
        ("backend.example.com", "http:// or https://"),
        ("ftp://backend.example.com", "http:// or https://"),
        ("https://", "http:// or https://"),
        ("https://user:pass@backend.example.com", "user or a password"),
        ("https://backend.example.com/?debug=1", "query or a fragment"),
    ],
)
def test_rejects_invalid_backend_urls(
    monkeypatch: pytest.MonkeyPatch, url: str, message: str
) -> None:
    monkeypatch.setenv("BACKEND_URL", url)

    with pytest.raises(ValidationError, match=message):
        Settings(_env_file=None)


def test_production_requires_https_so_the_token_is_never_sent_in_clear_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("BACKEND_URL", "http://backend.example.com")

    with pytest.raises(ValidationError, match="must use https://"):
        Settings(_env_file=None)


def test_development_allows_a_local_http_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("BACKEND_URL", "http://localhost:3000")

    assert Settings(_env_file=None).backend_url == "http://localhost:3000"


@pytest.mark.parametrize("distance", ["0", "-5", "nan", "inf"])
def test_rejects_an_invalid_snap_distance(monkeypatch: pytest.MonkeyPatch, distance: str) -> None:
    monkeypatch.setenv("MAX_SNAP_DISTANCE_M", distance)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


@pytest.mark.parametrize(
    ("variables", "message"),
    [
        ({"APP_ENV": "production", "BACKEND_URL": "http://backend.example.com"}, "https://"),
        ({"BACKEND_URL": "ftp://backend.example.com"}, "http:// or https://"),
        ({"MAX_SNAP_DISTANCE_M": "-1"}, "greater than 0"),
    ],
)
def test_errors_never_repeat_the_token(
    monkeypatch: pytest.MonkeyPatch, variables: dict[str, str], message: str
) -> None:
    monkeypatch.setenv("INTERNAL_TOKEN", TOKEN)
    for name, value in variables.items():
        monkeypatch.setenv(name, value)

    with pytest.raises(ValidationError, match=message) as error:
        Settings(_env_file=None)

    assert TOKEN not in str(error.value)
    assert TOKEN[-12:] not in str(error.value)


def test_a_short_token_is_not_repeated_in_the_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INTERNAL_TOKEN", "my-short-secret")

    with pytest.raises(ValidationError) as error:
        Settings(_env_file=None)

    assert "my-short-secret" not in str(error.value)
