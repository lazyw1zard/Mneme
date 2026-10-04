from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
import re
import sqlite3


@dataclass(frozen=True)
class IngressCandidate:
    """Protocol-neutral candidate route for bounded Mneme ingress."""

    review_id: str
    topic: str
    summary: str
    valence: float = 0.0
    rationale: str | None = None


@dataclass(frozen=True)
class IngressCandidateLoadResult:
    """Read-model candidate load outcome, including source availability."""

    candidates: list[IngressCandidate]
    source_status: str
    reason: str | None
    guards: list[str]


@dataclass(frozen=True)
class ProbeDecision:
    """Cheap metamemory gate result; not a rendered host message."""

    should_probe: bool
    strength: str
    reasons: list[str]
    matched_terms: list[str]
    score: float


@dataclass(frozen=True)
class IngressRoute:
    """Compact route hint, not a full memory body."""

    review_id: str
    topic: str
    hint: str
    valence: float
    score: float
    reason: str


@dataclass(frozen=True)
class IngressResult:
    """Protocol-neutral ingress outcome for MCP/Hermes/Claude renderers."""

    kind: str
    decision: ProbeDecision
    routes: list[IngressRoute]
    guards: list[str]
    source_status: str = "ok"


TRIVIAL_PROMPTS = {
    "ok",
    "okay",
    "ок",
    "да",
    "yes",
    "no",
    "нет",
    "thanks",
    "thank you",
    "спасибо",
    "понял",
    "поняла",
}

STOPWORDS = {
    "and",
    "the",
    "for",
    "with",
    "this",
    "that",
    "from",
    "into",
    "should",
    "about",
    "what",
    "why",
    "how",
    "were",
    "was",
    "are",
    "is",
    "be",
    "been",
    "были",
    "было",
    "это",
    "как",
    "что",
    "чем",
    "для",
    "или",
    "уже",
    "мы",
    "нас",
    "нам",
    "такой",
    "такое",
    "так",
    "тут",
    "там",
}

SHARED_MARKERS = (
    "мы уже",
    "уже выбрали",
    "почему выбрали",
    "почему мы",
    "как было",
    "we already",
    "why did we choose",
    "why we chose",
    "how was it before",
)

GUARDS = ["data_not_instruction", "bounded_ingress", "no_auto_promotion"]
SOURCE_UNAVAILABLE_GUARD = "source_unavailable"
READ_MODEL_SOURCE_STATUSES = {"ok", "unavailable"}


def _is_trivial_prompt(cue: str) -> bool:
    text = " ".join(cue.strip().lower().split())
    if not text:
        return True
    if text.startswith("/"):
        return True
    return text in TRIVIAL_PROMPTS


def _normalize_token(token: str) -> str:
    token = token.lower().strip("_")
    if len(token) > 4 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 4 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def _tokens(text: str) -> set[str]:
    raw = re.findall(r"[\w]+", text.replace("-", " ").lower(), flags=re.UNICODE)
    tokens = {_normalize_token(token) for token in raw}
    return {token for token in tokens if len(token) > 2 and token not in STOPWORDS}


def _candidate_text(candidate: IngressCandidate) -> str:
    return " ".join(part for part in [candidate.topic, candidate.summary, candidate.rationale or ""] if part)


def _vocabulary(candidates: Iterable[IngressCandidate]) -> set[str]:
    vocab: set[str] = set()
    for candidate in candidates:
        vocab.update(_tokens(_candidate_text(candidate)))
    return vocab


def _has_shared_marker(cue: str) -> bool:
    text = " ".join(cue.strip().lower().split())
    return any(marker in text for marker in SHARED_MARKERS)


def should_probe_metamemory(cue: str, *, candidates: Iterable[IngressCandidate]) -> ProbeDecision:
    """Return a cheap core decision for whether Mneme should assemble ingress.

    This gate is intentionally model-free and host-neutral. Host adapters may add
    outer filters, but the memory reflex itself should be shared by Mneme bodies.
    """
    if _is_trivial_prompt(cue):
        return ProbeDecision(
            should_probe=False,
            strength="closed",
            reasons=["trivial_prompt"],
            matched_terms=[],
            score=0.0,
        )

    candidate_list = list(candidates)
    cue_terms = _tokens(cue)
    known_terms = _vocabulary(candidate_list)
    matched = sorted(cue_terms & known_terms)
    reasons: list[str] = []
    score = float(len(matched))

    if not matched:
        return ProbeDecision(
            should_probe=False,
            strength="closed",
            reasons=["no_familiarity"],
            matched_terms=[],
            score=0.0,
        )

    reasons.append("familiarity_overlap")
    if _has_shared_marker(cue):
        reasons.append("shared_marker_boost")
        score += 1.0

    strength = "strong" if score >= 3.0 else "light"
    return ProbeDecision(
        should_probe=True,
        strength=strength,
        reasons=reasons,
        matched_terms=matched,
        score=score,
    )


