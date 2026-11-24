from pathlib import Path
import os
import streamlit as st
from .audio import apply_transcript, transcribe_openai, TranscriptionError
from .flow import invalidate


def transcribe_into(root: Path, scope: str, target: str):
    prefix = f"voice_{scope}_"
    source = st.session_state.get(prefix + "source", "Microfone")
    recording = st.session_state.get(prefix + ("recording" if source == "Microfone" else "file"))
    try:
        if recording is None:
            raise ValueError("Grave ou selecione um áudio antes de transcrever.")
        with st.spinner("Transcrevendo o áudio pela OpenAI..."):
            text = transcribe_openai(recording.getvalue(), getattr(recording, "name", "avaliacao.wav"),
                                     os.getenv("OPENAI_API_KEY", ""))
        apply_transcript(st.session_state, text, target,
                         replace=st.session_state.get(prefix + "replace", False),
                         max_length=20000 if scope == "geral" else 10000)
        invalidate(st.session_state)
        st.session_state[prefix + "message"] = "Transcrição colocada na avaliação acima. Confira o texto antes de gerar o relatório."
    except (ValueError, TranscriptionError) as exc:
        st.session_state[prefix + "error"] = str(exc)
    except Exception:
        st.session_state[prefix + "error"] = "Não foi possível transcrever. Confira a conexão e o áudio; o texto anterior foi preservado."


def render_audio(root: Path, scope: str, target: str):
    prefix = f"voice_{scope}_"
    label = "Ditar a avaliação completa" if scope == "geral" else f"Ditar a avaliação de {scope}"
    with st.expander(label, expanded=False):
        st.caption("O áudio será enviado à OpenAI para transcrição e o texto entrará na avaliação acima, para você conferir. Não dite nomes, modelos ou séries. Até dez minutos e 20 MB; a gravação não é salva automaticamente.")
        source = st.radio("Origem do áudio", ["Microfone", "Arquivo de áudio"], horizontal=True, key=prefix + "source")
        if source == "Microfone":
            uploaded = st.audio_input("Gravar avaliação", sample_rate=16000, key=prefix + "recording")
        else:
            uploaded = st.file_uploader("Selecionar áudio no computador", type=["wav", "mp3", "m4a", "ogg", "webm"], key=prefix + "file")
        ready = bool(os.getenv("OPENAI_API_KEY", "").strip())
        if not ready:
            st.info("Configure OPENAI_API_KEY para transcrever pela OpenAI. Consulte docs/AUDIO.md.")
        if st.session_state.get(target, "").strip():
            st.checkbox("Substituir o texto atual da avaliação", key=prefix + "replace")
        st.button("Transcrever para a avaliação", key=prefix + "transcribe", disabled=uploaded is None or not ready,
                  on_click=transcribe_into, args=(root, scope, target))
        if message := st.session_state.pop(prefix + "message", None):
            st.success(message)
        if error := st.session_state.pop(prefix + "error", None):
            st.error(error)
