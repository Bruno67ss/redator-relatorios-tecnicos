from pathlib import Path
import json
import os
from types import SimpleNamespace
from unittest.mock import Mock, patch
import pytest
from streamlit.testing.v1 import AppTest
from tests.scenarios import LEFT, RIGHT, CHARGER
from redator.case_support import CaseSupport
from redator.audio import TranscriptionError
from redator.filenames import report_filename
import streamlit as st
from streamlit.delta_generator import DeltaGenerator
import httpx
from openai import InternalServerError


def find(elements, label):
    return next(item for item in elements if item.label == label)


def new_app():
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py", default_timeout=30).run()
    assert not app.exception
    return app


def example_app():
    app = new_app()
    find(app.button, "Carregar exemplo fictício").click().run()
    find(app.radio, "Redação").set_value("Demonstração local").run()
    return app


def generate_example(app):
    find(app.button, "Gerar relatório para revisão").click().run()
    assert not app.exception and not app.error


def test_registration_has_one_shared_assessment_and_one_audio_control():
    app = new_app()
    assert app.session_state["equipment_ids"] == ["E1"]
    assert app.session_state["kind_E1"] == "Módulo eletrônico" and app.session_state["side_E1"] == ""
    assert [x.label for x in app.text_area] == ["Avaliação de todos os equipamentos"]
    assert len(app.audio_input) == 1
    assert not app.date_input and not app.number_input
    find(app.button, "＋ Adicionar equipamento").click().run()
    find(app.button, "＋ Adicionar equipamento").click().run()
    assert app.session_state["equipment_ids"] == ["E1", "E2", "E3"]
    assert len(app.text_area) == 1 and len(app.audio_input) == 1
    assert not app.exception


def support_ready_app():
    app = example_app()
    find(app.radio, "Redação").set_value("OpenAI").run()
    return app


def test_service_failure_shows_real_category_and_preserves_entered_case():
    app = support_ready_app()
    original = {key: app.session_state[key] for key in ("requester", "department", "general_assessment")}
    response = httpx.Response(503, request=httpx.Request("POST", "https://api.openai.com/v1/responses"))
    error = InternalServerError("PRIVATE_FAKE_KEY", response=response, body=None)
    with patch("redator.narrative.generate_narrative", side_effect=error):
        find(app.button, "Gerar relatório para revisão").click().run()
    assert any("503" in e.value for e in app.error)
    assert not any("PRIVATE" in e.value for e in app.error)
    assert all(app.session_state[key] == value for key, value in original.items())
    assert "draft" not in app.session_state and not app.exception


def test_optional_support_answers_then_applies_only_reviewed_assessment():
    app = support_ready_app()
    original = app.session_state["general_assessment"]
    initial = CaseSupport("Foi relatada falha de carga, de causa ainda não confirmada.", ("Qual teste foi realizado?",))
    updated = CaseSupport("Foi relatada falha de carga. O teste não foi realizado; a causa permanece não confirmada.")
    with patch("redator.support_ui.generate_case_support", return_value=initial):
        find(app.button, "Analisar meu relato").click().run()
    assert app.session_state["general_assessment"] == original and "draft" not in app.session_state
    find(app.text_area, "1. Qual teste foi realizado?").set_value("Não foi realizado.").run()
    with patch("redator.support_ui.generate_case_support", return_value=updated) as prepare:
        find(app.button, "Preparar avaliação com minhas respostas").click().run()
    assert prepare.call_args.args[2] == [{"pergunta": "Qual teste foi realizado?", "resposta": "Não foi realizado."}]
    assert app.session_state["general_assessment"] == original
    revised = updated.assessment + " Conferido pelo avaliador."
    find(app.text_area, "Avaliação preparada para revisão").set_value(revised).run()
    find(app.button, "Usar este texto na avaliação").click().run()
    assert app.session_state["general_assessment"] == revised and "draft" not in app.session_state
    assert "support_result" not in app.session_state and not app.exception


def test_support_is_optional_and_stale_suggestion_is_cleared():
    app = support_ready_app()
    assert not find(app.button, "Gerar relatório para revisão").disabled
    with patch("redator.support_ui.generate_case_support", return_value=CaseSupport("Sugestão antiga.")):
        find(app.button, "Analisar meu relato").click().run()
    find(app.text_area, "Avaliação de todos os equipamentos").set_value("Relato novo e diferente.").run()
    assert "support_result" not in app.session_state
    assert not any(t.label == "Avaliação preparada para revisão" for t in app.text_area)
    assert not app.exception


def test_review_changes_require_new_approval_but_no_organization_step():
    app = example_app()
    generate_example(app)
    assert len(app.text_area) == 2
    assert not any("organização" in x.label.lower() for x in app.expander)
    assert find(app.button, "Preparar documentos revisados").disabled
    find(app.checkbox, "Revisei o relatório e a identificação de todos os equipamentos e aprovo a emissão.").check().run()
    assert not find(app.button, "Preparar documentos revisados").disabled
    find(app.text_area, "Texto final editável").set_value(app.session_state["review_text"] + " Complemento revisado.").run()
    assert find(app.button, "Preparar documentos revisados").disabled
    find(app.text_area, "Avaliação de todos os equipamentos").set_value("Nova avaliação livre.").run()
    assert not any(t.label == "Texto final editável" for t in app.text_area)
    assert not app.exception


