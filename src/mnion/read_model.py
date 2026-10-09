from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json
import re
import sqlite3

from mnion.micro_consolidation import Mnion, load_micro_consolidation_review_receipts
from mnion.pointers import MemoryPointer


@dataclass(frozen=True)
class MnionItem:
    """Agent-facing item returned by the read-model, not a SQL row."""

    review_id: str
    mnion: Mnion
    grouped_ids: list[str]
    created_at: str | None
    guards: list[str]
    receipt: dict[str, Any]


@dataclass(frozen=True)
class ReadModelFreshness:
    """Cheap freshness check for reconstructable SQLite read-model state."""

    status: str
    stored_signature: str | None
    current_signature: str


@dataclass(frozen=True)
class ReadModelRefreshResult:
    """Outcome of optionally repairing a stale/missing read-model."""

    before: ReadModelFreshness
    after: ReadModelFreshness
    materialized_count: int | None

    @property
    def refreshed(self) -> bool:
        return self.materialized_count is not None


@dataclass(frozen=True)
class TopicEntry:
    """Compact memory-area entry for ingress; enough to choose, not flood."""

    label: str
    abstraction: str
    item_count: int
    top_review_ids: list[str]
    max_valence: float
    freshness: str | None = None

    def render(self) -> str:
        ids = ",".join(self.top_review_ids[:3])
        freshness = f"; fresh={self.freshness}" if self.freshness else ""
        return f"- {self.label} [{self.item_count} item(s), valence {self.max_valence:.2f}{freshness}] ids={ids}: {self.abstraction}"


SCHEMA = """
CREATE TABLE IF NOT EXISTS mnion_items (
    review_id TEXT PRIMARY KEY,
    summary TEXT NOT NULL,
    valence REAL NOT NULL,
    rationale TEXT,
    grouped_ids_json TEXT NOT NULL,
    created_at TEXT,
    receipt_json TEXT NOT NULL,
    topic_label TEXT NOT NULL,
    topic_abstraction TEXT NOT NULL
)
"""

META_SCHEMA = """
CREATE TABLE IF NOT EXISTS read_model_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
)
"""

RECEIPTS_SIGNATURE_KEY = "receipts_signature"


