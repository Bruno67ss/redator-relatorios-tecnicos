"""Avisos locais de conferência; nunca alteram o diagnóstico ou a transcrição."""
import re


def terminology_notes(text: str) -> tuple[str, ...]:
    for match in re.finditer(r"\bdestru[ií]d[oa]s?\b", text, flags=re.I):
        before = text[max(0, match.start() - 30):match.start()]
        if re.search(r"\bnão\s+(?:est[aá][a-z]*\s+|foi\s+|foram\s+|fic[a-z]*\s+)?$", before, flags=re.I):
            continue
        return ("Confira o termo ‘destruído’: ele indica dano físico severo e pode ter sido confundido na transcrição com ‘obstruído’. Confirme a condição e corrija o texto, se necessário. Nenhuma substituição foi feita automaticamente.",)
    return ()
