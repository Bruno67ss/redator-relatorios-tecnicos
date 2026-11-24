"""Transcrição remota com validação local de formato, tamanho e duração."""
from io import BytesIO
from pathlib import Path
from openai import APIConnectionError, APITimeoutError, APIStatusError
from .openai_service import create_client

MAX_BYTES = 20 * 1024 * 1024
MAX_SECONDS = 600
DEFAULT_TRANSCRIPTION_MODEL = "gpt-transcribe"
AUDIO_TYPES = {".wav": "audio/wav", ".mp3": "audio/mpeg", ".m4a": "audio/mp4",
               ".ogg": "audio/ogg", ".webm": "audio/webm"}


class TranscriptionError(RuntimeError):
    """Falha de transcrição com mensagem segura para a interface."""


def validate_audio_bytes(data: bytes):
    if not data:
        raise ValueError("Grave ou selecione um áudio antes de transcrever.")
    if len(data) > MAX_BYTES:
        raise ValueError("O áudio deve ter no máximo 20 MB.")


def validate_online_audio(data: bytes, filename: str) -> tuple[str, bytes, str]:
    """Confere formato e duração pelos pacotes, sem decodificar ou converter a fala."""
    validate_audio_bytes(data)
    extension = Path(filename).suffix.lower()
    if extension not in AUDIO_TYPES:
        raise ValueError("Use um arquivo WAV, MP3, M4A, OGG ou WEBM.")
    import av
    try:
        with av.open(BytesIO(data), options={"protocol_whitelist": "pipe",
                                            "format_whitelist": "wav,mp3,mov,ogg,matroska,webm"}) as container:
            if not container.streams.audio:
                raise ValueError("O arquivo selecionado não contém uma faixa de áudio.")
            stream = container.streams.audio[0]
            duration = float(stream.duration * stream.time_base) if stream.duration is not None and stream.time_base else 0
            if duration > MAX_SECONDS:
                raise ValueError("Use gravações de até dez minutos por transcrição.")
            first, last = None, None
            packets = 0
            for packet in container.demux(stream):
                if not packet.size:
                    continue
                packets += 1
                timestamp = packet.pts if packet.pts is not None else packet.dts
                if timestamp is not None and packet.time_base:
                    start = float(timestamp * packet.time_base)
                    first = start if first is None else min(first, start)
                    end = start + float((packet.duration or 0) * packet.time_base)
                    last = end if last is None else max(last, end)
                    duration = max(duration, last - first)
                    if duration > MAX_SECONDS:
                        raise ValueError("Use gravações de até dez minutos por transcrição.")
            if not packets or duration <= 0:
                raise ValueError("Não foi possível confirmar a duração deste áudio. Grave novamente ou use um arquivo válido.")
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("Não foi possível ler este áudio. Tente um arquivo WAV, MP3, M4A, OGG ou WEBM válido.") from exc
    # O nome original pode conter identificação; somente a extensão é reaproveitada.
    return "avaliacao" + extension, data, AUDIO_TYPES[extension]


def transcribe_openai(data: bytes, filename: str, api_key: str, *, client=None) -> str:
    if not api_key.strip():
        raise ValueError("Configure OPENAI_API_KEY no computador para transcrever o áudio.")
    audio = validate_online_audio(data, filename)
    owns_client = client is None
    try:
        if client is None:
            client = create_client(api_key)
        response = client.audio.transcriptions.create(
            file=audio, model=DEFAULT_TRANSCRIPTION_MODEL, languages=["pt"],
            response_format="json", timeout=60)
    except APITimeoutError as exc:
        raise TranscriptionError("A OpenAI excedeu o tempo de transcrição. Tente novamente; o texto anterior foi preservado.") from exc
    except APIConnectionError as exc:
        raise TranscriptionError("Não foi possível conectar à OpenAI para transcrever. Confira a conexão; o texto anterior foi preservado.") from exc
    except APIStatusError as exc:
        messages = {
            401: "A OpenAI recusou a chave de transcrição (401). Confira OPENAI_API_KEY.",
            403: "A OpenAI negou acesso à transcrição (403). Confira as permissões da conta.",
            404: "O modelo de transcrição gpt-transcribe não está disponível para esta conta (404).",
            429: "A transcrição atingiu um limite de uso ou saldo da API (429). Aguarde ou confira a conta.",
        }
        message = messages.get(exc.status_code, "A OpenAI não conseguiu concluir a transcrição. Aguarde e tente novamente.")
        raise TranscriptionError(message + " O texto anterior foi preservado.") from exc
    except Exception as exc:
        raise TranscriptionError("Não foi possível concluir a transcrição. Tente novamente; o texto anterior foi preservado.") from exc
    finally:
        if owns_client and client is not None:
            try:
                client.close()
            except Exception:
                pass  # Uma falha de fechamento não deve expor dados nem perder o texto.
    text = getattr(response, "text", None)
    if not isinstance(text, str) or not text.strip():
        raise TranscriptionError("A transcrição não retornou texto. Confira o áudio e tente novamente; o texto anterior foi preservado.")
    if len(text.strip()) > 10000:
        raise TranscriptionError("A transcrição ficou extensa demais. Divida o áudio; o texto anterior foi preservado.")
    return text.strip()


def apply_transcript(state, text: str, target: str, *, replace: bool, max_length: int = 4000):
    """Usado por callback, antes da criação dos campos editáveis do formulário."""
    clean = text.strip()
    if not clean:
        raise ValueError("Revise uma transcrição antes de usá-la no formulário.")
    current = str(state.get(target, "")).strip()
    combined = clean if replace or not current else current + "\n" + clean
    if len(combined) > max_length:
        raise ValueError(f"O campo de destino ultrapassaria {max_length} caracteres. Divida ou reduza o texto.")
    state[target] = combined
    state["approved"] = False
    for key in ("exports", "draft", "review_text", "source_fingerprint"):
        state.pop(key, None)
