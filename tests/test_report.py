from dataclasses import replace
from io import BytesIO
import pytest
from docx import Document
from redator.demo import demo_case
from redator.domain import Complaint
from redator.documents import create_demo_template, generate_docx
from redator.narrative import generate_demo_narrative
from redator.report import build_report_body, opening_paragraphs
from tests.scenarios import three_device_case


def single_case():
    case = demo_case()
    return replace(case, identities=case.identities[:1], technical=case.technical[:1],
                   complaints=(Complaint("E1", "falha de carregamento"),))


def test_opening_uses_professional_complaint_without_literal_quotes_and_closes_locally():
    case = single_case()
    text = build_report_body(case, generate_demo_narrative(case, "Avaliação sintética sem novos achados.", "Objetivo").text)
    assert text.startswith('Recebemos o módulo eletrônico direito com a queixa de falha de carregamento.')
    assert "Qualquer dúvida em relação ao exposto, por favor, entre em contato." in text
    assert text.endswith("Atenciosamente,")
    assert "E1:" not in text
    assert '“' not in opening_paragraphs(replace(case, complaints=()))[0]


def test_opening_does_not_repeat_complaint_prefix_returned_by_model():
    case = replace(single_case(), complaints=(Complaint("E1", "com a queixa de problema no funcionamento da bateria"),))
    opening = opening_paragraphs(case)[0]
    assert opening == "Recebemos o módulo eletrônico direito com a queixa de problema no funcionamento da bateria."


@pytest.mark.parametrize("complaints,expected", [
    ((), "Recebemos os módulos eletrônicos esquerdo e direito para avaliação técnica."),
    ((Complaint("E1", "falha de autonomia"), Complaint("E2", "falha de autonomia")),
     "Recebemos os módulos eletrônicos esquerdo e direito com a queixa de falha de autonomia."),
])
def test_pair_with_same_complaint_has_one_plural_opening(complaints, expected):
    case = three_device_case()
    case = replace(case, identities=case.identities[:2], technical=case.technical[:2], complaints=complaints)
    assert opening_paragraphs(case) == [expected]


def test_different_or_missing_complaints_remain_attached_to_their_device():
    case = three_device_case()
    case = replace(case, identities=case.identities[:2], technical=case.technical[:2], complaints=(
        Complaint("E1", "falha de autonomia"), Complaint("E2", "ausência de sinal")))
    opening = opening_paragraphs(case)[0]
    assert "esquerdo com a queixa de falha de autonomia" in opening
    assert "direito com a queixa de ausência de sinal" in opening
    missing = opening_paragraphs(replace(case, complaints=case.complaints[:1]))[0]
    assert "esquerdo com a queixa de falha de autonomia" in missing
    assert "direito com a queixa" not in missing


def test_charger_and_unknown_sides_are_not_included_in_a_named_electronic_module_pair():
    case = three_device_case()
    opening = opening_paragraphs(case)[0]
    assert "carregador" in opening and "eletrônicos esquerdo e direito" not in opening
    unknown = replace(case, identities=tuple(replace(i, side="") for i in case.identities[:2]), technical=case.technical[:2])
    assert "primeiro módulo eletrônico" in opening_paragraphs(unknown)[0]
    assert "esquerdo e direito" not in opening_paragraphs(unknown)[0]


def test_complete_review_is_not_wrapped_twice_and_role_is_added(tmp_path):
    case = single_case()
    path = tmp_path / "template.docx"
    create_demo_template(path)
    full = build_report_body(case, generate_demo_narrative(case, "Avaliação sintética sem novos achados.", "Objetivo").text)
    data = generate_docx(case, full, "Objetivo", path, text_is_complete=True, responsible_role="Supervisor de exemplo")
    text = "\n".join(p.text for p in Document(BytesIO(data)).paragraphs)
    assert text.count("Recebemos") == 1 and text.count("Qualquer dúvida") == 1
    assert "Supervisor de exemplo" in text and case.responsible in text


def test_shared_complaint_groups_electronic_modules_with_an_unassigned_charger():
    case = replace(three_device_case(), complaints=(
        Complaint("E1", "falha no carregamento"), Complaint("E2", "falha no carregamento")))
    assert opening_paragraphs(case) == [
        "Recebemos os módulos eletrônicos esquerdo e direito com a queixa de falha no carregamento, "
        "juntamente com o carregador, para avaliação técnica."
    ]


def test_grouping_normalizes_case_spacing_and_complaint_prefix_only():
    case = replace(three_device_case(), complaints=(
        Complaint("E1", "com a queixa de falha no carregamento."),
        Complaint("E2", "Falha   no carregamento")))
    assert opening_paragraphs(case)[0].count("com a queixa de") == 1
    assert "módulos eletrônicos esquerdo e direito" in opening_paragraphs(case)[0]


