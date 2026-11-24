import json
import re
import httpx
import pytest
from openai import InternalServerError, AuthenticationError
from redator.openai_service import create_client, error_message
from redator.narrative import generate_narrative
from tests.scenarios import three_device_case


def success_response():
    return {"id": "resp_ficticia", "object": "response", "status": "completed", "created_at": 1,
            "model": "test-model", "output": [{"id": "msg_ficticia", "type": "message", "role": "assistant",
            "status": "completed", "content": [{"type": "output_text", "annotations": [], "text": json.dumps({
                "paragraphs": ["Realizamos a limpeza do carregador, que voltou a funcionar."], "complaints": [], "notes": []})}]}]}


def test_503_is_retried_and_valid_draft_returns_without_changing_model():
    requests = []
    def handler(request):
        payload = json.loads(request.content)
        assert re.fullmatch(r"[A-Za-z0-9_-]{1,64}", payload["text"]["format"]["name"])
        requests.append(payload)
        if len(requests) == 1:
            return httpx.Response(503, headers={"retry-after": "0.001"}, json={"error": {"message": "temporarily unavailable", "type": "server_error"}})
        return httpx.Response(200, json=success_response())
    with create_client("fake-test-key", http_client=httpx.Client(transport=httpx.MockTransport(handler))) as client:
        draft = generate_narrative(three_device_case(), "Limpamos o carregador e voltou a funcionar.", "Objetivo", "fake-test-key", "test-model", client=client)
    assert draft.text == "Realizamos a limpeza do carregador, que voltou a funcionar."
    assert len(requests) == 2
    assert all(r["model"] == "test-model" and r["store"] is False for r in requests)


def test_persistent_503_stops_after_two_retries_and_does_not_expose_error_body():
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(503, headers={"retry-after": "0.001"}, json={"error": {"message": "PRIVATE_FAKE_KEY PRIVATE_FAKE_PATIENT", "type": "server_error"}})
    with create_client("fake-test-key", http_client=httpx.Client(transport=httpx.MockTransport(handler))) as client:
        with pytest.raises(InternalServerError) as caught:
            client.responses.create(model="test-model", input="Relato fictício")
    assert len(calls) == 3
    message = error_message(caught.value)
    assert "503" in message and "preservado" in message and "alterar a chave" in message
    assert "PRIVATE" not in message and "fake-test-key" not in message


def test_authentication_failure_is_not_retried_or_confused_with_unavailability():
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(401, json={"error": {"message": "PRIVATE_FAKE_KEY", "type": "invalid_request_error", "code": "invalid_api_key"}})
    with create_client("fake-test-key", http_client=httpx.Client(transport=httpx.MockTransport(handler))) as client:
        with pytest.raises(AuthenticationError) as caught:
            client.responses.create(model="test-model", input="Relato fictício")
    assert len(calls) == 1
    assert "401" in error_message(caught.value) and "PRIVATE" not in error_message(caught.value)


def test_local_failure_is_not_reported_as_a_connection_or_key_error():
    message = error_message(TypeError("PRIVATE_FAKE_PATIENT"))
    assert "falha interna no aplicativo" in message
    assert "PRIVATE" not in message and "chave" not in message
