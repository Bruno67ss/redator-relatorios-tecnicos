from dataclasses import replace
from io import BytesIO
import json
import re
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from docx import Document
from redator.domain import Identity
from redator.flow import initialize
from redator.narrative import generate_narrative, build_narrative_payload, explicit_complaints, remove_generic_receipt
from redator.labels import naturalize_references
from redator.report import build_report_body
from redator.documents import create_demo_template, generate_docx
from tests.scenarios import (three_device_case, combined_assessment, three_device_response,
                             shared_charging_assessment, shared_charging_response, LEFT, RIGHT, CHARGER)


def fake_client(response=None):
    client = Mock()
    client.responses.create.return_value = SimpleNamespace(status="completed", output_text=json.dumps(response or three_device_response()))
    return client


def test_three_devices_need_no_formal_conclusion_field_and_use_natural_names():
    case = three_device_case()
    client = fake_client()
    draft = generate_narrative(case, combined_assessment(), "Objetivo", "fake-test-key", "test-model", client=client)
    assert "funcionamento ficou dentro dos padrões" in draft.text
    assert "módulo esquerdo" in draft.text and "módulo direito" in draft.text and "carregador" in draft.text
    assert not re.search(r"\bE\d+\b", draft.text)
    request = client.responses.create.call_args.kwargs
    assert request["store"] is False and "tools" not in request
    assert re.fullmatch(r"[A-Za-z0-9_-]{1,64}", request["text"]["format"]["name"])
    assert "missing_conclusions" not in request["text"]["format"]["schema"]["properties"]
    assert json.loads(request["input"]) == build_narrative_payload(case, combined_assessment())
    for private in (case.requester, case.department, case.responsible, case.identities[0].model, case.identities[0].serial):
        assert private not in request["input"]


def test_an_actual_missing_conclusion_does_not_create_one_or_block_a_draft():
    response = {"paragraphs": ["O carregador foi recebido para avaliação. Foi observada sujidade na carcaça."],
                "complaints": [], "notes": ["O relato não informa testes ou um desfecho para o carregador."]}
    case = three_device_case()
    draft = generate_narrative(case, "Foi observada sujidade na carcaça do carregador.", "Objetivo", "fake-test-key", "test-model", client=fake_client(response))
    assert draft.text and draft.notes
    assert "troca" not in draft.text and "dentro dos padrões" not in draft.text


def test_a_manually_typed_legacy_alias_is_converted_to_a_natural_reference():
    text = naturalize_references("E1: Estrutura danificada. E2: Sem sucesso. E3: Funcionamento dentro dos padrões.", three_device_case().identities)
    assert "módulo esquerdo" in text and "módulo direito" in text and "carregador" in text
    assert not re.search(r"\bE\d+\b", text)


def test_migration_preserves_handwritten_right_device_alongside_dictated_text():
    case = three_device_case()
    state = {"ui_version": 3, "equipment_ids": ["E1", "E2", "E3"], "next_equipment": 4,
             "assessment_E1": LEFT, "assessment_E2": RIGHT, "assessment_E3": CHARGER,
             "details_dirty": True}
    for i in case.identities:
        state[f"kind_{i.alias}"], state[f"side_{i.alias}"] = i.kind, i.side
    initialize(state)
    assert state["ui_version"] == 4
    assert all(value in state["general_assessment"] for value in (LEFT, RIGHT, CHARGER))
    assert "details_dirty" not in state


def test_complete_review_exports_even_without_four_internal_sections(tmp_path):
    case = three_device_case()  # Categorias vazias de propósito: o relato é a fonte única.
    draft = generate_narrative(case, combined_assessment(), "Objetivo", "fake-test-key", "test-model", client=fake_client())
    case = replace(case, complaints=draft.complaints)
    template = tmp_path / "template.docx"
    create_demo_template(template)
    body = build_report_body(case, draft.text)
    data = generate_docx(case, body, "Objetivo", template, text_is_complete=True)
    text = "\n".join(p.text for p in Document(BytesIO(data)).paragraphs)
    assert "carregador" in text.lower() and "SINT-003" in text
    assert "Recebemos" in text and not re.search(r"\bE[123]\b", text)


