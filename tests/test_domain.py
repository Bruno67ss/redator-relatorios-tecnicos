from dataclasses import replace
import pytest
from redator.demo import demo_case
from redator.domain import Identity, TechnicalItem
from redator.labels import equipment_names, naturalize_references
from redator.narrative import build_narrative_payload
from redator.privacy import assert_deidentified

def test_duplicate_serials_are_normalized_before_validation():
    case = demo_case()
    case = replace(case, identities=(case.identities[0], replace(case.identities[1], serial="demo 001")))
    with pytest.raises(ValueError, match="repetidos"):
        case.validate_identity()

def test_missing_registration_prevents_emission():
    with pytest.raises(ValueError, match="Preencha"):
        replace(demo_case(), requester="").validate_identity()

def test_generic_equipment_uses_distinct_natural_references():
    identities = (Identity("E1", "Controlador", "", "Sintético A", "SINT-A"),
                  Identity("E2", "Controlador", "", "Sintético B", "SINT-B"))
    assert equipment_names(identities) == {"E1": "primeiro controlador", "E2": "segundo controlador"}
    text = naturalize_references("E1 não liga. E2 funciona.", identities)
    assert "primeiro controlador não liga" in text and "segundo controlador funciona" in text

def test_registration_is_absent_and_identifiers_in_narrative_are_blocked():
    case = demo_case()
    payload = build_narrative_payload(case, "O carregador não ligou no teste.")
    assert_deidentified(case, payload)
    with pytest.raises(ValueError, match="identificação"):
        assert_deidentified(case, build_narrative_payload(case, "Avaliação de " + case.requester))
