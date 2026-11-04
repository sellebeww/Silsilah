# Copyright (c) 2026 Vassel Goleyu. All rights reserved.
"""Cek higiene repo untuk CI (hanya stdlib). Gagal bila:
1. berkas .env (selain .env.example) ter-commit, atau pola secret muncul di berkas ter-commit;
2. kode layanan NLP memanggil print() atau logging dengan variabel yang berisi teks/gambar pesan;
3. modul anonimisasi mengimpor logging;
4. kode web memanggil console.* dengan data pesan.
Jalankan: python3 scripts/check_hygiene.py   (uji diri sendiri: --selftest)
"""

import ast
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Nama variabel yang membawa isi pesan (mentah maupun tersamar), gambar, atau body request.
BANNED_NAMES = {"text", "body", "raw", "content", "payload", "message", "ocr_text", "data", "image", "img", "form", "body_anonymized", "anonymized"}
LOG_METHODS = {"debug", "info", "warning", "warn", "error", "exception", "critical", "log"}
SECRET_PATTERNS = {
    "JWT": re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
    "kunci Supabase baru": re.compile(r"sb_(secret|publishable)_[A-Za-z0-9_-]{16,}"),
    "kunci privat": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "AWS access key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "nilai kunci di env": re.compile(r"^(SUPABASE_SERVICE_ROLE_KEY|SUPABASE_JWT_SECRET|NEXT_PUBLIC_SUPABASE_ANON_KEY)=\S+", re.M),
}


def tracked() -> list[Path]:
    out = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True).stdout
    return [q for p in out.decode().split("\0") if p and (q := ROOT / p).is_file()]  # berkas terhapus belum di-commit dilewati


def check_log_source(src: str, name: str = "<src>") -> list[str]:
    """Temukan print() dan panggilan logger yang menyertakan variabel terlarang (juga di dalam f-string)."""
    problems = []
    for node in ast.walk(ast.parse(src)):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        is_print = isinstance(f, ast.Name) and f.id == "print"
        is_log = isinstance(f, ast.Attribute) and f.attr in LOG_METHODS and isinstance(f.value, ast.Name) and f.value.id in {"log", "logger", "logging"}
        if is_print:
            problems.append(f"{name}:{node.lineno}: print() dilarang di kode layanan")
        elif is_log:
            used = {n.id for a in [*node.args, *(k.value for k in node.keywords)] for n in ast.walk(a) if isinstance(n, ast.Name)}
            used |= {n.attr for a in node.args for n in ast.walk(a) if isinstance(n, ast.Attribute)}
            if hit := used & BANNED_NAMES:
                problems.append(f"{name}:{node.lineno}: log memuat {sorted(hit)}; log hanya boleh berisi ID, hash, durasi, kode error")
    return problems


def check_secrets(files: list[Path]) -> list[str]:
    problems = []
    for p in files:
        rel = p.relative_to(ROOT)
        if re.search(r"(^|/)\.env(\.|$)", str(rel)) and rel.name != ".env.example":
            problems.append(f"{rel}: berkas env ter-commit")
            continue
        if p.suffix in {".png", ".jpg", ".webp", ".lock"} or p.name == "package-lock.json" or rel == Path("scripts/check_hygiene.py"):
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for label, pat in SECRET_PATTERNS.items():
            if pat.search(text):
                problems.append(f"{rel}: tampak seperti {label}")
    return problems


def check_web_console(files: list[Path]) -> list[str]:
    pat = re.compile(r"console\.\w+\(.*\b(text|body|payload|content|raw|variant|anonymized)\b")
    problems = []
    for p in files:
        rel = p.relative_to(ROOT)
        if rel.parts[:3] == ("apps", "web", "src") and p.suffix in {".ts", ".tsx"} and ".test." not in p.name:
            for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
                if pat.search(line):
                    problems.append(f"{rel}:{i}: console.* memuat data pesan")
    return problems


def run() -> list[str]:
    files = tracked()
    problems = check_secrets(files) + check_web_console(files)
    for p in files:
        rel = p.relative_to(ROOT)
        if rel.parts[:4] == ("services", "nlp", "src", "silsilah") and p.suffix == ".py":
            src = p.read_text(encoding="utf-8")
            problems += check_log_source(src, str(rel))
            if "anonymizer" in rel.parts and re.search(r"^\s*(import logging|from logging)", src, re.M):
                problems.append(f"{rel}: modul anonimisasi tidak boleh memakai logging")
    return problems


def selftest() -> None:
    assert check_log_source("log.info('x %s', text)")
    assert check_log_source("log.warning(f'gagal {result.body_anonymized}')")
    assert check_log_source("print(1)")
    assert not check_log_source("log.info('ok %s %d', variant_id, count)")
    assert re.search(SECRET_PATTERNS["JWT"], "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.abcdefghijk")
    print("selftest ok")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
        sys.exit(0)
    found = run()
    print("\n".join(found) or "higiene ok")
    sys.exit(1 if found else 0)
