"""Fluxo opcional sem impor novas etapas à geração habitual."""
import hashlib
import streamlit as st
from .case_support import generate_case_support
from .flow import invalidate
from .openai_service import error_message


def apply_support():
    text = st.session_state.get("support_edit", "").strip()
    if text:
        st.session_state["general_assessment"] = text
        invalidate(st.session_state)
        for key in list(st.session_state):
            if key.startswith("support_"):
                st.session_state.pop(key, None)
        st.session_state["support_applied"] = True


def render_case_support(case, narrative, context, provider, allowed, api_key, model):
    if st.session_state.pop("support_applied", False):
        st.success("Avaliação atualizada na caixa acima. Confira o texto e gere o relatório quando estiver pronto.")
    if st.session_state.get("support_context") not in (None, context):
        for key in list(st.session_state):
            if key.startswith("support_"):
                st.session_state.pop(key, None)
    with st.expander("Preciso de ajuda para explicar este caso (opcional)", expanded=False):
        st.caption("O aplicativo organiza o que você sabe e faz até três perguntas. Não pesquisa manuais nem confirma causas. Use somente informações técnicas sem identificação; cada solicitação usa a mesma IA de redação.")
        if provider != "OpenAI":
            st.info("Selecione OpenAI na lateral para usar esta ajuda.")
            return
        st.caption("A avaliação e as respostas passam por verificação automática de identificadores antes do envio. Não inclua nomes, modelos ou séries nas respostas.")
        if st.button("Analisar meu relato", disabled=not allowed):
            try:
                with st.spinner("Organizando os fatos e as dúvidas..."):
                    result = generate_case_support(case, narrative, [], api_key, model)
                st.session_state["support_context"] = context
                st.session_state["support_result"] = result
                st.session_state["support_edit"] = result.assessment
                for key in list(st.session_state):
                    if key.startswith("support_answer_"):
                        st.session_state.pop(key, None)
            except ValueError as exc:
                st.error(str(exc))
            except Exception as exc:
                st.error(error_message(exc))
        result = st.session_state.get("support_result")
        if result is None:
            return
        for note in result.notes:
            st.warning(note)
        answers = []
        for index, question in enumerate(result.questions, start=1):
            answer = st.text_area(f"{index}. {question}", key=f"support_answer_{index}", max_chars=3000,
                placeholder="Informe apenas o que você confirmou. Pode responder: não sei ou não foi testado.")
            answers.append({"pergunta": question, "resposta": answer.strip()})
        # Apenas uma rodada de esclarecimentos: mantém a operação curta e o relato original
        # como fonte. A avaliação sugerida nunca vira diagnóstico automaticamente.
        if result.questions and st.button("Preparar avaliação com minhas respostas", disabled=not allowed or not any(a["resposta"] for a in answers)):
            try:
                with st.spinner("Preparando a avaliação para você conferir..."):
                    updated = generate_case_support(case, narrative, answers, api_key, model)
                st.session_state["support_edit"] = updated.assessment
                st.session_state["support_answers_hash"] = hashlib.sha256(str(answers).encode()).hexdigest()
                st.session_state["support_updated_notes"] = updated.notes
            except ValueError as exc:
                st.error(str(exc))
            except Exception as exc:
                st.error(error_message(exc) + " A sugestão anterior também foi mantida.")
        for note in st.session_state.get("support_updated_notes", ()):
            st.warning(note)
        if "support_answers_hash" in st.session_state and st.session_state["support_answers_hash"] != hashlib.sha256(str(answers).encode()).hexdigest():
            st.info("Você alterou as respostas. Prepare a avaliação novamente para incluí-las no texto abaixo.")
        edited = st.text_area("Avaliação preparada para revisão", key="support_edit", height=240, max_chars=20000)
        st.caption("Edite livremente. Ao usar este texto, ele substitui a avaliação acima; o relatório ainda será gerado e revisado no fluxo normal.")
        st.button("Usar este texto na avaliação", disabled=not edited.strip(), on_click=apply_support)