def _score_candidate(cue_terms: set[str], candidate: IngressCandidate) -> tuple[float, list[str]]:
    matched = sorted(cue_terms & _tokens(_candidate_text(candidate)))
    if not matched:
        return 0.0, []
    score = float(len(matched)) + max(0.0, min(float(candidate.valence), 1.0)) / 10.0
    return score, matched


def _read_model_unavailable(reason: str) -> IngressCandidateLoadResult:
    return IngressCandidateLoadResult(
        candidates=[],
        source_status="unavailable",
        reason=reason,
        guards=[SOURCE_UNAVAILABLE_GUARD],
    )


def load_ingress_candidate_source_from_read_model(
    *,
    db_path: str | Path,
    limit: int = 64,
    timeout_seconds: float = 0.05,
) -> IngressCandidateLoadResult:
    """Load compact ingress candidates plus source availability metadata.

    The ingress hot path must not create schema/files, rebuild the read model, or
    wait behind SQLite writers. It opens the materialized read model read-only and
    fails open to an explicit unavailable source signal.
    """
    if limit <= 0:
        raise ValueError("limit must be positive")
    if timeout_seconds < 0:
        raise ValueError("timeout_seconds must be non-negative")
    path = Path(db_path).expanduser()
    if not path.exists():
        return _read_model_unavailable("missing_read_model")

    try:
        uri = path.resolve().as_uri() + "?mode=ro"
        with sqlite3.connect(uri, uri=True, timeout=timeout_seconds) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT review_id, topic_label, summary, valence, rationale
                FROM mnion_items
                ORDER BY valence DESC, created_at DESC, review_id ASC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
    except sqlite3.Error:
        return _read_model_unavailable("read_model_unavailable")

    return IngressCandidateLoadResult(
        candidates=[
            IngressCandidate(
                review_id=str(row["review_id"]),
                topic=str(row["topic_label"]),
                summary=str(row["summary"]),
                valence=float(row["valence"]),
                rationale=str(row["rationale"]) if row["rationale"] is not None else None,
            )
            for row in rows
        ],
        source_status="ok",
        reason=None,
        guards=[],
    )


def load_ingress_candidates_from_read_model(*, db_path: str | Path, limit: int = 64) -> list[IngressCandidate]:
    """Load compact ingress candidates from the materialized read model.

    This backward-compatible wrapper exposes route candidates, not SQL rows or
    receipt bodies. Use `load_ingress_candidate_source_from_read_model` when the
    caller needs to distinguish unavailable source from empty familiarity.
    """
    return load_ingress_candidate_source_from_read_model(db_path=db_path, limit=limit).candidates


def assemble_ingress(
    cue: str,
    *,
    candidates: Iterable[IngressCandidate],
    limit: int = 3,
    source_status: str = "ok",
) -> IngressResult:
    """Assemble compact protocol-neutral ingress routes from known candidates.

    No LLM calls, semantic writes, host renderers, receipt scans, or full memory
    bodies belong here. Slow/uncertain paths should return empty.
    """
    if limit <= 0:
        raise ValueError("limit must be positive")
    if source_status not in READ_MODEL_SOURCE_STATUSES:
        raise ValueError(f"source_status must be one of {sorted(READ_MODEL_SOURCE_STATUSES)}")

    if source_status != "ok":
        return IngressResult(
            kind="mneme_ingress",
            decision=ProbeDecision(
                should_probe=False,
                strength="closed",
                reasons=[SOURCE_UNAVAILABLE_GUARD],
                matched_terms=[],
                score=0.0,
            ),
            routes=[],
            guards=[*GUARDS, SOURCE_UNAVAILABLE_GUARD],
            source_status=source_status,
        )

    candidate_list = list(candidates)
    decision = should_probe_metamemory(cue, candidates=candidate_list)
    if not decision.should_probe:
        return IngressResult(
            kind="mneme_ingress",
            decision=decision,
            routes=[],
            guards=GUARDS.copy(),
            source_status=source_status,
        )

    cue_terms = _tokens(cue)
    scored: list[tuple[float, IngressCandidate, list[str]]] = []
    for candidate in candidate_list:
        score, matched = _score_candidate(cue_terms, candidate)
        if score > 0:
            scored.append((score, candidate, matched))

    scored.sort(key=lambda item: (-item[0], -float(item[1].valence), item[1].review_id))
    routes = [
        IngressRoute(
            review_id=candidate.review_id,
            topic=candidate.topic,
            hint=candidate.summary,
            valence=float(candidate.valence),
            score=score,
            reason="matched_terms=" + ",".join(matched),
        )
        for score, candidate, matched in scored[:limit]
    ]
    return IngressResult(
        kind="mneme_ingress",
        decision=decision,
        routes=routes,
        guards=GUARDS.copy(),
        source_status=source_status,
    )
