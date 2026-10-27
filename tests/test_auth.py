import base64

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

PASSWORD = "private-test-access-password"
PROVIDER_KEY = "private-test-provider-key"
CHAT = {"messages": [{"role": "user", "content": "Hello"}]}


def authorization(password=PASSWORD, username="owner"):
    credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {credentials}"}


def protected_client(handler=None, password=PASSWORD, api_key=PROVIDER_KEY):
    transport = httpx.MockTransport(handler) if handler else None
    return TestClient(
        create_app(Settings(api_key=api_key, access_password=password), transport=transport)
    )


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/"),
        ("GET", "/static/app.js"),
        ("GET", "/static/styles.css"),
        ("GET", "/api/config"),
        ("POST", "/api/chat"),
        ("GET", "/api/health/"),
        ("GET", "/api/health/anything"),
    ],
)
def test_live_content_requires_authentication(method, path):
    def unexpected_provider_request(request):
        raise AssertionError("Unauthenticated requests must not reach the provider")

    with protected_client(unexpected_provider_request) as client:
        response = client.request(method, path, json=CHAT if method == "POST" else None)

    assert response.status_code == 401
    assert response.headers["www-authenticate"].lower().startswith("basic")
    assert PASSWORD not in response.text
    assert PROVIDER_KEY not in response.text


@pytest.mark.parametrize(
    "header",
    [
        "Bearer other-token",
        "Basic",
        "Basic !!!not-base64!!!",
        "Basic " + base64.b64encode(b"no-colon").decode(),
        "Basic " + base64.b64encode(b"\xff:\xff").decode(),
        "Basic " + "x" * 5000,
        authorization("wrong-password")["Authorization"],
        authorization(username="someone-else")["Authorization"],
        authorization(password="")["Authorization"],
    ],
)
def test_wrong_or_malformed_credentials_fail_cleanly(header):
    with protected_client() as client:
        response = client.get("/api/config", headers={"Authorization": header})
    assert response.status_code == 401
    assert response.headers["www-authenticate"].lower().startswith("basic")
    assert PASSWORD not in response.text
    assert PROVIDER_KEY not in response.text


def test_authenticated_browser_can_load_page_assets_and_configuration():
    with protected_client() as client:
        for path in ("/", "/static/app.js", "/static/styles.css"):
            assert client.get(path, headers=authorization()).status_code == 200
        response = client.get("/api/config", headers=authorization())

    assert response.status_code == 200
    assert response.json()["mode"] == "live"
    assert PROVIDER_KEY not in response.text
    assert PASSWORD not in response.text


def test_authenticated_chat_uses_provider_key_without_forwarding_access_password():
    calls = []

    def handler(request):
        calls.append(request)
        assert request.headers["authorization"] == f"Bearer {PROVIDER_KEY}"
        assert PASSWORD not in request.content.decode()
        return httpx.Response(200, json={"choices": [{"message": {"content": "A real answer"}}]})

    with protected_client(handler) as client:
        response = client.post("/api/chat", json=CHAT, headers=authorization())

    assert response.status_code == 200
    assert response.json()["reply"] == "A real answer"
    assert len(calls) == 1
    assert PROVIDER_KEY not in response.text
    assert PASSWORD not in response.text


def test_health_stays_public_without_disclosing_live_configuration():
    with protected_client() as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert "www-authenticate" not in response.headers
    assert PROVIDER_KEY not in response.text
    assert PASSWORD not in response.text


@pytest.mark.parametrize(
    ("method", "path"),
    [("GET", "/"), ("GET", "/api/health"), ("GET", "/api/config"), ("POST", "/api/chat")],
)
def test_provider_key_without_access_password_fails_closed(method, path):
    def unexpected_provider_request(request):
        raise AssertionError("Incomplete access configuration must not reach the provider")

    with protected_client(unexpected_provider_request, password="") as client:
        response = client.request(method, path, json=CHAT if method == "POST" else None)

    assert response.status_code == 503
    assert "AGENT_ACCESS_PASSWORD" in response.json()["detail"]
    assert PROVIDER_KEY not in response.text


def test_demo_can_be_password_protected_before_a_provider_key_is_added():
    def unexpected_provider_request(request):
        raise AssertionError("Demo mode must not contact the provider")

    with protected_client(unexpected_provider_request, api_key="") as client:
        assert client.get("/api/config").status_code == 401
        response = client.post(
            "/api/chat",
            json={"messages": [{"role": "user", "content": "Calculate 2 + 3"}]},
            headers=authorization(),
        )

    assert response.status_code == 200
    assert response.json()["mode"] == "demo"
    assert response.json()["tool_calls"][0]["result"] == "5"


def test_utf8_password_and_case_insensitive_basic_scheme_are_supported():
    password = "a-private:passphrase-with-é-and-密碼"
    headers = authorization(password)
    headers["Authorization"] = headers["Authorization"].replace("Basic ", "bAsIc ", 1)
    with protected_client(password=password) as client:
        response = client.get("/api/config", headers=headers)
    assert response.status_code == 200
    assert password not in response.text


def test_environment_settings_read_access_password_without_exposing_it(monkeypatch):
    monkeypatch.setenv("AGENT_API_KEY", PROVIDER_KEY)
    monkeypatch.setenv("AGENT_ACCESS_PASSWORD", PASSWORD)
    monkeypatch.setenv("AGENT_MODEL", "configured-model")
    settings = Settings.from_environment()
    assert settings.api_key == PROVIDER_KEY
    assert settings.access_password == PASSWORD
    assert settings.model == "configured-model"
    assert PASSWORD not in repr(settings)
    assert PROVIDER_KEY not in repr(settings)
