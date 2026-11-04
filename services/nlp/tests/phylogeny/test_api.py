# Copyright (c) 2026 Vassel Goleyu. All rights reserved.
import json
import uuid
from collections.abc import Iterator

import httpx
import jwt
import pytest
from fastapi.testclient import TestClient

from silsilah.ingest.app import Deps, create_app
from silsilah.ingest.auth import TokenVerifier
from silsilah.ingest.pipeline import IngestPipeline
from silsilah.ingest.settings import Settings
from silsilah.phylogeny.memory import InMemoryPhylogenyRepository
from silsilah.phylogeny.placement import PlacementService
from silsilah.phylogeny.repository import SupabasePhylogenyRepository

from ..ingest.conftest import JWT_SECRET, FakeEmbedder, FakeOcr, FakeRepo, no_ner
from .helpers import node, unit

VARIANT = str(uuid.UUID(int=1))


def token(sub: str) -> dict[str, str]:
    signed = jwt.encode({"sub": sub, "aud": "authenticated"}, JWT_SECRET, algorithm="HS256")
    return {"Authorization": f"Bearer {signed}"}


@pytest.fixture
def client() -> Iterator[TestClient]:
    repo = InMemoryPhylogenyRepository()
    repo.roles = {"kurator-1": "curator", "kontributor-1": "contributor"}
    repo.add(node(VARIANT, "2026-03-01", unit(1, 0), precision="month", reports=4))
    deps = Deps(
        IngestPipeline(FakeRepo(), FakeEmbedder(), no_ner),
        FakeOcr(),
        TokenVerifier(None, JWT_SECRET),
        PlacementService(repo, 0.6, 0.85),
    )
    with TestClient(create_app(Settings("http://x", "k", JWT_SECRET), deps)) as c:
        yield c


def test_approve_requires_curator(client: TestClient) -> None:
    url = f"/moderation/variants/{VARIANT}/approve"
    assert client.post(url).status_code == 401
    assert client.post(url, headers=token("kontributor-1")).status_code == 403
    assert client.post(url, headers=token("tidak-terdaftar")).status_code == 403


def test_curator_approval_places_and_reports_uncertainty(client: TestClient) -> None:
    resp = client.post(f"/moderation/variants/{VARIANT}/approve", headers=token("kurator-1"))
    assert resp.status_code == 200
    body = resp.json()
    assert body["new_family"] is True and body["parent_id"] is None
    assert body["oldest_reported"] == {
        "variant_id": VARIANT,
        "first_seen_reported_at": "2026-03-01",
        "date_precision": "month",
        "report_count": 4,
    }


def test_unknown_variant_is_conflict(client: TestClient) -> None:
    resp = client.post(f"/moderation/variants/{uuid.UUID(int=9)}/approve", headers=token("kurator-1"))
    assert resp.status_code == 409


def test_supabase_repository_parses_vector_and_sends_plan() -> None:
    sent: list[httpx.Request] = []
    row = {
        "id": "v1",
        "family_id": None,
        "moderation_status": "pending",
        "body_anonymized": "teks",
        "embedding": "[0.6,0.8]",
        "first_seen_reported_at": "2026-02-01",
        "date_precision": "month",
        "submitted_at": "2026-02-03",
        "report_count": 2,
    }

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        if request.url.path.endswith("/variants"):
            return httpx.Response(200, json=[row])
        if request.url.path.endswith("match_variants"):
            return httpx.Response(200, json=[])
        return httpx.Response(204)

    repo = SupabasePhylogenyRepository(
        "http://db", "sb_secret_x", httpx.Client(transport=httpx.MockTransport(handler))
    )
    record = repo.get_variant("v1")
    assert record is not None and record.node is not None and record.node.embedding == (0.6, 0.8)
    plan = PlacementService(repo, 0.6, 0.85, new_id=lambda: "F1").place("v1")
    payload = json.loads(sent[-1].content)["p_plan"]
    assert sent[-1].url.path == "/rest/v1/rpc/apply_family_plan"
    assert "oldest" not in payload and payload["family_id"] == "F1" == plan.family_id
