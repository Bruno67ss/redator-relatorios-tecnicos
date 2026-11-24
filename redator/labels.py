"""Referências de leitura derivadas do cadastro, sem códigos internos no relatório."""
from collections import Counter
import re


def equipment_names(identities, *, full=False) -> dict[str, str]:
    bases = []
    for identity in identities:
        kind = " ".join(identity.kind.split()).lower()
        base = kind if full or kind != "módulo eletrônico" else "módulo"
        if identity.side in ("Direito", "Esquerdo"):
            base += " " + identity.side.lower()
        bases.append(base)
    counts, seen = Counter(bases), Counter()
    ordinals = ("primeiro", "segundo", "terceiro", "quarto", "quinto", "sexto", "sétimo", "oitavo", "nono", "décimo")
    result = {}
    for identity, base in zip(identities, bases):
        seen[base] += 1
        if counts[base] > 1:
            n = seen[base]
            base = f"{ordinals[n-1]} {base}" if n <= len(ordinals) else f"{base} de ordem {n}"
        result[identity.alias] = base
    return result


def naturalize_references(text: str, identities) -> str:
    names = equipment_names(identities)
    for alias in sorted(names, key=len, reverse=True):
        escaped = re.escape(alias)
        name = names[alias]
        text = re.sub(rf"\b{escaped}\s*:\s*", f"Quanto ao {name}, ", text, flags=re.I)
        text = re.sub(rf"\b(?:o\s+)?equipamento\s+{escaped}\b", f"o {name}", text, flags=re.I)
        text = re.sub(rf"\b{escaped}\b", f"o {name}", text, flags=re.I)
    return text