def test_different_charger_complaint_remains_separate_from_the_shared_pair():
    case = replace(three_device_case(), complaints=(
        Complaint("E1", "falha no carregamento"), Complaint("E2", "falha no carregamento"),
        Complaint("E3", "aquecimento")))
    opening = opening_paragraphs(case)[0]
    assert "módulos eletrônicos esquerdo e direito com a queixa de falha no carregamento" in opening
    assert "o carregador com a queixa de aquecimento" in opening
    assert opening.count("falha no carregamento") == 1


def test_different_complaints_with_a_charger_are_never_merged():
    case = replace(three_device_case(), complaints=(
        Complaint("E1", "falha no carregamento"), Complaint("E2", "ausência de sinal")))
    opening = opening_paragraphs(case)[0]
    assert "esquerdo com a queixa de falha no carregamento" in opening
    assert "direito com a queixa de ausência de sinal" in opening
    assert "carregador com a queixa" not in opening


def test_shared_complaint_does_not_invent_sides_for_unidentified_devices():
    case = three_device_case()
    case = replace(case, identities=tuple(replace(i, side="") for i in case.identities), complaints=(
        Complaint("E1", "falha no carregamento"), Complaint("E2", "falha no carregamento")))
    opening = opening_paragraphs(case)[0]
    assert "primeiro módulo eletrônico" in opening and "segundo módulo eletrônico" in opening
    assert "esquerdo" not in opening and "direito" not in opening
    assert opening.count("com a queixa de") == 1


def test_grouping_keeps_alias_side_mapping_even_when_registration_order_changes():
    case = three_device_case()
    case = replace(case, identities=(case.identities[1], case.identities[2], case.identities[0]),
                   technical=(case.technical[1], case.technical[2], case.technical[0]), complaints=(
                       Complaint("E2", "falha no carregamento"), Complaint("E1", "falha no carregamento")))
    opening = opening_paragraphs(case)[0]
    assert "módulos eletrônicos esquerdo e direito" in opening
    assert opening.count("carregador") == 1 and opening.count("falha no carregamento") == 1
    assert "carregador com a queixa" not in opening


@pytest.mark.parametrize("with_charger", [False, True])
def test_same_symptom_with_own_side_references_is_grouped(with_charger):
    case = three_device_case()
    if not with_charger:
        case = replace(case, identities=case.identities[:2], technical=case.technical[:2])
    case = replace(case, complaints=(
        Complaint("E1", "Intermitência no funcionamento do módulo esquerdo."),
        Complaint("E2", "Intermitência no funcionamento do módulo direito.")))
    opening = opening_paragraphs(case)[0]
    assert "os módulos eletrônicos esquerdo e direito" in opening
    assert opening.count("Intermitência no funcionamento") == 1
    assert "do módulo esquerdo" not in opening and "do módulo direito" not in opening
    assert ("juntamente com o carregador" in opening) == with_charger


@pytest.mark.parametrize("left,right", [
    ("intermitência no funcionamento do módulo esquerdo", "ausência de sinal do módulo direito"),
    ("falha após cinco horas no módulo esquerdo", "falha após sete horas no módulo direito"),
    ("suspeita de falha do módulo esquerdo", "falha confirmada do módulo direito"),
    ("não apresenta intermitência no módulo esquerdo", "apresenta intermitência no módulo direito"),
    ("falha no sensor esquerdo", "falha no sensor direito"),
    ("intermitência do módulo direito", "intermitência do módulo direito"),
])
def test_different_symptoms_qualifications_or_inconsistent_sides_remain_separate(left, right):
    case = replace(three_device_case(), complaints=(Complaint("E1", left), Complaint("E2", right)))
    opening = opening_paragraphs(case)[0]
    assert "os módulos eletrônicos esquerdo e direito" not in opening
    assert opening.count("com a queixa de") == 2
    assert "módulo eletrônico esquerdo" in opening and "módulo eletrônico direito" in opening


def test_removing_own_side_reference_preserves_hypothesis_and_technical_paragraphs():
    case = replace(three_device_case(), complaints=(
        Complaint("E1", "suspeita de intermitência no módulo eletrônico do lado esquerdo"),
        Complaint("E2", "suspeita de intermitência no módulo eletrônico do lado direito")))
    technical = "Cinco horas à esquerda e sete à direita.\n\nA falha não foi reproduzida.\n\nNão realizamos substituição."
    body = build_report_body(case, technical)
    assert "com a queixa de suspeita de intermitência" in body
    assert body.split("\n\n")[1:4] == technical.split("\n\n")
