from dataclasses import replace
import re
import pytest
from redator.demo import demo_case
from redator.filenames import report_filename, units, MAX_STEM_UNITS
from redator.terminology import terminology_notes


def test_filenames_use_unit_requester_and_paired_model_serial_for_every_device():
    case = demo_case()
    name = report_filename(case, "Empresa Exemplo")
    assert name.stem == (f"Empresa Exemplo {case.department} - {case.requester} - "
                         f"{case.identities[0].model} - {case.identities[0].serial} e "
                         f"{case.identities[1].model} - {case.identities[1].serial}")
    assert name.for_extension("docx")[:-5] == name.for_extension("pdf")[:-4]
    assert not name.shortened


def test_same_model_with_two_different_serials_keeps_both_pairs():
    case = demo_case()
    case = replace(case, identities=(case.identities[0], replace(case.identities[1], model=case.identities[0].model)))
    name = report_filename(case)
    assert name.stem.count(case.identities[0].model) == 2
    assert all(i.serial in name.stem for i in case.identities)


def test_windows_characters_and_path_fragments_cannot_escape_the_filename():
    case = replace(demo_case(), department='Oficina Fictícia / Centro: "Exemplo"', requester='..\\Solicitante: Exemplo?')
    name = report_filename(case)
    assert not re.search(r'[<>:"/\\|?*\x00-\x1f]', name.stem)
    assert not name.stem.endswith((" ", ".")) and not name.stem.startswith(".")
    with pytest.raises(ValueError):
        name.for_extension("pdf.exe")


def test_long_names_are_abbreviated_before_serials():
    case = demo_case()
    case = replace(case, requester="Nome Fictício Muito Extenso " * 10, department="Setor Fictícia Muito Extensa " * 10,
                   identities=tuple(replace(i, model="Modelo Fictício Muito Extenso " * 10) for i in case.identities))
    name = report_filename(case)
    assert name.shortened and units(name.stem) <= MAX_STEM_UNITS
    assert all(i.serial in name.stem for i in case.identities)


def test_extreme_serial_lengths_still_produce_a_safe_deterministic_name():
    case = demo_case()
    identities = tuple(replace(case.identities[0], alias=f"E{i}", serial=str(i) * 100) for i in range(1, 5))
    case = replace(case, identities=identities)
    name = report_filename(case)
    assert units(name.stem) <= MAX_STEM_UNITS and name.shortened
    assert name == report_filename(case)


def test_terminology_warning_never_changes_destruction_into_obstruction():
    source = "Os filtros de ventilação estavam destruídos. Depois, relatou-se obstrução por poeira."
    assert terminology_notes(source)
    assert "destruídos" in source  # O aviso não altera a avaliação.
    assert not terminology_notes("Os filtros de ventilação estavam obstruídos por poeira.")
    assert not terminology_notes("Os filtros não estavam destruídos, apenas obstruídos.")
