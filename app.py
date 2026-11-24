from dataclasses import replace
from datetime import date
from pathlib import Path
import hashlib
import json
import os
import streamlit as st
from dotenv import load_dotenv
from redator.domain import Case, Identity, TechnicalItem, validate_review
from redator.documents import create_demo_template, generate_docx, convert_pdf
from redator.narrative import build_narrative_payload, generate_narrative, generate_demo_narrative
from redator.audio_ui import render_audio
from redator.flow import initialize, add_equipment, remove_equipment, load_example, clear_case
from redator.settings import load_profile, DEFAULT_MODEL
from redator.report import build_report_body
from redator.filenames import report_filename
from redator.terminology import terminology_notes
from redator.support_ui import render_case_support
from redator.openai_service import error_message
from redator.privacy import assert_deidentified

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env", override=True)
st.set_page_config(page_title="Redator de Relatórios Técnicos", page_icon="🛠️", layout="wide")
initialize(st.session_state)
profile = load_profile(ROOT)


def invalidate_review():
    st.session_state["approved"] = False
    st.session_state.pop("exports", None)


def template_path() -> Path:
    configured = os.getenv("RELATORIO_TEMPLATE", "").strip() or profile["template_path"]
    if configured:
        candidate = Path(configured)
        candidate = candidate if candidate.is_absolute() else ROOT / candidate
        if not candidate.exists():
            raise ValueError("O template configurado não foi encontrado. Confira a configuração local.")
        return candidate
    path = ROOT / "local" / "template-neutro.docx"
    if not path.exists():
        create_demo_template(path)
    return path


st.title("Redator de Relatórios Técnicos")
st.caption("Cadastre os equipamentos, relate a avaliação e revise o relatório.")
st.info("Preencha a identificação nos campos próprios do documento. Não inclua nomes, modelos, séries ou outros identificadores na avaliação técnica enviada à IA.")
with st.sidebar:
    st.subheader("Preparação")
    provider = st.radio("Redação", ["OpenAI", "Demonstração local"], index=0 if os.getenv("OPENAI_API_KEY") else 1)
    if provider == "Demonstração local":
        st.caption("Demonstração da redação sem chamadas à IA. A transcrição de áudio usa a OpenAI. Use Carregar exemplo fictício para testar.")
    mode = st.radio("Formato", ["Objetivo", "Detalhado"])
    with st.expander("Configurações avançadas da IA") as advanced_ai:
        model = st.text_input("Modelo OpenAI", value=os.getenv("OPENAI_MODEL", DEFAULT_MODEL), disabled=provider != "OpenAI")
        st.caption("Chave configurada localmente." if os.getenv("OPENAI_API_KEY") else "A chave ainda não foi configurada.")
    st.button("Carregar exemplo fictício", on_click=load_example, args=(st.session_state,))
    st.button("Nova avaliação", on_click=clear_case, args=(st.session_state,))
    st.caption("O trabalho fica na sessão. Baixe os documentos revisados antes de encerrar.")

st.header("1. Identificação")
a, b = st.columns(2)
requester = a.text_input("Solicitante", key="requester", max_chars=150)
department = b.text_input("Setor", key="department", max_chars=150)
report_date = date.today()
st.caption(f"{profile['city']} · {report_date:%d/%m/%Y} · {profile['responsible']}")

st.header("2. Equipamentos e avaliação")
identities = []
for position, alias in enumerate(st.session_state["equipment_ids"], start=1):
    with st.container(border=True):
        title, remove = st.columns([5, 1])
        title.subheader(f"Equipamento {position}")
        remove.button("Remover", key=f"remove_{alias}", disabled=len(st.session_state["equipment_ids"]) == 1,
                      on_click=remove_equipment, args=(st.session_state, alias))
        a, b = st.columns(2)
        kind = a.text_input("Tipo de equipamento", value="Módulo eletrônico", key=f"kind_{alias}", max_chars=100)
        side = b.selectbox("Lado (opcional)", ["", "Direito", "Esquerdo"], key=f"side_{alias}",
                           format_func=lambda x: x or "Não se aplica / não informado")
        a, b = st.columns(2)
        equipment_model = a.text_input("Modelo", key=f"model_{alias}", max_chars=150)
        serial = b.text_input("Número de série", key=f"serial_{alias}", max_chars=100)
        identities.append(Identity(alias, kind, side, equipment_model, serial))
st.button("＋ Adicionar equipamento", on_click=add_equipment, args=(st.session_state,))

st.subheader("Avaliação técnica")
st.caption("Descreva todos os equipamentos aqui, digitando, ditando ou combinando os dois. Use o tipo e o lado de cada equipamento; para tipos repetidos, use primeiro e segundo. Não inclua nomes, modelos ou séries no relato.")
narrative = st.text_area("Avaliação de todos os equipamentos", key="general_assessment", height=260, max_chars=20000,
    placeholder="Conte o que encontrou, o que fez, como cada equipamento ficou e o que recomenda. Não precisa separar em campos nem escrever uma conclusão formal.")