def test_names_in_the_single_assessment_are_blocked_before_the_api():
    case = three_device_case()
    client = fake_client()
    with pytest.raises(ValueError, match="identificação"):
        generate_narrative(case, "Avaliação de " + case.requester, "Objetivo", "fake-test-key", "test-model", client=client)
    client.responses.create.assert_not_called()


def test_generic_word_requester_does_not_match_a_fictional_requester_name():
    from redator.privacy import assert_deidentified
    case = replace(three_device_case(), requester="Solicitante Exemplo")
    payload = build_narrative_payload(case, "O solicitante relatou falha e o equipamento foi avaliado.")
    assert assert_deidentified(case, payload) == payload


def test_missing_model_complaint_uses_generic_opening_instead_of_copying_raw_speech():
    case = three_device_case()
    response = three_device_response()
    response["complaints"] = []
    draft = generate_narrative(case, combined_assessment(), "Objetivo", "fake-test-key", "test-model", client=fake_client(response))
    assert not draft.complaints
    assert any("não foi reformulada" in note for note in draft.notes)
    assert not explicit_complaints(case, "Recebemos um módulo com queixa de não carregar.")


def test_informal_complaint_is_formalized_with_literal_evidence_kept_out_of_report():
    case = three_device_case()
    narrative = "Recebemos o módulo esquerdo com queixa de que deu pau de bateria, né? Acho que é o circuito, mas não confirmei."
    response = {"paragraphs": ["Há suspeita de falha no circuito do módulo esquerdo, ainda não confirmada."],
                "complaints": [{"alias": "E1", "text": "falha no funcionamento da bateria",
                                "source_quote": "deu pau de bateria, né"}], "notes": []}
    draft = generate_narrative(case, narrative, "Objetivo", "fake-key", "test-model", client=fake_client(response))
    body = build_report_body(replace(case, complaints=draft.complaints), draft.text)
    assert "queixa de falha no funcionamento da bateria" in body
    assert "suspeita" in body and "não confirmada" in body
    assert "deu pau" not in body and "né" not in body and "“" not in body


@pytest.mark.parametrize("evidence", ["", "o módulo foi danificado por água", None])
def test_unsupported_complaint_evidence_is_not_published_or_replaced_by_raw_fallback(evidence):
    case = three_device_case()
    response = {"paragraphs": ["O módulo esquerdo não liga."], "notes": [],
                "complaints": [{"alias": "E1", "text": "dano por água", "source_quote": evidence}]}
    draft = generate_narrative(case, "Recebemos o módulo esquerdo com queixa de que pifou.", "Objetivo", "fake-key", "test-model", client=fake_client(response))
    assert not draft.complaints and draft.notes
    opening = build_report_body(replace(case, complaints=draft.complaints), draft.text).split("\n\n")[0]
    assert "dano por água" not in opening and "pifou" not in opening


def test_complaints_for_multiple_devices_keep_their_own_professional_wording():
    response = {"paragraphs": ["O módulo esquerdo não liga. O módulo direito apresenta falha de carga."], "notes": [],
                "complaints": [
                    {"alias": "E1", "text": "ausência de funcionamento", "source_quote": "o esquerdo pifou"},
                    {"alias": "E2", "text": "falha de carregamento", "source_quote": "o direito não carrega"}]}
    draft = generate_narrative(three_device_case(), "Na entrada, o esquerdo pifou e o direito não carrega.", "Objetivo", "fake-key", "test-model", client=fake_client(response))
    assert [(c.alias, c.text) for c in draft.complaints] == [("E1", "ausência de funcionamento"), ("E2", "falha de carregamento")]


def test_model_generic_receipt_is_not_duplicated_and_physical_findings_remain():
    case = three_device_case()
    response = {"paragraphs": ["Recebemos os módulos esquerdo e direito para avaliação. Ambos estão íntegros e sem oxidação."],
                "complaints": [], "notes": []}
    draft = generate_narrative(case, "Ambos os módulos estão íntegros e sem oxidação.", "Detalhado", "fake-key", "test-model", client=fake_client(response))
    assert draft.text == "Ambos estão íntegros e sem oxidação."
    body = build_report_body(case, draft.text)
    assert body.count("Recebemos") == 1


