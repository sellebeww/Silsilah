# Copyright (c) 2026 Vassel Goleyu. All rights reserved.
"""Aplikasi FastAPI. Jalankan: uvicorn --factory silsilah.ingest.app:create_app

Body permintaan tidak pernah dilog atau dikembalikan dalam pesan error. Gambar tidak pernah menyentuh disk.
"""

import asyncio
import logging
import math
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Protocol, TypeVar

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from PIL import Image
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile
from starlette.formparsers import MultiPartParser

from silsilah.anonymizer import AnonymizationError, PiiLeakError
from silsilah.anonymizer.ner import default_recognizer

from .auth import InvalidTokenError, TokenVerifier
from .embedding import SentenceTransformerEmbedding
from .ocr import InvalidImageError, OcrEmptyError, OcrError, TesseractOcr, open_image
from .pipeline import (
    DatePrecision,
    IngestPipeline,
    SubmissionRejectedError,
    SubmitResult,
    check_text_length,
    today_wib,
)
from .ratelimit import RateLimiter
from .repository import RepositoryError, SupabaseVariantRepository
from .settings import Settings

MAX_IMAGE_BYTES = 5 * 1024 * 1024
_MULTIPART_OVERHEAD = 64 * 1024
# Starlette menulis upload yang melebihi spool_max_size ke file sementara di disk; dinaikkan di atas batas
# Content-Length yang kita terima, sehingga gambar selalu tinggal di memori.
MultiPartParser.spool_max_size = MAX_IMAGE_BYTES + _MULTIPART_OVERHEAD

log = logging.getLogger("silsilah.ingest")
T = TypeVar("T")


class Ocr(Protocol):
    def extract(self, img: Image.Image) -> str: ...


@dataclass
class Deps:
    pipeline: IngestPipeline
    ocr: Ocr
    verifier: TokenVerifier
    close: Callable[[], None] = field(default=lambda: None)


class SubmissionMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")
    first_seen_date: date
    date_precision: DatePrecision = "day"

    @field_validator("first_seen_date")
    @classmethod
    def _not_future(cls, v: date) -> date:
        if v > today_wib():
            raise ValueError("tanggal pertama kali diterima tidak boleh di masa depan")
        return v


class TextSubmission(SubmissionMeta):
    text: str

    @field_validator("text")
    @classmethod
    def _length(cls, v: str) -> str:
        check_text_length(v)
        return v


def build_deps(settings: Settings) -> Deps:
    """Muat semua model sekali saat startup, bukan saat kiriman pertama."""
    repo = SupabaseVariantRepository(settings.supabase_url, settings.supabase_service_role_key)
    embedder = SentenceTransformerEmbedding(
        settings.embedding_model, settings.embedding_dim, settings.embedding_prefix
    )
    pipeline = IngestPipeline(repo, embedder, default_recognizer())
    verifier = TokenVerifier(settings.supabase_url, settings.supabase_jwt_secret)
    return Deps(pipeline, TesseractOcr(settings.ocr_langs), verifier, close=repo.close)


def _error(status: int, message: str, exc: Exception) -> JSONResponse:
    log.warning("kiriman ditolak status=%d sebab=%s", status, type(exc).__name__)
    return JSONResponse(status_code=status, content={"detail": message})