def test_audio_and_handwritten_text_share_the_same_box():
    app = example_app()
    find(app.text_area, "Avaliação de todos os equipamentos").set_value(RIGHT).run()
    with patch.dict(os.environ, {"OPENAI_API_KEY": "fake-test-key"}), patch("redator.audio_ui.transcribe_openai", return_value=CHARGER) as transcribe:
        app.audio_input[0].set_value(("clip.wav", b"RIFF-fake-local-audio", "audio/wav")).run()
        find(app.button, "Transcrever para a avaliação").click().run()
    assert RIGHT in app.session_state["general_assessment"]
    assert CHARGER in app.session_state["general_assessment"]
    assert len(app.text_area) == 1 and not app.exception
    assert transcribe.call_args.args[:2] == (b"RIFF-fake-local-audio", "clip.wav")


def test_preparing_word_really_succeeds_even_with_legacy_pending_flag():
    app = example_app()
    generate_example(app)
    app.session_state["details_dirty"] = True  # Reproduz o estado que bloqueava o teste do usuário.
    find(app.text_area, "Texto final editável").set_value(app.session_state["review_text"] + " Ajuste feito na revisão final.").run()
    find(app.checkbox, "Gerar também PDF usando o Word instalado").uncheck().run()
    find(app.checkbox, "Revisei o relatório e a identificação de todos os equipamentos e aprovo a emissão.").check().run()
    assert not find(app.button, "Preparar documentos revisados").disabled
    find(app.button, "Preparar documentos revisados").click().run()
    assert not app.error and not app.exception
    assert app.session_state["exports"]["docx"].startswith(b"PK")
    assert not any("ajustes de organização" in w.value for w in app.warning)


def test_word_and_pdf_downloads_receive_the_same_metadata_name():
    app = example_app()
    generate_example(app)
    find(app.checkbox, "Revisei o relatório e a identificação de todos os equipamentos e aprovo a emissão.").check().run()
    original_download = DeltaGenerator.download_button
    with patch("redator.documents.convert_pdf", return_value=b"%PDF-ficticio"), patch.object(DeltaGenerator, "download_button", autospec=True, side_effect=original_download) as downloads:
        find(app.button, "Preparar documentos revisados").click().run()
    assert not app.error and not app.exception
    exports = app.session_state["exports"]
    assert all(i.serial in exports["filename"].stem for i in app.session_state["report_case"].identities)
    names = [call.kwargs["file_name"] for call in downloads.call_args_list]
    assert names == [exports["filename"].for_extension("docx"), exports["filename"].for_extension("pdf")]
    assert app.session_state["report_case"].requester in names[0]


def test_destructive_term_warning_does_not_add_an_emission_block():
    app = example_app()
    find(app.text_area, "Avaliação de todos os equipamentos").set_value("Os filtros foram descritos como destruídos; conferir se estavam obstruídos por poeira.").run()
    assert any("Confira o termo" in w.value for w in app.warning)
    generate_example(app)
    find(app.checkbox, "Revisei o relatório e a identificação de todos os equipamentos e aprovo a emissão.").check().run()
    assert not find(app.button, "Preparar documentos revisados").disabled


def test_normal_generation_has_no_test_or_privacy_confirmation_and_preview_is_advanced():
    app = support_ready_app()
    assert not any("dados fictícios" in item.label or "Conferi a avaliação" in item.label for item in app.checkbox)
    assert not find(app.button, "Gerar relatório para revisão").disabled
    assert not find(app.button, "Analisar meu relato").disabled
    advanced = find(app.sidebar.expander, "Configurações avançadas da IA")
    assert len(advanced.code) == 1
    assert not app.main.code
    assert json.loads(advanced.code[0].value)["avaliacao"] == app.session_state["general_assessment"]


def test_normal_generation_keeps_registration_out_of_the_api_request():
    app = support_ready_app()
    find(app.text_input, "Solicitante").set_value("Cadastro Fictício Separado").run()
    client = Mock()
    client.responses.create.return_value = SimpleNamespace(status="completed", output_text=json.dumps({
        "paragraphs": ["Texto técnico fictício para revisão."], "complaints": [], "notes": []}))
    with patch.dict(os.environ, {"OPENAI_API_KEY": "fake-test-key"}), patch("redator.narrative.create_client", return_value=client):
        find(app.button, "Gerar relatório para revisão").click().run()
    assert not app.exception and not app.error
    request = client.responses.create.call_args.kwargs
    assert request["store"] is False
    payload = json.loads(request["input"])
    assert set(payload) == {"equipamentos", "avaliacao", "formato"}
    assert all(set(item) == {"alias", "tipo", "lado", "referencia"} for item in payload["equipamentos"])
    case = app.session_state["report_case"]
    for private in (case.requester, case.department, case.responsible, *(i.model for i in case.identities), *(i.serial for i in case.identities)):
        assert private not in request["input"]
    assert case.requester == "Cadastro Fictício Separado"
    assert find(app.button, "Preparar documentos revisados").disabled


