from dataclasses import replace
from datetime import date
from io import BytesIO
from zipfile import ZipFile
import pytest
from docx import Document
from redator.demo import demo_case
from redator.documents import create_demo_template, generate_docx, introduction, format_location_date
from redator.domain import validate_review

def test_neutral_document_has_only_synthetic_metadata_and_preserves_review(tmp_path):
    case = demo_case()
    template = tmp_path / "neutral.docx"
    create_demo_template(template)
    reviewed = "A falha não foi reproduzida. Nenhum reparo foi realizado.\n\nHipótese ainda não confirmada."
    data = generate_docx(case, reviewed, "Objetivo", template, text_is_complete=True)
    doc = Document(BytesIO(data))
    lines = [p.text for p in doc.paragraphs]
    assert all(part in lines for part in reviewed.split("\n\n"))
    assert "Solicitante: " + case.requester in lines
    assert case.department in lines and case.responsible in lines
    assert all(i.model in " ".join(lines) and i.serial in " ".join(lines) for i in case.identities)
    assert not any("{{" in line for line in lines)
    assert doc.core_properties.author == doc.core_properties.last_modified_by == ""
    with ZipFile(BytesIO(data)) as archive:
        assert not any(name.startswith("word/media/") for name in archive.namelist())
    assert "RELATÓRIO TÉCNICO" in doc.sections[0].header.paragraphs[0].text

def test_invalid_template_and_empty_review_are_rejected(tmp_path):
    template = tmp_path / "invalid.docx"
    Document().save(template)
    with pytest.raises(ValueError, match="Template"):
        generate_docx(demo_case(), "Texto revisado.", "Objetivo", template)
    with pytest.raises(ValueError, match="vazio"):
        validate_review("", "Objetivo")

def test_introduction_and_date_are_generic():
    case = demo_case()
    assert "Os equipamentos identificados" in introduction(case)
    assert "O equipamento identificado" in introduction(replace(case, identities=case.identities[:1]))
    assert format_location_date("Cidade Exemplo", date(2026, 1, 15)) == "Cidade Exemplo, 15 de Janeiro de 2026."