render_audio(ROOT, "geral", "general_assessment")
for note in terminology_notes(narrative):
    st.warning(note)

empty = tuple(TechnicalItem(i.alias, "", "", "", "") for i in identities)
intake_case = Case(requester, department, profile["city"], report_date, profile["responsible"], tuple(identities), empty)
context_data = {"case": intake_case.fingerprint("intake"), "narrative": narrative,
                "provider": provider, "model": model, "mode": mode,
                "closing": profile["closing"], "role": profile["role"]}
context = hashlib.sha256(json.dumps(context_data, sort_keys=True).encode()).hexdigest()
if st.session_state.get("source_fingerprint") not in (None, context):
    from redator.flow import invalidate
    invalidate(st.session_state)
    st.warning("A avaliação ou o cadastro mudou. Gere novamente o relatório para revisar a nova versão.")

st.header("3. Gerar e revisar o relatório")
can_send = True
if provider == "OpenAI":
    payload = build_narrative_payload(intake_case, narrative, mode)
    try:
        assert_deidentified(intake_case, payload)
    except ValueError as exc:
        can_send = False
        st.warning(str(exc))
    with advanced_ai:
        st.caption("Conferir o texto que será enviado à IA (opcional)")
        st.caption("Somente tipo, lado e avaliação técnica. Solicitante, setor, responsável, modelos, séries e áudio não são enviados.")
        st.code(json.dumps(payload, ensure_ascii=False, indent=2), language="json")
render_case_support(intake_case, narrative, context, provider, can_send,
                    os.getenv("OPENAI_API_KEY", ""), model)
if st.button("Gerar relatório para revisão", type="primary", disabled=not can_send):
    try:
        with st.spinner("Preparando o relatório para sua revisão..."):
            if provider == "OpenAI":
                result = generate_narrative(intake_case, narrative, mode, os.getenv("OPENAI_API_KEY", ""), model)
            else:
                result = generate_demo_narrative(intake_case, narrative, mode)
        report_case = replace(intake_case, complaints=result.complaints)
        body = build_report_body(report_case, result.text, profile["closing"])
        st.session_state["draft"] = body
        st.session_state["review_text"] = body
        st.session_state["report_case"] = report_case
        st.session_state["report_notes"] = result.notes
        st.session_state["source_fingerprint"] = context
        invalidate_review()
    except ValueError as exc:
        st.error(str(exc))
    except Exception as exc:
        st.error(error_message(exc))

if "draft" in st.session_state:
    report_case = st.session_state["report_case"]
    for note in st.session_state.get("report_notes", ()):
        st.warning(note)
    st.caption("Revise o texto completo e faça os ajustes aqui antes de aprovar a emissão.")
    reviewed = st.text_area("Texto final editável", key="review_text", height=440, on_change=invalidate_review)
    for note in terminology_notes(reviewed):
        st.warning(note)
    st.caption(profile["responsible"] + (" · " + profile["role"] if profile["role"] else ""))
    try:
        validate_review(reviewed, mode)
        valid = True
    except ValueError as exc:
        st.warning(str(exc))
        valid = False
    approved = st.checkbox("Revisei o relatório e a identificação de todos os equipamentos e aprovo a emissão.", key="approved")
    include_pdf = st.checkbox("Gerar também PDF usando o Word instalado", value=True)
    can_export = approved and valid
    if st.button("Preparar documentos revisados", disabled=not can_export):
        try:
            with st.spinner("Preparando os documentos no computador..."):
                docx_bytes = generate_docx(report_case, reviewed, mode, template_path(), text_is_complete=True, responsible_role=profile["role"], department_prefix=profile["department_prefix"])
                filename = report_filename(report_case, profile["department_prefix"])
                exports = {"docx": docx_bytes, "context": context, "filename": filename,
                           "review_hash": hashlib.sha256(reviewed.encode()).hexdigest()}
                if include_pdf:
                    try:
                        exports["pdf"] = convert_pdf(docx_bytes)
                    except RuntimeError as exc:
                        st.warning(str(exc))
                st.session_state["exports"] = exports
        except ValueError as exc:
            st.error(str(exc))
        except Exception:
            st.error("Não foi possível preparar o documento. Confira o template local e tente novamente.")
    exports = st.session_state.get("exports")
    if can_export and exports and exports["context"] == context and exports["review_hash"] == hashlib.sha256(reviewed.encode()).hexdigest():
        filename = exports["filename"]
        st.caption("Nome dos arquivos: " + filename.stem)
        if filename.shortened:
            st.info("O nome foi abreviado para respeitar o limite do Windows. O cadastro completo permanece dentro do relatório.")
        a, b = st.columns(2)
        a.download_button("Baixar Word", exports["docx"], file_name=filename.for_extension("docx"), mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        if "pdf" in exports:
            b.download_button("Baixar PDF", exports["pdf"], file_name=filename.for_extension("pdf"), mime="application/pdf")
        st.success("Documentos prontos. Confira também a aparência antes de encaminhar.")

st.caption("Redator de Relatórios Técnicos · Execução local · O diagnóstico técnico e a aprovação pertencem ao profissional.")
