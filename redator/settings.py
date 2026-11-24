"""Padrões neutros; configurações particulares ficam fora do versionamento."""
import json
from pathlib import Path

DEFAULT_CITY = "Cidade Exemplo"
DEFAULT_MODEL = "gpt-6-luna"
DEFAULT_RESPONSIBLE = "Responsável Exemplo"
DEFAULT_CLOSING = "Qualquer dúvida em relação ao exposto, por favor, entre em contato."


def load_profile(root: Path) -> dict:
    path = root / "local" / "profile.json"
    profile = {"city": DEFAULT_CITY, "responsible": DEFAULT_RESPONSIBLE,
               "role": "", "closing": DEFAULT_CLOSING, "template_path": "", "department_prefix": ""}
    if path.exists():
        values = json.loads(path.read_text(encoding="utf-8-sig"))
        for key in profile:
            if isinstance(values.get(key), str) and values[key].strip():
                profile[key] = values[key].strip()
    return profile
