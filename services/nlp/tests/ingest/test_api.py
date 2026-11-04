# Copyright (c) 2026 Vassel Goleyu. All rights reserved.
import hashlib
import io
import logging
import os
import tempfile
from datetime import timedelta
from typing import Any

import jwt
import pytest
from PIL import Image

from silsilah.anonymizer import PiiLeakError, normalize_for_hash
from silsilah.ingest.pipeline import today_wib

from .conftest import JWT_SECRET, Env, make_env

RAW = "Pesan berantai dari Bu Rina Kartikasari: transfer ke 0812-3456-7890 sebelum Jumat!"
PHONE_DIGITS = "081234567890"


def payload(text: str = RAW, **kw: Any) -> dict[str, Any]:
    return {"text": text, "first_seen_date": "2026-03-10", "date_precision": "day", **kw}


def png_bytes(size: tuple[int, int] = (200, 80), noise: bool = False) -> bytes:
    img = (
        Image.frombytes("RGB", size, os.urandom(size[0] * size[1] * 3))
        if noise
        else Image.new("RGB", size, "white")
    )
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def post_image(
    env: Env, data: bytes, filename: str = "pesan.png", ctype: str = "image/png", **fields: str
) -> Any:
    form = {"first_seen_date": "2026-03-10", "date_precision": "day", **fields}
    return env.client.post("/submit/image", data=form, files={"image": (filename, data, ctype)})


# --- alur teks ---


def test_text_stored_anonymized_and_pending(env: Env) -> None:
    resp = env.client.post("/submit/text", json=payload())
    assert resp.status_code == 201
    body = resp.json()
    assert body["is_duplicate"] is False and body["report_count"] == 1
    assert "[TELEPON]" in body["body_anonymized"] and "[NAMA]" in body["body_anonymized"]
    assert {e["type"] for e in body["entities_found"]} == {"TELEPON", "NAMA"}
    [(stored_hash, row)] = env.repo.rows.items()
    assert PHONE_DIGITS not in row.body.replace("-", "") and "Kartikasari" not in row.body
    assert stored_hash == hashlib.sha256(normalize_for_hash(row.body).encode()).hexdigest()
    assert len(row.embedding) == 384


def test_exact_duplicate_increments_without_new_row_or_embedding(env: Env) -> None:
    first = env.client.post("/submit/text", json=payload()).json()
    resp = env.client.post("/submit/text", json=payload())
    assert resp.status_code == 200
    assert resp.json() | {"report_count": 0} == first | {"is_duplicate": True, "report_count": 0}
    assert resp.json()["report_count"] == 2
    assert len(env.repo.rows) == 1 and env.embedder.calls == 1


def test_duplicate_ignores_case_spacing_and_punctuation(env: Env) -> None:
    env.client.post("/submit/text", json=payload())
    noisy = "PESAN  berantai dari Bu Rina Kartikasari transfer ke 0812 3456 7890 sebelum jumat"
    resp = env.client.post("/submit/text", json=payload(noisy))
    assert resp.json()["is_duplicate"] is True and len(env.repo.rows) == 1


def test_earlier_first_seen_updates_existing_variant(env: Env) -> None:
    env.client.post("/submit/text", json=payload())
    env.client.post("/submit/text", json=payload(first_seen_date="2026-01-20", date_precision="month"))
    env.client.post("/submit/text", json=payload(first_seen_date="2026-05-01"))
    [row] = env.repo.rows.values()
    assert (str(row.first_seen), row.precision, row.report_count) == ("2026-01-01", "month", 3)


def test_approximate_date_stored_at_start_of_period(env: Env) -> None:
    env.client.post("/submit/text", json=payload(first_seen_date="2025-08-17", date_precision="year"))
    [row] = env.repo.rows.values()
    assert str(row.first_seen) == "2025-01-01"


# --- validasi ---


@pytest.mark.parametrize(
    "override",
    [
        {"text": "terlalu pendek"},
        {"text": "a" * 5001},
        {"first_seen_date": str(today_wib() + timedelta(days=1))},
        {"first_seen_date": "bukan-tanggal"},
        {"date_precision": "minggu"},
        {"kolom_lain": "x"},
    ],
)
def test_validation_rejects_without_echoing_input(env: Env, override: dict[str, Any]) -> None:
    secret = "Kartikasari0812"
    data = payload(**override)
    if "text" in override:
        data["text"] = override["text"] + (secret if len(override["text"]) > 100 else "")
    else:
        data["text"] = RAW + secret
    resp = env.client.post("/submit/text", json=data)
    assert resp.status_code == 422
    assert secret not in resp.text and not env.repo.rows


def test_today_is_accepted(env: Env) -> None:
    assert env.client.post("/submit/text", json=payload(first_seen_date=str(today_wib()))).status_code == 201


def test_pii_leak_rejected_and_nothing_stored(env: Env, monkeypatch: pytest.MonkeyPatch) -> None:
    def leak(text: str) -> None:
        raise PiiLeakError("pola PII masih ada: TELEPON")

    monkeypatch.setattr("silsilah.ingest.pipeline.assert_no_pii", leak)
    resp = env.client.post("/submit/text", json=payload())
    assert resp.status_code == 422 and not env.repo.rows


# --- rate limit ---