def create_app(settings: Settings | None = None, deps: Deps | None = None) -> FastAPI:
    settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.deps = deps or build_deps(settings)
        yield
        app.state.deps.close()

    app = FastAPI(title="Silsilah NLP", lifespan=lifespan, docs_url=None, redoc_url=None)
    app.state.limiter = RateLimiter(settings.rate_limit_per_hour)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_methods=["POST"],
        allow_headers=["Authorization", "Content-Type"],
        max_age=600,
    )

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        # Handler bawaan FastAPI menggemakan "input"; di sini hanya lokasi dan pesan.
        errors = [
            {"loc": list(e.get("loc", ())), "msg": e.get("msg"), "type": e.get("type")} for e in exc.errors()
        ]
        log.warning("kiriman ditolak status=422 sebab=validasi")
        return JSONResponse(status_code=422, content={"detail": errors})

    handlers: list[tuple[type[Exception], int, str | None]] = [
        (SubmissionRejectedError, 422, None),
        (PiiLeakError, 422, "Teks tidak dapat dianonimkan dengan aman. Hapus data pribadi lalu kirim ulang."),
        (AnonymizationError, 503, "Layanan anonimisasi sedang tidak tersedia"),
        (InvalidImageError, 415, None),
        (OcrEmptyError, 422, None),
        (OcrError, 503, None),
        (RepositoryError, 503, "Penyimpanan sedang tidak tersedia"),
        (TimeoutError, 503, "Pemrosesan melebihi batas waktu"),
    ]
    for exc_type, status, message in handlers:

        def handler(
            _: Request, exc: Exception, status: int = status, message: str | None = message
        ) -> JSONResponse:
            return _error(status, message or str(exc), exc)

        app.add_exception_handler(exc_type, handler)

    async def rate_limited(request: Request) -> None:
        auth = request.headers.get("authorization")
        if auth:
            scheme, _, token = auth.partition(" ")
            try:
                if scheme.lower() != "bearer" or not token:
                    raise InvalidTokenError("format Authorization salah")
                key = "user:" + request.app.state.deps.verifier.subject(token)
            except InvalidTokenError:
                raise HTTPException(401, "Token tidak valid") from None
        else:
            # Di balik proxy, uvicorn --proxy-headers mengisi client.host dari X-Forwarded-For tepercaya.
            key = "ip:" + (request.client.host if request.client else "unknown")
        retry_after = request.app.state.limiter.hit(key)
        if retry_after is not None:
            raise HTTPException(
                429,
                "Terlalu banyak kiriman, coba lagi nanti",
                headers={"Retry-After": str(math.ceil(retry_after))},
            )

    async def run(fn: Callable[..., T], *args: Any) -> T:
        return await asyncio.wait_for(run_in_threadpool(fn, *args), settings.submit_timeout_s)

    def respond(kind: str, result: SubmitResult, response: Response) -> dict[str, Any]:
        response.status_code = 200 if result.is_duplicate else 201
        log.info(
            "kiriman diterima jenis=%s duplikat=%s entitas=%s",
            kind,
            result.is_duplicate,
            ",".join(f"{e.type}:{e.count}" for e in result.entities_found) or "-",
        )
        return {
            "variant_id": result.variant_id,
            "is_duplicate": result.is_duplicate,
            "report_count": result.report_count,
            "body_anonymized": result.body_anonymized,
            "entities_found": [{"type": e.type, "count": e.count} for e in result.entities_found],
        }

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/submit/text", status_code=201, dependencies=[Depends(rate_limited)])
    async def submit_text(body: TextSubmission, request: Request, response: Response) -> dict[str, Any]:
        pipeline: IngestPipeline = request.app.state.deps.pipeline
        result = await run(pipeline.submit, body.text, body.first_seen_date, body.date_precision)
        return respond("teks", result, response)

    @app.post("/submit/image", status_code=201, dependencies=[Depends(rate_limited)])
    async def submit_image(request: Request, response: Response) -> dict[str, Any]:
        # Ukuran dicek dari header SEBELUM body diurai, agar upload besar tidak pernah dibaca.
        length = request.headers.get("content-length")
        if length is None or not length.isdigit():
            raise HTTPException(411, "Content-Length wajib diisi")
        if int(length) > MAX_IMAGE_BYTES + _MULTIPART_OVERHEAD:
            raise HTTPException(413, "Ukuran gambar maksimal 5 MB")
        if not request.headers.get("content-type", "").startswith("multipart/form-data"):
            raise HTTPException(415, "Gunakan multipart/form-data")
        async with request.form(max_files=1, max_fields=3) as form:
            upload = form.get("image")
            fields = {k: v for k, v in form.items() if k != "image"}
            if not isinstance(upload, UploadFile):
                raise HTTPException(422, "Field 'image' wajib berisi berkas gambar")
            data = await upload.read(MAX_IMAGE_BYTES + 1)
        if len(data) > MAX_IMAGE_BYTES:
            raise HTTPException(413, "Ukuran gambar maksimal 5 MB")
        try:
            meta = SubmissionMeta.model_validate(fields)
        except ValidationError as exc:
            raise RequestValidationError(exc.errors()) from None

        img = open_image(data)
        del data
        ocr: Ocr = request.app.state.deps.ocr
        text = await run(ocr.extract, img)
        del img  # gambar dibuang begitu teks didapat
        pipeline: IngestPipeline = request.app.state.deps.pipeline
        result = await run(pipeline.submit, text, meta.first_seen_date, meta.date_precision)
        return respond("gambar", result, response)

    return app
