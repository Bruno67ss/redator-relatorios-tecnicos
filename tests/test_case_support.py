from dataclasses import replace
import json
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from redator.case_support import generate_case_support
from redator.narrative import build_narrative_payload, generate_narrative
from redator.privacy import assert_deidentified
from tests.scenarios import three_device_case


def client_for(data):
    client = Mock()
    client.responses.create.return_value = SimpleNamespace(status="completed", output_text=json.dumps(data))
    return client


def test_common_surname_word_does_not_block_a_technical_sentence():
    case = replace(three_device_case(), responsible="Prof. Avaliador Claro")
    payload = build_narrative_payload(case, "É claro que o carregador apresentou indicação vermelha. A causa ainda não foi confirmada.")
    assert assert_deidentified(case, payload) == payload


@pytest.mark.parametrize("leak", ["Avaliador", "Avaliador Claro", "Prof. Avaliador Claro", "Solicitante Simulado", "Fictício A", "SINT-001", "S I N T 0 0 1"])
def test_identifiers_still_block_before_support_api(leak):
    case = replace(three_device_case(), responsible="Prof. Avaliador Claro")
    client = client_for({})
    with pytest.raises(ValueError, match="identificação"):
        generate_case_support(case, "Foi observada luz vermelha.", [{"pergunta": "O que foi testado?", "resposta": leak}], "fake-key", "test-model", client=client)
    client.responses.create.assert_not_called()


def test_short_model_does_not_match_inside_a_technical_word():
    case = three_device_case()
    case = replace(case, identities=(replace(case.identities[0], model="XYZ"), *case.identities[1:]))
    assert_deidentified(case, build_narrative_payload(case, "O circuito apresentou falha elétrica."))
    with pytest.raises(ValueError):
        assert_deidentified(case, build_narrative_payload(case, "O modelo XYZ apresentou falha."))


def test_support_keeps_uncertainty_and_sends_only_technical_data_and_answers():
    case = three_device_case()
    response = {"assessment": "O módulo esquerdo não carregou e apresentou luz vermelha. A causa não foi confirmada.",
                "questions": [], "notes": ["Consulte documentação para interpretar o código luminoso."]}
    client = client_for(response)
    answers = [{"pergunta": "Qual componente foi confirmado como defeituoso?", "resposta": "Não sei; não foi confirmado."}]
    result = generate_case_support(case, "O módulo esquerdo não carregou e mostrou luz vermelha.", answers, "fake-key", "test-model", client=client)
    assert result.assessment == response["assessment"] and not result.questions
    request = client.responses.create.call_args.kwargs
    assert request["store"] is False and "tools" not in request and "previous_response_id" not in request
    data = json.loads(request["input"])
    assert data["esclarecimentos"] == answers and set(data) == {"equipamentos", "avaliacao", "esclarecimentos"}
    for private in (case.requester, case.department, case.responsible, case.identities[0].model, case.identities[0].serial):
        assert private not in request["input"]


@pytest.mark.parametrize("data", [
    {"assessment": "", "questions": [], "notes": []},
    {"assessment": "Texto", "questions": ["A?", "B?", "C?", "D?"], "notes": []},
    {"assessment": "Texto", "questions": "Pergunta?", "notes": []},
])
def test_invalid_support_response_is_rejected(data):
    with pytest.raises(ValueError, match="ajuda válida"):
        generate_case_support(three_device_case(), "O carregador não ligou.", [], "fake-key", "test-model", client=client_for(data))


def test_detailed_and_objective_send_distinct_style_directions():
    data = {"paragraphs": ["O carregador foi limpo e voltou a funcionar."], "complaints": [], "notes": []}
    calls = []
    for mode in ("Objetivo", "Detalhado"):
        client = client_for(data)
        generate_narrative(three_device_case(), "O carregador foi limpo e voltou a funcionar.", mode, "fake-key", "test-model", client=client)
        calls.append(client.responses.create.call_args.kwargs["instructions"])
    assert calls[0] != calls[1]
    assert "Modo Objetivo: prefira três parágrafos: observações, parecer e conclusão" in calls[0]
    assert "use mais parágrafos quando necessário" in calls[0]
    assert "Modo Detalhado: aprofunde e organize o conteúdo conforme a complexidade do caso" in calls[1]
    assert "sem número fixo de parágrafos, contagem mínima de palavras ou proporção" in calls[1]
    assert "4 a 7" not in calls[1] and "1,5 a 2" not in calls[1]
