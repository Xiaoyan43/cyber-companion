#!/usr/bin/env python
"""P0-OSS-2 manual dev script — canonical SQLite memory vs Hindsight candidate A/B.

NOT run in CI. Two modes:

  Dry run (default, free, no network):
      python backend/scripts/memory_backend_ab.py
      Runs only the canonical engine (real `MemoryStore` + `retrieval.rank_memories`)
      against the fixed fixtures in `memory_backend_fixtures.py`. Hindsight side is
      printed as "skipped" — this mode exists to validate fixture/scoring logic
      without spending anything.

  Live run (real Hindsight, billed, needs a server + key):
      python backend/scripts/memory_backend_ab.py --live
      Connects to a self-hosted Hindsight server at --base-url (default
      http://localhost:8888 — see `docker run ghcr.io/vectorize-io/hindsight:latest`
      per hindsight.vectorize.io self-host docs; this script does not start one),
      retains the same fixture facts into a per-fixture bank, recalls with the same
      queries, and prints both sides side-by-side. Requires `pip install
      hindsight-client` (the real PyPI package is `hindsight-client`, NOT the
      unrelated abandoned package literally named `hindsight` — confirmed by
      unzipping both wheels, not just trusting the name). Not a repo dependency —
      intentionally not pinned in requirements until P1 verdict.

      The LLM key (e.g. DeepSeek via HINDSIGHT_API_LLM_PROVIDER=openai +
      HINDSIGHT_API_LLM_BASE_URL=https://api.deepseek.com/v1) is configured on the
      *server* (docker run -e ...), not in this script — Hindsight does its own
      fact-extraction LLM calls server-side.

Verified against the real `hindsight-client` 0.8.3 SDK source (unzipped the wheel,
read `hindsight_client/hindsight_client.py` directly — not guessed from docs):
  - `Hindsight.retain(bank_id, content, context=None, tags=None, ...)` returns a
    Pydantic `RetainResponse` (`.operation_id`, not dict `.get()`).
  - `Hindsight.recall(bank_id, query, ...)` has NO `limit` param (only `budget`:
    low/mid/high controls result volume) and returns `RecallResponse.results`
    (list of Pydantic `RecallResult`, fields `.id`/`.text`/`.type`/`.tags`).
  - There is NO per-memory-id delete in the SDK — only whole-bank
    `clear_bank_memories`. `HindsightCandidateBackend.delete()` is wired to raise
    `UnsupportedCandidateCapability`, matching this.
  - `_LiveClientAdapter` below bridges the real Pydantic-returning SDK to the
    plain-dict `HindsightClientProtocol` that `HindsightCandidateBackend` expects.

⚠️ Still unverified (will only surface on a real --live run):
  - RAM is sampled via this process's `ru_maxrss`. Hindsight server runs out of
    process (separate `docker run`), so this under-reports — cross-check with
    `docker stats` during the first --live run.

Usage:
    python backend/scripts/memory_backend_ab.py [--live] [--category 单跳] [--base-url http://localhost:8888]
"""

from __future__ import annotations

import argparse
import resource
import sys
import time
from dataclasses import dataclass
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def _load_dotenv() -> None:
    import os

    env_path = _REPO_ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = value.strip().strip('"').strip("'")


_load_dotenv()

from backend.app.memory.adapters.hindsight_candidate import (  # noqa: E402
    HindsightCandidateBackend,
)
from backend.app.memory.adapters.contract import CandidateMemoryDTO  # noqa: E402
from backend.app.memory.retrieval import rank_memories, tokenize  # noqa: E402
from backend.app.memory.store import MemoryStore  # noqa: E402
from backend.scripts.memory_backend_fixtures import (  # noqa: E402
    FIXTURES,
    MemoryFixture,
)

_OUTPUT_DIR = _REPO_ROOT / "data" / "memory_backend_ab"


@dataclass
class QueryResult:
    backend: str
    query: str
    top_content: str | None
    hit: bool
    latency_s: float


def _run_canonical(fixture: MemoryFixture, db_path: Path) -> list[QueryResult]:
    store = MemoryStore(db_path=db_path)
    for fact in fixture.facts:
        store.create_memory(
            type=fact.type,
            content=fact.content,
            importance=fact.importance,
            confidence=fact.confidence,
            tags=list(fact.tags),
        )
    results: list[QueryResult] = []
    for query in fixture.queries:
        t0 = time.perf_counter()
        ranked = rank_memories(store.list_memories(limit=200), query.query)
        elapsed = time.perf_counter() - t0
        top = ranked[0] if ranked else None
        hit = bool(top) and any(kw in top.content for kw in query.expected_keywords)
        results.append(
            QueryResult(
                backend="canonical",
                query=query.query,
                top_content=top.content if top else None,
                hit=hit,
                latency_s=elapsed,
            )
        )
    return results


