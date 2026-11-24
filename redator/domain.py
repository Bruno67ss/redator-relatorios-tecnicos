from dataclasses import asdict, dataclass
from datetime import date
import hashlib
import json


@dataclass(frozen=True)
class TechnicalItem:
    alias: str
    observations: str
    procedures: str
    result: str
    conclusion: str


@dataclass(frozen=True)
class Identity:
    alias: str
    kind: str
    side: str
    model: str
    serial: str


@dataclass(frozen=True)
class Complaint:
    alias: str
    text: str


@dataclass(frozen=True)
class Case:
    requester: str
    department: str
    city: str
    report_date: date
    responsible: str
    identities: tuple[Identity, ...]
    technical: tuple[TechnicalItem, ...]
    complaints: tuple[Complaint, ...] = ()

    def validate_identity(self):
        if not all(s.strip() for s in (self.requester, self.department, self.city, self.responsible)):
            raise ValueError("Preencha solicitante, setor, cidade e responsável.")
        if not self.identities:
            raise ValueError("Adicione pelo menos um equipamento.")
        aliases = [i.alias for i in self.identities]
        if len(set(aliases)) != len(aliases) or aliases != [t.alias for t in self.technical]:
            raise ValueError("A identificação dos equipamentos está inconsistente.")
        if len({c.alias for c in self.complaints}) != len(self.complaints) or any(c.alias not in aliases for c in self.complaints):
            raise ValueError("Confira a relação de queixas e equipamentos.")
        serials = [normalize(i.serial) for i in self.identities if i.serial.strip() and normalize(i.serial) != "naoinformado"]
        if len(set(serials)) != len(serials):
            raise ValueError("Há números de série repetidos. Confira os equipamentos.")
        for i in self.identities:
            if not all(v.strip() for v in (i.kind, i.model, i.serial)):
                raise ValueError(f"Complete a identificação de {i.alias}; use 'Não informado' se necessário.")

    def validate(self):
        self.validate_identity()
        for t in self.technical:
            for value in (t.observations, t.procedures, t.result, t.conclusion):
                if not value.strip():
                    raise ValueError(f"Complete os quatro campos técnicos de {t.alias}.")
                if len(value) > 4000:
                    raise ValueError("Cada campo técnico aceita até 4.000 caracteres.")

    def fingerprint(self, mode: str) -> str:
        raw = json.dumps({"case": asdict(self), "mode": mode}, default=str, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()


def normalize(value: str) -> str:
    import re
    import unicodedata
    plain = unicodedata.normalize("NFKD", value.casefold())
    return re.sub(r"[^a-z0-9]", "", plain)


def paragraphs(text: str) -> list[str]:
    import re
    return [p.strip() for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]


def validate_review(text: str, mode: str):
    parts = paragraphs(text)
    if not parts:
        raise ValueError("O texto revisado não pode ficar vazio.")
    if len(text) > 30000:
        raise ValueError("O relatório ultrapassa 30.000 caracteres.")
    # Três parágrafos são o padrão de geração, não uma restrição à revisão humana.
