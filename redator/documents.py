"""DOCX local e PDF convertido pelo Word instalado, sem serviços online."""
from copy import deepcopy
from io import BytesIO
from pathlib import Path
import subprocess
import sys
import tempfile
from docx import Document
from docx.shared import Cm, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from .domain import Case, paragraphs, validate_review
from .report import build_report_body
from .settings import DEFAULT_CLOSING

TOKENS = ("{{LOCAL_DATA}}", "{{SOLICITANTE}}", "{{SETOR}}", "{{EQUIPAMENTOS}}", "{{CORPO}}", "{{RESPONSAVEL}}")
OPTIONAL_TOKENS = ("{{INTRODUCAO}}",)
MONTHS = ("Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro")


def format_location_date(city, value):
    display_city = "São Paulo" if city.strip() in ("São Paulo SP", "São Paulo - SP", "São Paulo/SP") else city.strip()
    return f"{display_city}, {value.day:02d} de {MONTHS[value.month - 1]} de {value.year}."


def introduction(case: Case) -> str:
    subject = "O equipamento identificado foi avaliado" if len(case.identities) == 1 else "Os equipamentos identificados foram avaliados"
    return subject + ". As observações e conclusões técnicas a seguir foram revisadas pelo profissional responsável."


def recipient_department(department: str, prefix: str = "") -> str:
    department, prefix = department.strip(), prefix.strip()
    if not prefix or department.casefold() == prefix.casefold() or department.casefold().startswith(prefix.casefold() + " "):
        return department
    return prefix + " " + department


def create_demo_template(path: Path):
    """Constrói do zero um modelo neutro, sem logotipo ou conteúdo institucional."""
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = Document()
    section = doc.sections[0]
    section.page_width, section.page_height = Cm(21), Cm(29.7)
    section.left_margin = section.right_margin = Cm(2.5)
    section.top_margin = section.bottom_margin = Cm(2.2)
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(11)
    normal.paragraph_format.space_after = Pt(8)
    normal.paragraph_format.line_spacing = 1.15
    normal.paragraph_format.widow_control = True
    section.header.paragraphs[0].text = "RELATÓRIO TÉCNICO DE MANUTENÇÃO"
    for value in ("{{LOCAL_DATA}}", "{{SETOR}}", "{{SOLICITANTE}}", "{{EQUIPAMENTOS}}",
                  "{{INTRODUCAO}}", "{{CORPO}}", "{{RESPONSAVEL}}"):
        paragraph = doc.add_paragraph(value)
        if value == "{{EQUIPAMENTOS}}":
            paragraph.paragraph_format.space_after = Pt(8)
        if value == "{{CORPO}}":
            paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    section.footer.paragraphs[0].text = "Documento sujeito à revisão do profissional responsável."
    doc.core_properties.author = ""
    doc.core_properties.last_modified_by = ""
    doc.core_properties.title = "Relatório técnico de manutenção"
    doc.core_properties.subject = ""
    doc.core_properties.comments = ""
    doc.save(path)


def generate_docx(case: Case, text: str, mode: str, template: Path, *, text_is_complete: bool = False,
                  closing: str = DEFAULT_CLOSING, responsible_role: str = "", department_prefix: str = "") -> bytes:
    case.validate_identity()
    validate_review(text, mode)
    doc = Document(template)
    body = text if text_is_complete else build_report_body(case, text, closing)
    # Cada marcador deve ocupar um parágrafo exclusivo no corpo, mesmo se dividido em runs.
    counts = {token: sum(p.text.strip() == token for p in doc.paragraphs) for token in TOKENS}
    if any(count != 1 for count in counts.values()):
        raise ValueError("Template inválido: cada marcador obrigatório deve ocupar um parágrafo exclusivo no corpo, uma vez.")
    # Evita exportar resíduos de identificação de um relatório reutilizado como template.
    if any(sum(p.text.strip() == token for p in doc.paragraphs) > 1 for token in OPTIONAL_TOKENS):
        raise ValueError("O template repete a introdução.")
    if any("{{" in p.text and p.text.strip() not in TOKENS + OPTIONAL_TOKENS for p in doc.paragraphs):
        raise ValueError("O template tem marcadores desconhecidos ou fora de parágrafos exclusivos.")
    equipment = [f"Ref.: {i.model} - {i.serial} ({i.kind.lower()}" + (f" {i.side.lower()}" if i.side else "") + ")" for i in case.identities]
    replacements = {
        "{{LOCAL_DATA}}": [format_location_date(case.city, case.report_date)],
        "{{SOLICITANTE}}": [f"Solicitante: {case.requester}"], "{{SETOR}}": [recipient_department(case.department, department_prefix)],
        "{{EQUIPAMENTOS}}": equipment, "{{CORPO}}": paragraphs(body),
        "{{INTRODUCAO}}": [introduction(case)],
        "{{RESPONSAVEL}}": [case.responsible] + ([responsible_role] if responsible_role else []),
    }
    for p in list(doc.paragraphs):
        if p.text.strip() not in replacements:
            continue
        token = p.text.strip()
        values = replacements[token]
        for index, value in enumerate(values):
            clone = deepcopy(p._p)
            p._p.addprevious(clone)
            from docx.text.paragraph import Paragraph
            new_p = Paragraph(clone, p._parent)
            # Preserva formato do primeiro run do marcador; nunca interpreta texto como template.
            formatting = deepcopy(new_p.runs[0]._r.rPr) if new_p.runs and new_p.runs[0]._r.rPr is not None else None
            new_p.clear()
            run = new_p.add_run(value)
            if token == "{{EQUIPAMENTOS}}" and index < len(values) - 1:
                new_p.paragraph_format.space_after = Pt(0)
                new_p.paragraph_format.keep_with_next = True
            if value == "Atenciosamente," or value in (case.responsible, responsible_role):
                new_p.paragraph_format.keep_with_next = value != (responsible_role or case.responsible)
            if formatting is not None:
                run._r.insert(0, formatting)
        p._p.getparent().remove(p._p)
    doc.core_properties.author = ""
    doc.core_properties.last_modified_by = ""
    doc.core_properties.title = "Relatório técnico"
    doc.core_properties.subject = ""
    doc.core_properties.comments = ""
    output = BytesIO()
    doc.save(output)
    return output.getvalue()


def convert_pdf(docx_bytes: bytes) -> bytes:
    if sys.platform != "win32":
        raise RuntimeError("A conversão PDF deste MVP requer Windows com Microsoft Word instalado.")
    with tempfile.TemporaryDirectory(prefix="relatorio-") as folder:
        source = Path(folder) / "relatório.docx"
        target = Path(folder) / "relatório.pdf"
        source.write_bytes(docx_bytes)
        # Processo separado: COM precisa de inicialização própria e limite de tempo.
        try:
            result = subprocess.run([sys.executable, "-m", "redator.word_pdf", str(source), str(target)],
                                    cwd=Path(__file__).resolve().parents[1], capture_output=True,
                                    timeout=60, creationflags=subprocess.CREATE_NO_WINDOW)
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("O Word excedeu o tempo de conversão. Baixe o Word e exporte para PDF manualmente.") from exc
        if result.returncode or not target.exists():
            raise RuntimeError("O Word não conseguiu converter. Verifique se está instalado e ativado; o DOCX continua disponível.")
        data = target.read_bytes()
        if not data.startswith(b"%PDF"):
            raise RuntimeError("O conversor não produziu um PDF válido.")
        return data