def test_rate_limit_per_ip_and_per_contributor() -> None:
    gen = make_env(rate_limit=2)
    env = next(gen)
    texts = [RAW + f" varian {i}" for i in range(4)]
    assert [env.client.post("/submit/text", json=payload(t)).status_code for t in texts[:2]] == [201, 201]
    limited = env.client.post("/submit/text", json=payload(texts[2]))
    assert limited.status_code == 429 and int(limited.headers["Retry-After"]) > 0
    token = jwt.encode({"sub": "kontributor-1", "aud": "authenticated"}, JWT_SECRET, algorithm="HS256")
    authed = env.client.post(
        "/submit/text", json=payload(texts[3]), headers={"Authorization": f"Bearer {token}"}
    )
    assert authed.status_code == 201
    gen.close()


def test_invalid_token_rejected(env: Env) -> None:
    bad = jwt.encode(
        {"sub": "x", "aud": "authenticated"}, "kunci-lain-yang-juga-cukup-panjang!", algorithm="HS256"
    )
    resp = env.client.post("/submit/text", json=payload(), headers={"Authorization": f"Bearer {bad}"})
    assert resp.status_code == 401 and not env.repo.rows


def test_cors_only_allowed_origin(env: Env) -> None:
    headers = {"Access-Control-Request-Method": "POST"}
    ok = env.client.options("/submit/text", headers={**headers, "Origin": "http://localhost:3000"})
    bad = env.client.options("/submit/text", headers={**headers, "Origin": "https://jahat.example"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert "access-control-allow-origin" not in bad.headers


def test_oversized_text_body_rejected_before_parsing_with_cors(env: Env) -> None:
    big = {"text": "x" * 70_000, "first_seen_date": "2026-03-10"}
    resp = env.client.post("/submit/text", json=big, headers={"Origin": "http://localhost:3000"})
    assert resp.status_code == 413 and not env.repo.rows
    assert resp.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert "xxxx" not in resp.text


def test_text_without_content_length_rejected(env: Env) -> None:
    def chunks() -> Any:
        yield b"{}"

    resp = env.client.post("/submit/text", content=chunks(), headers={"Content-Type": "application/json"})
    assert resp.status_code == 411 and not env.repo.rows


def test_api_responses_carry_security_headers(env: Env) -> None:
    h = env.client.get("/health").headers
    assert h["x-content-type-options"] == "nosniff" and h["cache-control"] == "no-store"
    assert "frame-ancestors 'none'" in h["content-security-policy"]


# --- alur gambar ---


def test_image_ocr_then_anonymized(env: Env) -> None:
    env.ocr.text = RAW
    resp = post_image(env, png_bytes((300, 100)))
    assert resp.status_code == 201 and "[TELEPON]" in resp.json()["body_anonymized"]
    assert env.ocr.sizes == [(300, 100)]


@pytest.mark.parametrize(
    ("data", "filename", "ctype"),
    [
        (b"bukan gambar sama sekali, hanya teks", "pesan.png", "image/png"),
        (b"%PDF-1.7 palsu", "pesan.jpg", "image/jpeg"),
        (b"GIF89a" + b"\x00" * 50, "pesan.webp", "image/webp"),
    ],
)
def test_image_content_checked_not_extension(env: Env, data: bytes, filename: str, ctype: str) -> None:
    resp = post_image(env, data, filename, ctype)
    assert resp.status_code == 415 and not env.repo.rows


def test_gif_rejected_even_if_valid(env: Env) -> None:
    buf = io.BytesIO()
    Image.new("RGB", (50, 50)).save(buf, format="GIF")
    assert post_image(env, buf.getvalue(), "a.gif", "image/gif").status_code == 415


def test_image_over_5mb_rejected_before_parsing(env: Env) -> None:
    resp = post_image(env, b"\x89PNG" + b"\x00" * (5 * 1024 * 1024 + 70_000))
    assert resp.status_code == 413 and env.ocr.sizes == []


@pytest.mark.parametrize(("ocr_text", "status"), [("", 422), ("hanya pendek", 422)])
def test_ocr_empty_or_short_gives_clear_error(env: Env, ocr_text: str, status: int) -> None:
    if ocr_text:
        env.ocr.text = ocr_text
    else:
        from silsilah.ingest.ocr import OcrEmptyError

        def empty(img: Image.Image) -> str:
            raise OcrEmptyError("Tidak ada teks yang terbaca dari gambar")

        env.ocr.extract = empty  # type: ignore[method-assign]
    resp = post_image(env, png_bytes())
    assert resp.status_code == status and resp.json()["detail"]


def test_image_requires_valid_date(env: Env) -> None:
    env.ocr.text = RAW
    resp = post_image(env, png_bytes(), first_seen_date=str(today_wib() + timedelta(days=3)))
    assert resp.status_code == 422 and not env.repo.rows


# --- tidak ada teks mentah / gambar di disk atau log ---


def test_disk_recorder_detects_writes(disk_writes: list[str]) -> None:
    with tempfile.TemporaryFile() as f:
        f.write(b"x")
    assert disk_writes, "perekam harus menangkap penulisan file sementara"


def test_no_raw_text_or_image_on_disk_or_in_logs(
    env: Env, disk_writes: list[str], caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    env.ocr.text = RAW
    # >1 MB dan tak termampatkan: tanpa pengaturan spool, Starlette akan menulisnya ke file sementara.
    big = png_bytes((1100, 1100), noise=True)
    assert 1024 * 1024 < len(big) < 5 * 1024 * 1024
    assert post_image(env, big).status_code == 201
    assert env.client.post("/submit/text", json=payload(RAW + " lagi")).status_code == 201
    assert env.client.post("/submit/text", json=payload("pendek")).status_code == 422
    assert disk_writes == []
    for secret in ("Kartikasari", "0812-3456-7890", "Pesan berantai"):
        assert secret not in caplog.text
    assert "kiriman diterima" in caplog.text
