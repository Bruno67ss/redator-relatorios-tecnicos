"""Abertura e encerramento determinísticos, montados sem chamada à IA."""
from .domain import Case
from .settings import DEFAULT_CLOSING
from .labels import equipment_names
import re


def complaint_phrase(text: str) -> str:
    text = " ".join(text.split()).strip(' \"“”').rstrip(".")
    # A IA às vezes devolve a expressão de ligação junto com a queixa.
    # Ela pertence à abertura local e deve aparecer uma única vez.
    return re.sub(r"^(?:(?:com\s+)?(?:a\s+)?queixa\s+de\s+)+", "", text, flags=re.I)


def opening_paragraphs(case: Case) -> list[str]:
    complaints = {c.alias: complaint_phrase(c.text) for c in case.complaints if c.text.strip()}
    # O próprio equipamento já é nomeado na abertura. Retira apenas uma referência
    # final ao seu lado cadastrado; sintomas, componentes e qualificações permanecem.
    for identity in case.identities:
        if (identity.alias in complaints and identity.kind.strip().casefold() == "módulo eletrônico"
                and identity.side in ("Esquerdo", "Direito")):
            text = complaints[identity.alias]
            reference = rf"\s+(?:do|no)\s+módulo(?:\s+eletrônico)?(?:\s+do\s+lado)?\s+{identity.side}$"
            complaints[identity.alias] = re.sub(reference, "", text, flags=re.I) or text
    names = equipment_names(case.identities, full=True)

    def listed(values):
        return values[0] if len(values) == 1 else ", ".join(values[:-1]) + " e " + values[-1]

    def group_name(identities):
        if (len(identities) == 2
                and all(i.kind.strip().casefold() == "módulo eletrônico" for i in identities)
                and {i.side for i in identities} == {"Esquerdo", "Direito"}):
            return "os módulos eletrônicos esquerdo e direito"
        return listed(["o " + names[i.alias] for i in identities])

    if not any(complaints.values()) and len(case.identities) == 2:
        return ["Recebemos " + group_name(case.identities) + " para avaliação técnica."]

    # Agrupa somente queixas com a mesma redação após retirar a referência ao próprio
    # equipamento, sem inferir sinônimos
    # ou estender a queixa a equipamentos que não a receberam explicitamente.
    groups = {}
    for identity in case.identities:
        complaint = complaints.get(identity.alias, "")
        key = (bool(complaint), complaint.casefold() if complaint else identity.alias)
        groups.setdefault(key, []).append(identity)
    descriptions, shared = [], []
    for identities in groups.values():
        label = group_name(identities)
        if complaint := complaints.get(identities[0].alias):
            label += f" com a queixa de {complaint}"
            if len(identities) > 1:
                shared.append((identities, label))
        descriptions.append(label)
    if len(shared) == 1:
        identities, label = shared[0]
        aliases = {i.alias for i in identities}
        others = [i for i in case.identities if i.alias not in aliases]
        if others and all(not complaints.get(i.alias) for i in others):
            return ["Recebemos " + label + ", juntamente com " + group_name(others) + ", para avaliação técnica."]
    suffix = "." if len(descriptions) == 1 and any(complaints.values()) else " para avaliação técnica."
    return ["Recebemos " + listed(descriptions) + suffix]


def build_report_body(case: Case, technical_text: str, closing: str = DEFAULT_CLOSING) -> str:
    return "\n\n".join(opening_paragraphs(case) + [technical_text.strip(), closing.strip(), "Atenciosamente,"])
