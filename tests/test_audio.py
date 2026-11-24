from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import math
import struct
import wave
import pytest
from redator.audio import MAX_BYTES, MAX_SECONDS, apply_transcript
from redator.audio import transcribe_openai, validate_online_audio, TranscriptionError
from redator.openai_service import create_client
import httpx
from openai import APIConnectionError, APITimeoutError, AuthenticationError, InternalServerError, NotFoundError, RateLimitError


def wav_bytes(seconds=1, silent=False):
    out = BytesIO()
    with wave.open(out, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        values = (0 if silent else int(8000 * math.sin(2 * math.pi * 440 * i / 16000)) for i in range(seconds * 16000))
        wav.writeframes(b"".join(struct.pack("<h", n) for n in values))
    return out.getvalue()


def test_inserting_transcript_preserves_other_equipment_and_requires_new_review():
    state = {"obs_E1": "Já observado.", "obs_E2": "Outro módulo.", "approved": True,
             "draft": "Anterior", "exports": {"pdf": b"old"}, "source_fingerprint": "old", "review_text": "Anterior"}
    apply_transcript(state, " Texto conferido. ", "obs_E1", replace=False)
    assert state["obs_E1"] == "Já observado.\nTexto conferido."
    assert state["obs_E2"] == "Outro módulo."
    assert not state["approved"] and "exports" not in state and "draft" not in state
    apply_transcript(state, "Substituído.", "obs_E1", replace=True)
    assert state["obs_E1"] == "Substituído."


def test_oversized_transcript_does_not_change_form():
    state = {"obs_E1": "Original.", "approved": True}
    with pytest.raises(ValueError):
        apply_transcript(state, "a" * 4001, "obs_E1", replace=True)
    assert state == {"obs_E1": "Original.", "approved": True}


def test_online_transcription_uses_original_bytes_generic_name_and_portuguese(monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL", "modelo-somente-do-redator")
    client = Mock()
    client.audio.transcriptions.create.return_value = SimpleNamespace(text=" Falha persistente. ")
    data = wav_bytes()
    assert transcribe_openai(data, "Solicitante-Identificador.WAV", "fake-key", client=client) == "Falha persistente."
    assert client.audio.transcriptions.create.call_args.kwargs == {
        "file": ("avaliacao.wav", data, "audio/wav"), "model": "gpt-transcribe",
        "languages": ["pt"], "response_format": "json", "timeout": 60,
    }


def test_installed_sdk_serializes_audio_request_with_mock_transport():
    received = []
    data = wav_bytes()
    def handler(request):
        received.append(request)
        assert request.url.path == "/v1/audio/transcriptions"
        assert b'filename="avaliacao.wav"' in request.content
        assert data in request.content
        assert b"gpt-transcribe" in request.content
        assert b'name="languages[]"' in request.content and b"\r\npt\r\n" in request.content
        assert b"Solicitante-Identificador" not in request.content
        return httpx.Response(200, json={"text": "Falha intermitente."})
    with create_client("fake-key", http_client=httpx.Client(transport=httpx.MockTransport(handler))) as client:
        assert transcribe_openai(data, "Solicitante-Identificador.wav", "fake-key", client=client) == "Falha intermitente."
    assert len(received) == 1


@pytest.mark.parametrize("data,filename", [
    (b"", "clip.wav"), (b"x" * (MAX_BYTES + 1), "clip.wav"),
    (b"nao-e-audio", "clip.wav"), (b"nao-e-audio", "clip.exe"),
])
def test_invalid_online_audio_is_rejected_before_api(data, filename):
    client = Mock()
    with pytest.raises(ValueError):
        transcribe_openai(data, filename, "fake-key", client=client)
    client.audio.transcriptions.create.assert_not_called()


def test_online_duration_limit_is_checked_without_transcribing():
    out = BytesIO()
    with wave.open(out, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(b"\0\0" * ((MAX_SECONDS + 1) * 16000))
    client = Mock()
    with pytest.raises(ValueError, match="dez minutos"):
        transcribe_openai(out.getvalue(), "clip.wav", "fake-key", client=client)
    client.audio.transcriptions.create.assert_not_called()


def test_online_inspection_handles_missing_metadata_without_decoding(monkeypatch):
    import av
    from fractions import Fraction
    container = Mock()
    stream = SimpleNamespace(duration=None, time_base=Fraction(1, 1000))
    container.streams.audio = [stream]
    container.demux.return_value = [SimpleNamespace(size=10, pts=0, dts=0, duration=1000, time_base=Fraction(1, 1000))]
    container.__enter__ = Mock(return_value=container)
    container.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(av, "open", Mock(return_value=container))
    assert validate_online_audio(b"fake-compressed-audio", "clip.webm")[0] == "avaliacao.webm"
    container.decode.assert_not_called()


@pytest.mark.parametrize("value", [None, "", "   ", 42, "a" * 10001])
def test_empty_invalid_or_oversized_api_text_is_rejected(value):
    client = Mock()
    client.audio.transcriptions.create.return_value = SimpleNamespace(text=value)
    with pytest.raises(TranscriptionError, match="texto anterior foi preservado"):
        transcribe_openai(wav_bytes(), "clip.wav", "fake-key", client=client)


@pytest.mark.parametrize("status,error_type", [
    (401, AuthenticationError), (404, NotFoundError), (429, RateLimitError), (503, InternalServerError),
])
def test_api_errors_do_not_expose_response_or_credentials(status, error_type):
    client = Mock()
    response = httpx.Response(status, request=httpx.Request("POST", "https://api.openai.com/v1/audio/transcriptions"))
    client.audio.transcriptions.create.side_effect = error_type("PRIVATE_FAKE_AUDIO PRIVATE_FAKE_KEY", response=response, body=None)
    with pytest.raises(TranscriptionError) as caught:
        transcribe_openai(wav_bytes(), "clip.wav", "fake-key", client=client)
    assert "PRIVATE" not in str(caught.value) and "fake-key" not in str(caught.value)
    assert "texto anterior foi preservado" in str(caught.value)
    if status != 503:
        assert str(status) in str(caught.value)


@pytest.mark.parametrize("error", [
    APITimeoutError(request=httpx.Request("POST", "https://api.openai.com/v1/audio/transcriptions")),
    APIConnectionError(request=httpx.Request("POST", "https://api.openai.com/v1/audio/transcriptions")),
    RuntimeError("PRIVATE_FAKE_AUDIO PRIVATE_FAKE_KEY"),
])
def test_connection_timeout_and_unexpected_failure_keep_safe_messages(error):
    client = Mock()
    client.audio.transcriptions.create.side_effect = error
    with pytest.raises(TranscriptionError) as caught:
        transcribe_openai(wav_bytes(), "clip.wav", "fake-key", client=client)
    assert "PRIVATE" not in str(caught.value)
    assert "texto anterior foi preservado" in str(caught.value)


def test_missing_api_key_never_sends_audio():
    client = Mock()
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        transcribe_openai(wav_bytes(), "clip.wav", "", client=client)
    client.audio.transcriptions.create.assert_not_called()


@pytest.mark.parametrize("container_format,codec,extension", [
    ("mp3", "libmp3lame", ".mp3"), ("mp4", "aac", ".m4a"),
    ("ogg", "libopus", ".ogg"), ("webm", "libopus", ".webm"),
])
def test_supported_compressed_formats_keep_original_bytes(container_format, codec, extension):
    import av
    output = BytesIO()
    with av.open(output, "w", format=container_format) as container:
        stream = container.add_stream(codec, rate=16000)
        frame = av.AudioFrame(format="s16", layout="mono", samples=16000)
        frame.sample_rate = 16000
        frame.planes[0].update(b"\0\0" * 16000)
        for packet in stream.encode(frame):
            container.mux(packet)
        for packet in stream.encode(None):
            container.mux(packet)
    data = output.getvalue()
    filename, uploaded, _ = validate_online_audio(data, "clip" + extension)
    assert filename == "avaliacao" + extension
    assert uploaded == data


@pytest.mark.parametrize("api_failure", [False, True])
def test_created_client_is_closed_on_success_and_failure(monkeypatch, api_failure):
    client = Mock()
    monkeypatch.setattr("redator.audio.create_client", Mock(return_value=client))
    if api_failure:
        client.audio.transcriptions.create.side_effect = RuntimeError("PRIVATE_FAKE_AUDIO")
        with pytest.raises(TranscriptionError):
            transcribe_openai(wav_bytes(), "clip.wav", "fake-key")
    else:
        client.audio.transcriptions.create.return_value = SimpleNamespace(text="Texto fictício.")
        assert transcribe_openai(wav_bytes(), "clip.wav", "fake-key") == "Texto fictício."
    client.close.assert_called_once()


def test_duration_from_packets_rejects_long_recording_without_metadata(monkeypatch):
    import av
    from fractions import Fraction
    container = Mock()
    stream = SimpleNamespace(duration=None, time_base=Fraction(1, 1000))
    container.streams.audio = [stream]
    container.demux.return_value = [
        SimpleNamespace(size=10, pts=0, dts=0, duration=1000, time_base=Fraction(1, 1000)),
        SimpleNamespace(size=10, pts=600000, dts=600000, duration=1000, time_base=Fraction(1, 1000)),
    ]
    container.__enter__ = Mock(return_value=container)
    container.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(av, "open", Mock(return_value=container))
    with pytest.raises(ValueError, match="dez minutos"):
        validate_online_audio(b"fake-compressed-audio", "clip.webm")