class _LiveClientAdapter:
    """Bridges the real `hindsight-client` SDK (Pydantic responses) to the
    plain-dict `HindsightClientProtocol` that `HindsightCandidateBackend` expects.
    """

    def __init__(self, client: object, *, recall_budget: str = "mid") -> None:
        self._client = client
        self._recall_budget = recall_budget

    def retain(self, *, bank_id, content, context=None, tags=None):
        response = self._client.retain(bank_id=bank_id, content=content, context=context, tags=tags or None)
        return response.model_dump()

    def recall(self, *, bank_id, query, limit=10):
        response = self._client.recall(bank_id=bank_id, query=query, budget=self._recall_budget)
        results = [item.model_dump() for item in (response.results or [])][:limit]
        return {"results": results}

    def list_memories(self, *, bank_id, limit=100, offset=0):
        response = self._client.list_memories(bank_id=bank_id, limit=limit, offset=offset)
        return {"items": list(response.items or [])}


def _run_hindsight_live(fixture: MemoryFixture, base_url: str) -> list[QueryResult]:
    try:
        from hindsight_client import Hindsight
    except ImportError:
        print(
            "  [hindsight] hindsight-client not installed — run `pip install hindsight-client` first, skipping.",
            file=sys.stderr,
        )
        return []

    bank_id = f"boxi-eval-{fixture.id}"
    results: list[QueryResult] = []
    rss_before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

    real_client = Hindsight(base_url=base_url)
    try:
        candidate = HindsightCandidateBackend(_LiveClientAdapter(real_client), bank_id=bank_id)

        for fact in fixture.facts:
            candidate.write(
                CandidateMemoryDTO(
                    type=fact.type,
                    content=fact.content,
                    tags=fact.tags,
                    importance=fact.importance,
                    confidence=fact.confidence,
                )
            )

        for query in fixture.queries:
            t0 = time.perf_counter()
            hits = candidate.search(query.query, limit=5)
            elapsed = time.perf_counter() - t0
            top = hits[0] if hits else None
            hit = bool(top) and any(kw in top.content for kw in query.expected_keywords)
            results.append(
                QueryResult(
                    backend="hindsight",
                    query=query.query,
                    top_content=top.content if top else None,
                    hit=hit,
                    latency_s=elapsed,
                )
            )
    finally:
        real_client.close()

    rss_after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    print(f"  [hindsight] this-process ru_maxrss delta: {rss_after - rss_before} (under-reports — server is out-of-process; cross-check `docker stats`)")
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="also run real Hindsight (billed)")
    parser.add_argument("--category", default=None, help="filter to one fixture category")
    parser.add_argument(
        "--base-url",
        default="http://localhost:8888",
        help="Hindsight server base URL for --live (default: http://localhost:8888)",
    )
    args = parser.parse_args()

    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    tokenize("预热分词器")  # jieba lazy-loads its dict on first call; keep that cost out of timed queries
    fixtures = [f for f in FIXTURES if args.category is None or f.category == args.category]
    if not fixtures:
        print(f"No fixtures match category={args.category!r}", file=sys.stderr)
        sys.exit(1)

    for fixture in fixtures:
        print(f"\n=== {fixture.id} ({fixture.category}) ===")
        db_path = _OUTPUT_DIR / f"{fixture.id}.canonical.db"
        if db_path.exists():
            db_path.unlink()
        canonical_results = _run_canonical(fixture, db_path)
        hindsight_results = _run_hindsight_live(fixture, args.base_url) if args.live else []
        hindsight_by_query = {r.query: r for r in hindsight_results}

        for c in canonical_results:
            h = hindsight_by_query.get(c.query)
            print(f"  query: {c.query}")
            print(
                f"    canonical: hit={c.hit} latency={c.latency_s * 1000:.1f}ms "
                f"top={c.top_content!r}"
            )
            if args.live:
                if h:
                    print(
                        f"    hindsight: hit={h.hit} latency={h.latency_s * 1000:.1f}ms "
                        f"top={h.top_content!r}"
                    )
                else:
                    print("    hindsight: skipped (see stderr)")
            else:
                print("    hindsight: skipped (dry run — pass --live to spend real API calls)")


if __name__ == "__main__":
    main()