@pytest.mark.parametrize("text", [
    "Recebemos os módulos com ruído elétrico para avaliação. Os testes confirmaram falha nos conectores.",
    "Recebemos o módulo esquerdo com queixa de baixa autonomia. A falha não foi reproduzida.",
    "Na avaliação, ambos apresentaram ruído elétrico. Recomendamos troca dos módulos.",
])
def test_receipt_cleanup_preserves_technical_details_and_ordinary_paragraphs(text):
    assert remove_generic_receipt(text, three_device_case().identities) == text


@pytest.mark.parametrize("source", [
    shared_charging_assessment(),
    "Recebemos ambos os módulos eletrônicos com queixa de falha no carregamento.",
    "Recebemos os dois módulos com queixa de falha no carregamento.",
    "Recebemos os módulos eletrônicos direito e esquerdo com queixa de falha no carregamento.",
])
def test_explicit_shared_complaint_identifies_both_electronic_modules_only(source):
    complaints = explicit_complaints(three_device_case(), source)
    assert {c.alias for c in complaints} == {"E1", "E2"}


@pytest.mark.parametrize("mode", ["Objetivo", "Detalhado"])
def test_shared_charging_case_has_no_false_charger_warning_and_keeps_technical_text(mode):
    case = three_device_case()
    response = shared_charging_response()
    client = fake_client(response)
    draft = generate_narrative(case, shared_charging_assessment(), mode, "fake-key", "test-model", client=client)
    assert not draft.notes
    assert {c.alias for c in draft.complaints} == {"E1", "E2"}
    assert draft.text == "\n\n".join(response["paragraphs"])
    body = build_report_body(replace(case, complaints=draft.complaints), draft.text)
    assert body.split("\n\n")[1:4] == response["paragraphs"]
    assert body.count("queixa de falha no carregamento") == 1
    assert "juntamente com o carregador" in body
    assert "A substituição ainda não foi realizada." in body


@pytest.mark.parametrize("missing_alias,missing_name", [("E1", "módulo esquerdo"), ("E2", "módulo direito")])
def test_shared_complaint_missing_one_device_keeps_a_specific_warning(missing_alias, missing_name):
    response = shared_charging_response()
    response["complaints"] = [c for c in response["complaints"] if c["alias"] != missing_alias]
    draft = generate_narrative(three_device_case(), shared_charging_assessment(), "Objetivo", "fake-key", "test-model", client=fake_client(response))
    warning = next(note for note in draft.notes if "não foi reformulada" in note)
    assert missing_name in warning and "carregador" not in warning
    assert missing_alias not in {c.alias for c in draft.complaints}


def test_actual_charger_complaint_is_not_hidden_by_electronic_module_grouping():
    source = shared_charging_assessment() + " O carregador chegou também com queixa de aquecimento."
    draft = generate_narrative(three_device_case(), source, "Objetivo", "fake-key", "test-model", client=fake_client(shared_charging_response()))
    assert any("não foi reformulada" in note and "carregador" in note for note in draft.notes)


def test_equipment_without_identifiable_complaint_does_not_receive_a_warning():
    source = "O carregador apresentava sujeira nos contatos. A limpeza restabeleceu o carregamento."
    response = {"paragraphs": [source], "complaints": [], "notes": []}
    draft = generate_narrative(three_device_case(), source, "Objetivo", "fake-key", "test-model", client=fake_client(response))
    assert not draft.complaints and not draft.notes
    assert "com a queixa" not in build_report_body(three_device_case(), draft.text)


def test_shared_complaint_with_invalid_evidence_remains_a_warning():
    response = shared_charging_response()
    response["complaints"][1]["source_quote"] = "trecho inexistente no relato"
    draft = generate_narrative(three_device_case(), shared_charging_assessment(), "Objetivo", "fake-key", "test-model", client=fake_client(response))
    assert {c.alias for c in draft.complaints} == {"E1"}
    assert any("origem da queixa" in note for note in draft.notes)
    assert any("não foi reformulada" in note and "módulo direito" in note for note in draft.notes)
