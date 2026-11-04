# Copyright (c) 2026 Vassel Goleyu. All rights reserved.
import json
import math
import shutil
from datetime import date

import httpx
import pytest
from PIL import Image, ImageDraw, ImageFont

from silsilah.ingest.ocr import InvalidImageError, OcrError, TesseractOcr, open_image, preprocess
from silsilah.ingest.ratelimit import RateLimiter
from silsilah.ingest.repository import RepositoryError, SupabaseVariantRepository


def test_rate_limiter_window_resets_and_rotates_salt() -> None:
    now = [0.0]
    limiter = RateLimiter(limit=2, window_s=60, clock=lambda: now[0])
    assert [limiter.hit("ip:1.2.3.4") for _ in range(2)] == [None, None]
    assert limiter.hit("ip:1.2.3.4") == pytest.approx(60)
    assert limiter.hit("ip:5.6.7.8") is None
    first_digests = set(limiter._counts)
    now[0] = 61
    assert limiter.hit("ip:1.2.3.4") is None
    assert first_digests.isdisjoint(limiter._counts), "garam baru: hash tidak bisa dikaitkan antar jendela"
    assert all(b"1.2.3.4" not in k for k in limiter._counts)


def test_preprocess_grayscale_and_resize() -> None:
    small = preprocess(Image.new("RGB", (300, 100)))
    big = preprocess(Image.new("RGB", (6000, 2000)))
    assert small.mode == big.mode == "L"
    assert max(small.size) == 1200 and max(big.size) == 3000


def test_open_image_rejects_decompression_bomb() -> None:
    import io

    buf = io.BytesIO()
    Image.new("1", (9000, 9000)).save(buf, format="PNG")  # kecil di disk, 81 juta piksel di memori
    with pytest.raises(InvalidImageError):
        open_image(buf.getvalue())


def test_ocr_missing_binary_is_clear_error() -> None:
    with pytest.raises(OcrError, match="tidak terpasang"):
        TesseractOcr(binary="/tidak/ada/tesseract").extract(Image.new("RGB", (50, 50), "white"))


@pytest.mark.skipif(
    shutil.which("tesseract") is None, reason="Tesseract tidak terpasang (diuji di image Docker)"
)
def test_tesseract_reads_text_in_memory() -> None:
    img = Image.new("RGB", (900, 120), "white")
    ImageDraw.Draw(img).text(
        (20, 30), "Bantuan tunai untuk warga", fill="black", font=ImageFont.load_default(48)
    )
    assert "Bantuan" in TesseractOcr().extract(img)


def test_repository_calls_rpc_and_hides_error_body() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if request.url.path.endswith("register_duplicate_report"):
            return httpx.Response(200, json=[])
        if json.loads(request.content)["p_body"] == "gagal":
            return httpx.Response(400, json={"details": "Failing row contains (teks rahasia)"})
        return httpx.Response(200, json=[{"id": "u1", "report_count": 1, "is_duplicate": False}])

    repo = SupabaseVariantRepository(
        "http://db", "sb_secret_x", httpx.Client(transport=httpx.MockTransport(handler))
    )
    assert repo.register_duplicate("h" * 64, date(2026, 3, 1), "month") is None
    stored = repo.insert_pending("teks [NAMA]", "h" * 64, [0.5] * 384, date(2026, 3, 1), "month")
    assert (stored.id, stored.is_duplicate) == ("u1", False)
    assert calls[1].url.path == "/rest/v1/rpc/insert_pending_variant"
    assert calls[1].headers["apikey"] == "sb_secret_x" and "authorization" not in calls[1].headers
    sent = json.loads(calls[1].content)
    assert sent["p_first_seen"] == "2026-03-01" and len(sent["p_embedding"]) == 384
    with pytest.raises(RepositoryError) as exc:
        repo.insert_pending("gagal", "h" * 64, [0.5] * 384, date(2026, 3, 1), "day")
    assert "rahasia" not in str(exc.value)


def test_local_embedding_dimension_and_l2_norm() -> None:
    from silsilah.ingest.embedding import SentenceTransformerEmbedding
    from silsilah.ingest.settings import Settings

    model = Settings.embedding_model
    emb = SentenceTransformerEmbedding(model, 384)
    vecs = emb.embed(["Bantuan tunai Rp 500.000", "Bantuan tunai Rp 1.000.000", "Resep rendang empuk"])
    assert len(vecs) == 3 and all(len(v) == 384 for v in vecs)
    assert all(math.isclose(sum(x * x for x in v), 1.0, rel_tol=1e-4) for v in vecs)
    dot = [sum(a * b for a, b in zip(vecs[0], v, strict=True)) for v in vecs[1:]]
    assert dot[0] > dot[1], "varian bantuan harus lebih mirip satu sama lain daripada resep"
    with pytest.raises(ValueError, match="EMBEDDING_DIM"):
        SentenceTransformerEmbedding(model, 768)