@pytest.mark.parametrize("identifier", ["requester", "model_E1", "serial_E1", "email", "cpf", "phone"])
def test_suspected_identifiers_block_generation_and_support_before_sending(identifier):
    app = support_ready_app()
    examples = {"email": "pessoa@example.com", "cpf": "123.456.789-00", "phone": "(11) 99999-1234"}
    leak = examples[identifier] if identifier in examples else app.session_state[identifier]
    with patch("redator.narrative.create_client") as generation_client, patch("redator.case_support.create_client") as support_client:
        find(app.text_area, "Avaliação de todos os equipamentos").set_value("O módulo não liga. " + leak).run()
        assert find(app.button, "Gerar relatório para revisão").disabled
        assert find(app.button, "Analisar meu relato").disabled
        assert any("identifica" in warning.value.casefold() for warning in app.warning)
        generation_client.assert_not_called()
        support_client.assert_not_called()
        assert not app.exception


def test_correcting_a_suspected_identifier_releases_buttons_without_auto_sending():
    app = support_ready_app()
    find(app.text_area, "Avaliação de todos os equipamentos").set_value("Solicitante: Pessoa Fictícia").run()
    assert find(app.button, "Gerar relatório para revisão").disabled
    with patch("redator.narrative.create_client") as generation_client, patch("redator.case_support.create_client") as support_client:
        find(app.text_area, "Avaliação de todos os equipamentos").set_value("O módulo não liga.").run()
        assert not find(app.button, "Gerar relatório para revisão").disabled
        assert not find(app.button, "Analisar meu relato").disabled
        generation_client.assert_not_called()
        support_client.assert_not_called()
    assert not any("identifica" in warning.value.casefold() for warning in app.warning)


def test_support_answers_still_block_identifiers_before_the_api_call():
    app = support_ready_app()
    initial = CaseSupport("O módulo não liga.", ("Qual teste foi realizado?",))
    with patch("redator.support_ui.generate_case_support", return_value=initial):
        find(app.button, "Analisar meu relato").click().run()
    find(app.text_area, "1. Qual teste foi realizado?").set_value("pessoa@example.com").run()
    with patch("redator.case_support.create_client") as client:
        find(app.button, "Preparar avaliação com minhas respostas").click().run()
        client.assert_not_called()
    assert any("identificador" in error.value for error in app.error)
    assert app.session_state["support_edit"] == initial.assessment
    assert not app.exception


def test_local_demo_generates_without_confirmations_or_external_clients():
    app = example_app()
    with patch("redator.narrative.create_client") as generation_client, patch("redator.case_support.create_client") as support_client:
        generate_example(app)
        generation_client.assert_not_called()
        support_client.assert_not_called()
    assert not app.sidebar.code
    assert any("Demonstração da redação sem chamadas à IA" in caption.value for caption in app.sidebar.caption)


@pytest.mark.parametrize("replace", [False, True])
def test_online_transcription_failure_preserves_previous_text_and_review(replace):
    with patch.dict(os.environ, {"OPENAI_API_KEY": "fake-test-key"}):
        app = example_app()
        generate_example(app)
        original = app.session_state["general_assessment"]
        review = app.session_state["review_text"]
        app.audio_input[0].set_value(("clip.wav", b"RIFF-fake-audio", "audio/wav")).run()
        if replace:
            find(app.checkbox, "Substituir o texto atual da avaliação").check().run()
        with patch("redator.audio_ui.transcribe_openai", side_effect=TranscriptionError("Falha de transcrição; o texto anterior foi preservado.")):
            find(app.button, "Transcrever para a avaliação").click().run()
    assert app.session_state["general_assessment"] == original
    assert app.session_state["review_text"] == review
    assert any("texto anterior foi preservado" in error.value for error in app.error)
    assert not app.exception


def test_online_file_transcription_still_supports_explicit_replacement():
    app = example_app()
    with patch.dict(os.environ, {"OPENAI_API_KEY": "fake-test-key"}):
        find(app.radio, "Origem do áudio").set_value("Arquivo de áudio").run()
        app.file_uploader[0].set_value(("clip.mp3", b"fake-mp3-audio", "audio/mpeg")).run()
        find(app.checkbox, "Substituir o texto atual da avaliação").check().run()
        with patch("redator.audio_ui.transcribe_openai", return_value="Nova avaliação técnica.") as transcribe:
            find(app.button, "Transcrever para a avaliação").click().run()
    assert app.session_state["general_assessment"] == "Nova avaliação técnica."
    assert transcribe.call_args.args[:2] == (b"fake-mp3-audio", "clip.mp3")
    assert not app.exception


def test_transcription_requires_key_and_explains_remote_processing():
    app = example_app()
    with patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
        app.audio_input[0].set_value(("clip.wav", b"fake-audio", "audio/wav")).run()
    assert find(app.button, "Transcrever para a avaliação").disabled
    assert any("OPENAI_API_KEY" in message.value for message in app.info)
    assert any("O áudio será enviado à OpenAI" in message.value for message in app.caption)