def _connect(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute(SCHEMA)
    return conn


def _receipts_signature(receipts_path: str | Path) -> str:
    path = Path(receipts_path).expanduser()
    try:
        stat = path.stat()
    except FileNotFoundError:
        return "missing:0:0"
    return f"file:{stat.st_size}:{stat.st_mtime_ns}"


def _read_only_uri(path: Path) -> str:
    return path.resolve().as_uri() + "?mode=ro"


def read_model_freshness(*, receipts_path: str | Path, db_path: str | Path, timeout_seconds: float = 0.05) -> ReadModelFreshness:
    """Return whether the SQLite read-model was built from current receipts.

    This check is cheap and read-only. It never creates the database or schema;
    callers that choose to repair a stale model should materialize explicitly.
    """
    current_signature = _receipts_signature(receipts_path)
    path = Path(db_path).expanduser()
    if not path.exists():
        return ReadModelFreshness(status="missing", stored_signature=None, current_signature=current_signature)
    try:
        with sqlite3.connect(_read_only_uri(path), uri=True, timeout=timeout_seconds) as conn:
            row = conn.execute(
                "SELECT value FROM read_model_meta WHERE key = ?",
                (RECEIPTS_SIGNATURE_KEY,),
            ).fetchone()
    except sqlite3.Error:
        return ReadModelFreshness(status="stale", stored_signature=None, current_signature=current_signature)
    stored_signature = str(row[0]) if row is not None else None
    status = "fresh" if stored_signature == current_signature else "stale"
    return ReadModelFreshness(status=status, stored_signature=stored_signature, current_signature=current_signature)


def _topic_for_summary(summary: str) -> tuple[str, str]:
    text = summary.lower()
    if "residual" in text or "did not form a sharper object" in text:
        return "Mneme residual / uncategorized", "Reviewed mnion items without a stable topic yet."
    if "continuity" in text or "trace-governed" in text or "first-person" in text:
        return "Continuity / trace-governed identity", "Continuity, identity, and shaped traces."
    if "micro-consolidation" in text or "bounded unread" in text or "review receipts" in text:
        return "Mneme micro-consolidation", "Review packets, receipts, pointers, and retrieval staging."
    if "naming boundary" in text or "memory_tag-to-mnion" in text:
        return "Mneme naming / memory_tag-to-mnion boundary", "Raw tags, consolidated mnions, and provenance split."
    if "capture" in text or "ttl" in text or "portable" in text or "pre-capture" in text:
        return "Memory-tag capture layer", "MCP capture, call TTL, pre-capture filter, and portability."
    if "self-promise" in text or "active inference" in text or "welfare" in text or "harness" in text:
        return "Agency / contour welfare", "Self-promise, active inference, harness/body stability."
    return "Mneme residual / uncategorized", "Reviewed mnion items without a stable topic yet."


def _mnion_from_payload(payload: dict[str, Any]) -> Mnion:
    return Mnion(
        summary=str(payload.get("summary", "")).strip(),
        valence=float(payload.get("valence", 0.0)),
        rationale=str(payload["rationale"]).strip() if payload.get("rationale") is not None else None,
    )


def _mnion_entries_from_receipt(receipt: dict[str, Any]) -> list[tuple[str, dict[str, Any], list[Any]]]:
    nested = receipt.get("mnions")
    if isinstance(nested, list):
        entries: list[tuple[str, dict[str, Any], list[Any]]] = []
        for entry in nested:
            if not isinstance(entry, dict):
                continue
            review_id = entry.get("review_id")
            mnion_payload = entry.get("mnion")
            grouped_ids = entry.get("grouped_ids", [])
            if isinstance(review_id, str) and review_id and isinstance(mnion_payload, dict):
                entries.append((review_id, mnion_payload, grouped_ids if isinstance(grouped_ids, list) else []))
        return entries

    review_id = str(receipt.get("id") or "").strip()
    mnion_payload = receipt.get("mnion") or receipt.get("contour")
    if not review_id or not isinstance(mnion_payload, dict):
        return []
    grouped_ids = receipt.get("grouped_ids") or mnion_payload.get("member_ids") or []
    return [(review_id, mnion_payload, grouped_ids if isinstance(grouped_ids, list) else [])]


def materialize_mnion_items_sqlite(*, receipts_path: str | Path, db_path: str | Path) -> int:
    """Rebuild the SQLite read-model from append-only review receipts.

    JSONL receipts remain the audit/source of truth. SQLite is only a compact
    read-model so the agent can call get_item/resolve_pointer instead of scanning
    receipts or touching SQL.
    """
    receipts = load_micro_consolidation_review_receipts(receipts_path)
    with _connect(db_path) as conn:
        conn.execute(META_SCHEMA)
        conn.execute("DELETE FROM mnion_items")
        count = 0
        for receipt in receipts:
            for review_id, mnion_payload, grouped_ids in _mnion_entries_from_receipt(receipt):
                mnion = _mnion_from_payload(mnion_payload)
                if not mnion.summary:
                    continue
                label, abstraction = _topic_for_summary(mnion.summary)
                conn.execute(
                    """
                    INSERT OR REPLACE INTO mnion_items (
                        review_id, summary, valence, rationale, grouped_ids_json,
                        created_at, receipt_json, topic_label, topic_abstraction
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        review_id,
                        mnion.summary,
                        mnion.valence,
                        mnion.rationale,
                        json.dumps([str(v) for v in grouped_ids], ensure_ascii=False),
                        receipt.get("created_at"),
                        json.dumps(receipt, ensure_ascii=False, sort_keys=True),
                        label,
                        abstraction,
                    ),
                )
                count += 1
        conn.execute(
            "INSERT OR REPLACE INTO read_model_meta (key, value) VALUES (?, ?)",
            (RECEIPTS_SIGNATURE_KEY, _receipts_signature(receipts_path)),
        )
        return count


def ensure_read_model_fresh(*, receipts_path: str | Path, db_path: str | Path) -> ReadModelRefreshResult:
    """Materialize the read-model only when it is missing or stale."""
    before = read_model_freshness(receipts_path=receipts_path, db_path=db_path)
    if before.status == "fresh":
        return ReadModelRefreshResult(before=before, after=before, materialized_count=None)
    materialized_count = materialize_mnion_items_sqlite(receipts_path=receipts_path, db_path=db_path)
    after = read_model_freshness(receipts_path=receipts_path, db_path=db_path)
    return ReadModelRefreshResult(before=before, after=after, materialized_count=materialized_count)


def _item_from_row(row: sqlite3.Row) -> MnionItem:
    receipt = json.loads(row["receipt_json"])
    grouped_ids = json.loads(row["grouped_ids_json"])
    return MnionItem(
        review_id=str(row["review_id"]),
        mnion=Mnion(summary=str(row["summary"]), valence=float(row["valence"]), rationale=row["rationale"]),
        grouped_ids=[str(v) for v in grouped_ids],
        created_at=row["created_at"],
        guards=["do_not_infer", "no_auto_promotion", "receipt_backed"],
        receipt=receipt,
    )


def get_item(*, review_id: str, db_path: str | Path) -> MnionItem | None:
    """Return one ready mnion item by review_id, or None on structured miss."""
    with _connect(db_path) as conn:
        row = conn.execute("SELECT * FROM mnion_items WHERE review_id = ?", (str(review_id),)).fetchone()
        return _item_from_row(row) if row is not None else None


MIN_ROUTE_PREFIX = 6
ROUTE_CANDIDATE_LIMIT = 8
_EXACT_ROUTE = re.compile(r"review_[A-Za-z0-9_-]+(?::mnion:[1-9][0-9]*)?")
_ROUTE_HINT = re.compile(rf"(?:review_)?([0-9a-f]{{{MIN_ROUTE_PREFIX},32}})(:mnion:[1-9][0-9]*)?")


def is_valid_route_query(review_id: Any) -> bool:
    """Validate the exact-route/hex-hint union without changing the supplied token."""
    return (isinstance(review_id, str) and 0 < len(review_id) <= 256
            and (_EXACT_ROUTE.fullmatch(review_id) is not None
                 or _ROUTE_HINT.fullmatch(review_id) is not None))


def resolve_review_id(*, review_id: str, db_path: str | Path) -> tuple[str | None, list[str]]:
    """Resolve an exact route or an explicitly supported hexadecimal route hint.

    Hints accept 6..32 lowercase hex characters, with optional ``review_`` and
    an exact ``:mnion:N`` suffix. Preserve the literal input: no whitespace or
    quote stripping and no type coercion. Existing legacy exact routes still
    work, but a miss on one never becomes a prefix search. A full item route
    never falls back to a longer item number. Ambiguity returns at most eight
    options plus one overflow witness; callers must not choose arbitrarily.
    """
    if not is_valid_route_query(review_id):
        return None, []
    exact_shape = _EXACT_ROUTE.fullmatch(review_id)
    hint = _ROUTE_HINT.fullmatch(review_id)
    path = Path(db_path).expanduser()
    if not path.exists():
        return None, []
    conn = sqlite3.connect(_read_only_uri(path), uri=True, timeout=0.05)
    try:
        if exact_shape is not None:
            row = conn.execute(
                "SELECT review_id FROM mnion_items WHERE review_id = ?", (review_id,)
            ).fetchone()
            if row is not None:
                return str(row[0]), []
        if hint is None:
            return None, []
        hex_prefix, suffix = hint.groups()
        suffix = suffix or ""
        canonical = "review_" + hex_prefix + suffix
        if canonical != review_id:
            row = conn.execute(
                "SELECT review_id FROM mnion_items WHERE review_id = ?", (canonical,)
            ).fetchone()
            if row is not None:
                return str(row[0]), []
        if len(hex_prefix) == 32 and suffix:
            return None, []
        # The primary-key range avoids reading the whole id index. For a full
        # packet hash, only its item routes qualify; a supplied item number is
        # an exact suffix, never a prefix of another item number.
        prefix = "review_" + hex_prefix
        if len(hex_prefix) == 32:
            prefix += ":mnion:"
        upper = prefix[:-1] + chr(ord(prefix[-1]) + 1)
        rows = conn.execute(
            "SELECT review_id FROM mnion_items WHERE review_id >= ? AND review_id < ? "
            "AND (? = '' OR substr(review_id, -length(?)) = ?) "
            "ORDER BY review_id LIMIT ?",
            (prefix, upper, suffix, suffix, suffix, ROUTE_CANDIDATE_LIMIT + 1),
        ).fetchall()
        matches = [str(row[0]) for row in rows]
        return (matches[0], []) if len(matches) == 1 else (None, matches)
    finally:
        conn.close()


def resolve_pointer(pointer: MemoryPointer, *, db_path: str | Path) -> MnionItem | None:
    """Resolve a pointer through its route.review_id without loading unrelated context."""
    if pointer.route.get("kind") != "micro_consolidation_review":
        return None
    review_id = pointer.route.get("review_id")
    if not review_id:
        return None
    return get_item(review_id=review_id, db_path=db_path)


def list_topics_for_ingress(*, db_path: str | Path, limit: int = 8) -> list[TopicEntry]:
    """Return a compact topic map for ingress instead of a wall of pointers."""
    if limit <= 0:
        raise ValueError("limit must be positive")
    with _connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT
                topic_label,
                topic_abstraction,
                COUNT(*) AS item_count,
                MAX(valence) AS max_valence,
                MAX(created_at) AS freshness
            FROM mnion_items
            GROUP BY topic_label, topic_abstraction
            ORDER BY max_valence DESC, item_count DESC, topic_label ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        topics: list[TopicEntry] = []
        for row in rows:
            id_rows = conn.execute(
                """
                SELECT review_id FROM mnion_items
                WHERE topic_label = ?
                ORDER BY valence DESC, created_at DESC, review_id ASC
                LIMIT 3
                """,
                (row["topic_label"],),
            ).fetchall()
            topics.append(
                TopicEntry(
                    label=str(row["topic_label"]),
                    abstraction=str(row["topic_abstraction"]),
                    item_count=int(row["item_count"]),
                    top_review_ids=[str(r["review_id"]) for r in id_rows],
                    max_valence=float(row["max_valence"] or 0.0),
                    freshness=row["freshness"],
                )
            )
        return topics
