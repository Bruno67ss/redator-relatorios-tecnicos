"""Auditoria das fontes destinadas à distribuição; não imprime segredos."""
from pathlib import Path
import ast
import hashlib
import json
import os
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
IGNORED = {'.venv', 'venv', 'local', '.pytest_cache', '__pycache__', '.git'}
ALLOWED_SUFFIXES = {'.py', '.md', '.txt', '.toml', '.json'}
PATTERNS = {
    'private_path': re.compile(r'(?i)(?<![a-z0-9])(?:[a-z]:[\\/]|/home/|/Users/|\\\\[a-z0-9_.-]+\\)'),
    'private_key': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    'token': re.compile(r'(?:sk-(?:proj-)?[a-zA-Z0-9_-]{20,}|gh[pousr]_[a-zA-Z0-9]{20,}|AKIA[A-Z0-9]{16})'),
    'internal_address': re.compile(r'(?<!\d)(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})(?!\d)'),
    'unexpected_contact': re.compile(r'[\w.+-]+@(?!(?:example\.(?:com|org|net))\b)[\w.-]+\.[a-zA-Z]{2,}'),
}

def audit(denied_terms=()):
    findings, hashes = [], {}
    patterns = dict(PATTERNS)
    if denied_terms:
        patterns['denied_term'] = re.compile('|'.join(re.escape(v) for v in denied_terms), re.I)
    for directory, dirs, names in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in IGNORED]
        for filename in sorted(names):
            path = Path(directory) / filename
            relative = path.relative_to(ROOT)
            name = relative.as_posix()
            if path.is_symlink():
                findings.append({'file': name, 'rule': 'symlink'})
                continue
            if path.name not in {'.env.example', '.gitignore'} and path.suffix not in ALLOWED_SUFFIXES:
                findings.append({'file': name, 'rule': 'unexpected_file'})
                continue
            if path.name.startswith('.env') and path.name != '.env.example':
                findings.append({'file': name, 'rule': 'filled_environment'})
                continue
            try:
                content = path.read_text(encoding='utf-8-sig')
            except (UnicodeError, OSError):
                findings.append({'file': name, 'rule': 'unreadable_text'})
                continue
            if path.suffix == '.py':
                try:
                    ast.parse(content, filename=name)
                except SyntaxError:
                    findings.append({'file': name, 'rule': 'invalid_python'})
            if name == '.env.example' and not re.search(r'^OPENAI_API_KEY=\s*$', content, re.M):
                findings.append({'file': name, 'rule': 'nonempty_api_key'})
            # O próprio scanner contém expressões de caminhos e credenciais.
            for rule, pattern in patterns.items():
                if rule == 'private_path' and path.resolve() == Path(__file__).resolve():
                    continue
                if pattern.search(content) or pattern.search(name):
                    findings.append({'file': name, 'rule': rule})
            hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return {'files_scanned': len(hashes), 'findings': findings, 'sha256': hashes}

if __name__ == '__main__':
    # Argumentos opcionais permitem buscar termos privados sem gravá-los nas fontes.
    result = audit(sys.argv[1:])
    print(json.dumps({'files_scanned': result['files_scanned'], 'findings': result['findings']}, ensure_ascii=False, indent=2))
    sys.exit(bool(result['findings']))
