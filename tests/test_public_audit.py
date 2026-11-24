import json
from scripts import audit_public

def test_audit_accepts_neutral_sources_and_empty_key(tmp_path, monkeypatch):
    monkeypatch.setattr(audit_public, "ROOT", tmp_path)
    (tmp_path / ".env.example").write_text("OPENAI_API_KEY=\n", encoding="utf-8")
    (tmp_path / "example.py").write_text('message = "Dados sintéticos"\n', encoding="utf-8")
    result = audit_public.audit()
    assert result["files_scanned"] == 2 and not result["findings"]

def test_audit_blocks_credentials_paths_and_binary_artifacts_without_echoing_values(tmp_path, monkeypatch):
    monkeypatch.setattr(audit_public, "ROOT", tmp_path)
    fake_token = "sk-proj-" + "A" * 30
    fake_path = chr(90) + ":/" + "private/demo"
    (tmp_path / "unsafe.md").write_text(fake_token + " " + fake_path, encoding="utf-8")
    (tmp_path / "attachment.docx").write_bytes(b"synthetic")
    result = audit_public.audit()
    assert {v["rule"] for v in result["findings"]} == {"token", "private_path", "unexpected_file"}
    assert fake_token not in json.dumps(result["findings"])

def test_audit_accepts_private_terms_as_ephemeral_parameters(tmp_path, monkeypatch):
    monkeypatch.setattr(audit_public, "ROOT", tmp_path)
    (tmp_path / "example.md").write_text("Empresa confidencial de teste", encoding="utf-8")
    assert audit_public.audit(["Empresa confidencial"])["findings"][0]["rule"] == "denied_term"


def test_invalid_python_is_reported_without_echoing_source(tmp_path, monkeypatch):
    monkeypatch.setattr(audit_public, "ROOT", tmp_path)
    fake_token = "sk-proj-" + "B" * 30
    (tmp_path / "invalid.py").write_text("invalid syntax " + fake_token, encoding="utf-8")
    result = audit_public.audit()
    assert "invalid_python" in {finding["rule"] for finding in result["findings"]}
    assert fake_token not in json.dumps(result["findings"])
