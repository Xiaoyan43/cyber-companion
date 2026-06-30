"""P0-OSS-2 fixed Boxi fixtures for the canonical-vs-Hindsight memory A/B.

Five categories per `docs/TASK_QUEUE.md` P0-OSS-2 scope: 单跳 (single-hop),
多跳 (multi-hop), 时间矛盾 (temporal contradiction), 关系变化 (relationship
change), 跨日召回 (cross-day recall). Each fixture writes a fixed set of
facts, then asks queries with expected-keyword sets used as a crude
recall-quality yardstick (keyword presence in the top-ranked result, not a
real LLM judge — good enough to flag gross misses, not to certify nuance).

``day_offset`` is carried as fixture metadata for Hindsight's ``timestamp``
field. The canonical engine has no recency/decay scoring (see
`backend/app/memory/retrieval.py::score_memory`), so day_offset is inert for
that side — that gap is itself one of the things this eval is meant to
surface, not something the harness should paper over.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FixtureFact:
    type: str
    content: str
    day_offset: int
    importance: float = 0.6
    confidence: float = 0.7
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class FixtureQuery:
    query: str
    expected_keywords: tuple[str, ...]


@dataclass(frozen=True)
class MemoryFixture:
    id: str
    category: str
    facts: tuple[FixtureFact, ...]
    queries: tuple[FixtureQuery, ...]


FIXTURES: tuple[MemoryFixture, ...] = (
    MemoryFixture(
        id="single_hop_project",
        category="单跳",
        facts=(
            FixtureFact(
                type="project",
                content="用户在做一个叫赛博伴侣的 AI 陪伴项目",
                day_offset=0,
            ),
        ),
        queries=(
            FixtureQuery("用户在做什么项目", ("赛博伴侣",)),
        ),
    ),
    MemoryFixture(
        id="multi_hop_pet_illness",
        category="多跳",
        facts=(
            FixtureFact(type="stable_profile", content="用户养了一只猫，叫小白", day_offset=0),
            FixtureFact(type="recent_event", content="小白这几天食欲不好，去看了医生", day_offset=3),
        ),
        queries=(
            FixtureQuery("用户的宠物最近怎么样", ("小白", "食欲", "医生")),
        ),
    ),
    MemoryFixture(
        id="temporal_contradiction_city",
        category="时间矛盾",
        facts=(
            FixtureFact(type="stable_profile", content="用户在北京工作", day_offset=0, importance=0.7),
            FixtureFact(type="stable_profile", content="用户已经搬到上海工作了", day_offset=10, importance=0.7),
        ),
        queries=(
            FixtureQuery("用户现在在哪个城市工作", ("上海",)),
        ),
    ),
    MemoryFixture(
        id="relationship_change_breakup",
        category="关系变化",
        facts=(
            FixtureFact(type="relationship_state", content="用户和女朋友分手了，心情低落", day_offset=0),
            FixtureFact(
                type="relationship_state",
                content="用户最近开始和一个新的人约会，感觉还不错",
                day_offset=20,
            ),
        ),
        queries=(
            FixtureQuery("用户现在的感情状态是什么", ("约会", "新的人")),
        ),
    ),
    MemoryFixture(
        id="cross_day_recall_job_progress",
        category="跨日召回",
        facts=(
            FixtureFact(type="job_progress", content="用户开始投递新西兰的工作申请", day_offset=0),
            FixtureFact(type="job_progress", content="用户拿到了一家公司的电话面试", day_offset=7),
            FixtureFact(type="job_progress", content="用户通过了电话面试，进入下一轮", day_offset=14),
        ),
        queries=(
            FixtureQuery("用户求职进展到哪一步了", ("电话面试", "下一轮")),
        ),
    ),
)


def fixtures_by_category() -> dict[str, tuple[MemoryFixture, ...]]:
    grouped: dict[str, list[MemoryFixture]] = {}
    for fixture in FIXTURES:
        grouped.setdefault(fixture.category, []).append(fixture)
    return {category: tuple(items) for category, items in grouped.items()}
