"""Barreira local por lista permitida; não substitui conferência do texto livre."""
import json
import re
import unicodedata
from .domain import Case, normalize


def assert_deidentified(case: Case, payload: dict):
    raw = json.dumps(payload, ensure_ascii=False)
    def values(value):
        if isinstance(value, str):
            return [value]
        if isinstance(value, dict):
            return [s for k, v in value.items() if k != "alias" for s in values(v)]
        if isinstance(value, list):
            return [s for v in value for s in values(v)]
        return []
    technical_text = " ".join(values(payload))
    def words(text):
        plain = unicodedata.normalize("NFKD", text.casefold())
        plain = "".join(char for char in plain if not unicodedata.combining(char))
        return re.findall(r"[a-z0-9]+", plain)

    technical_words = words(technical_text)
    folded = " ".join(technical_words)
    def compact_match(token):
        for start in range(len(technical_words)):
            joined = ""
            for end in range(start, len(technical_words)):
                joined += technical_words[end]
                if joined == token:
                    return True
                if len(joined) >= len(token):
                    break
        return False
    forbidden = [case.requester, case.department, case.responsible]
    forbidden += [part for part in re.findall(r"[\wÀ-ÿ]{4,}", case.requester)
                  if normalize(part) not in {"solicitante", "cliente", "teste", "exemplo"}]
    # O nome completo e o primeiro nome continuam protegidos. Um sobrenome isolado
    # pode ser uma palavra comum, como 'claro', sem identificar o responsável.
    titles = {"eng", "profissional", "responsavel", "tecnico", "tecnica", "prof", "exemplo", "de", "demonstracao"}
    personal_name = [part for part in words(case.responsible) if part not in titles]
    if personal_name:
        forbidden.append(" ".join(personal_name))
        if len(personal_name[0]) >= 4:
            forbidden.append(personal_name[0])
    for identity in case.identities:
        forbidden.extend([identity.serial, identity.model])
    for value in forbidden:
        token = normalize(value)
        phrase = " ".join(words(value))
        # Respeita limites de palavras: um modelo curto não deve coincidir com
        # letras no meio de termos técnicos. Tolera separadores dentro de códigos.
        phrase_match = phrase and f" {phrase} " in f" {folded} "
        code_match = compact_match(token) if token else False
        if token and token not in {"naoinformado", "naoseaplica"} and (phrase_match or code_match):
            raise ValueError("A descrição contém identificação cadastrada. Retire nomes, modelos e séries antes de enviar.")
    patterns = [r"[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}",
                r"\b\d{3}[. ]?\d{3}[. ]?\d{3}[- ]?\d{2}\b",
                r"(?:\+55\s*)?\(?\d{2}\)?[\s-]*9?\d{4}[\s-]*\d{4}\b",
                r"(?i)\b(?:solicitante|nome|série|serial|cpf|cliente)\s*[:#]\s*\S+"]
    if any(re.search(pattern, raw) for pattern in patterns):
        raise ValueError("Foi encontrado um possível identificador no texto técnico. Revise a prévia antes de enviar.")
    return payload
