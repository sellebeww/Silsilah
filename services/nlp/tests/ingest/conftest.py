# Copyright (c) 2026 Vassel Goleyu. All rights reserved.
"""Fixture ingest: DB dan model diganti tiruan; perekam penulisan disk lewat audit hook Python."""

import os
import sys
from collections.abc import Generator, Iterator, Sequence
from dataclasses import dataclass
from datetime import date
from typing import Any

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from silsilah.ingest.app import Deps, create_app
from silsilah.ingest.auth import TokenVerifier
from silsilah.ingest.pipeline import IngestPipeline
from silsilah.ingest.repository import StoredVariant
from silsilah.ingest.settings import Settings

JWT_SECRET = "rahasia-uji-yang-cukup-panjang-32b"

# Audit hook tidak bisa dilepas, jadi satu hook global yang hanya merekam saat _recording tidak None.
_recording: list[str] | None = None
_WRITE_FLAGS = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND


def _audit(event: str, args: tuple[Any, ...]) -> None:
    if _recording is None:
        return
    if event == "open":
        path, mode, flags = args
        writes = (isinstance(mode, str) and any(c in mode for c in "wax+")) or (
            isinstance(flags, int) and flags & _WRITE_FLAGS
        )
        if writes:
            _recording.append(f"open {path}")
    elif event in ("tempfile.mkstemp", "tempfile.mkdtemp", "shutil.copyfile", "os.rename"):
        _recording.append(f"{event} {args[0]}")


sys.addaudithook(_audit)


@pytest.fixture
def disk_writes() -> Iterator[list[str]]:
    """Daftar penulisan ke disk selama tes; tes memeriksa bahwa daftar ini kosong."""
    global _recording
    _recording = []
    try:
        yield _recording
    finally:
        _recording = None


def no_ner(text: str) -> list[tuple[int, int]]:
    return []


@dataclass
class Row:
    id: str
    body: str
    embedding: list[float]
    first_seen: date
    precision: str
    report_count: int = 1


class FakeRepo:
    """Meniru semantik fungsi SQL register_duplicate_report / insert_pending_variant."""

    def __init__(self) -> None:
        self.rows: dict[str, Row] = {}

    def register_duplicate(self, body_hash: str, first_seen: date, precision: str) -> StoredVariant | None:
        row = self.rows.get(body_hash)
        if row is None:
            return None
        row.report_count += 1
        if first_seen < row.first_seen:
            row.first_seen, row.precision = first_seen, precision
        return StoredVariant(row.id, row.report_count, True)

    def insert_pending(
        self, body: str, body_hash: str, embedding: list[float], first_seen: date, precision: str
    ) -> StoredVariant:
        row = Row(f"v{len(self.rows) + 1}", body, embedding, first_seen, precision)
        self.rows[body_hash] = row
        return StoredVariant(row.id, 1, False)


class FakeEmbedder:
    dim = 384

    def __init__(self) -> None:
        self.calls = 0

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        self.calls += 1
        return [[0.0] * 383 + [1.0] for _ in texts]


class FakeOcr:
    def __init__(self, text: str = "") -> None:
        self.text = text
        self.sizes: list[tuple[int, int]] = []

    def extract(self, img: Image.Image) -> str:
        self.sizes.append(img.size)
        return self.text


@dataclass
class Env:
    client: TestClient
    repo: FakeRepo
    embedder: FakeEmbedder
    ocr: FakeOcr


def make_env(rate_limit: int = 100, client_host: str = "203.0.113.7") -> Generator[Env]:
    repo, embedder, ocr = FakeRepo(), FakeEmbedder(), FakeOcr()
    settings = Settings("http://supabase.invalid", "kunci-uji", JWT_SECRET, rate_limit_per_hour=rate_limit)
    deps = Deps(IngestPipeline(repo, embedder, no_ner), ocr, TokenVerifier(None, JWT_SECRET))
    with TestClient(create_app(settings, deps), client=(client_host, 50000)) as client:
        yield Env(client, repo, embedder, ocr)


@pytest.fixture
def env() -> Iterator[Env]:
    yield from make_env()
