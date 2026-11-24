"""Nomes de download derivados exclusivamente do cadastro local."""
from dataclasses import dataclass
import hashlib
import re
import unicodedata
from .domain import Case
from .documents import recipient_department

MAX_STEM_UNITS = 220  # Deixa espaço para extensão e caminho usual de Downloads no Windows.


def units(value: str) -> int:
    return len(value.encode("utf-16-le")) // 2


def clean_part(value: str) -> str:
    value = unicodedata.normalize("NFC", value)
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f\x7f]', " ", value)
    return " ".join(value.split()).strip(" .")


def clip(value: str, limit: int) -> str:
    if units(value) <= limit:
        return value
    out = ""
    for char in value:
        if units(out + char) > limit - 3:
            break
        out += char
    return out.rstrip(" .") + "..."


@dataclass(frozen=True)
class ReportFilename:
    stem: str
    shortened: bool = False

    def for_extension(self, extension: str) -> str:
        extension = extension.lstrip(".").lower()
        if extension not in ("docx", "pdf"):
            raise ValueError("Formato de download inválido.")
        return self.stem + "." + extension


def report_filename(case: Case, department_prefix: str = "") -> ReportFilename:
    fields = [clean_part(recipient_department(case.department, department_prefix)) or "Setor",
              clean_part(case.requester) or "Solicitante"]
    minimums = [16, 24]
    for identity in case.identities:
        model = clean_part(identity.model) or "Modelo não informado"
        serial = clean_part(identity.serial) or "Série não informada"
        fields.extend([model, serial])
        minimums.extend([8, units(serial)])  # Prioriza preservar todas as séries completas.

    def render(values):
        equipment = " e ".join(values[i] + " - " + values[i + 1] for i in range(2, len(values), 2))
        return " - ".join(values[:2] + ([equipment] if equipment else []))

    full = render(fields)
    if units(full) <= MAX_STEM_UNITS:
        return ReportFilename(full)
    values = list(fields)
    limits = [units(v) for v in fields]
    # Encurta descrições extensas antes de tocar nos identificadores de série.
    while units(render(values)) > MAX_STEM_UNITS:
        candidates = [i for i in range(len(values)) if limits[i] > min(minimums[i], units(fields[i]))]
        if not candidates:
            break
        index = max(candidates, key=lambda i: limits[i] - min(minimums[i], units(fields[i])))
        excess = units(render(values)) - MAX_STEM_UNITS
        limits[index] = max(min(minimums[index], units(fields[index])), limits[index] - excess)
        values[index] = clip(fields[index], limits[index])
    stem = render(values)
    if units(stem) > MAX_STEM_UNITS:
        suffix = " - " + hashlib.sha256(full.encode()).hexdigest()[:10]
        stem = clip(stem, MAX_STEM_UNITS - units(suffix)) + suffix
    return ReportFilename(stem.rstrip(" ."), shortened=True)
