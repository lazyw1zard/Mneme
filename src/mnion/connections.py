"""Authored links preserve a difference between traces, not a new memory tier.

Receipts are append-only; SQLite is a reconstructable mechanical adjacency index.
Only deliberate neighborhood reads repair it. Host ingress reads the projection
separately and may reuse validation, never the repair/write paths in this module.
"""
from __future__ import annotations

from collections import deque
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sqlite3
from typing import Any
from uuid import uuid4

from . import read_model
from .annotations import (annotation_path_for_receipts, default_annotation_state_dir,
                          is_valid_exact_item_route, load_claim_annotations, _pending_barrier)
from .config import default_config_path
from .micro_consolidation import load_micro_consolidation_review_receipts, validate_claim

KINDS = frozenset({'continues', 'corrects', 'follows_from'})
MAX_RELATION_CHARS = 1200
MAX_CONNECTIONS = 8
MAX_DEPTH = 2
_ID = re.compile(r'connection_[0-9a-f]{32}')
_SIGNATURE_KEY = 'connections_signature'
_GUARDS = ['Authored relations are interpretations, not proven causality or occurrence times.',
           'Node claims are navigation; open exact get_item bodies before factual answers.',
           'This bounded view is not a complete graph or an automatic engram candidate.']


@dataclass(frozen=True)
class MnionConnection:
    id: str
    source_review_id: str
    target_review_id: str
    relation_kind: str
    relation_summary: str
    created_at: str
    created_by: str = 'agent'


def _validate(source: Any, target: Any, kind: Any, summary: Any) -> None:
    if not is_valid_exact_item_route(source) or not is_valid_exact_item_route(target):
        raise ValueError('Use two literal exact item routes, never hints or repaired IDs.')
    if source == target:
        raise ValueError('A connection must join distinct items.')
    if not isinstance(kind, str) or kind not in KINDS:
        raise ValueError('relation_kind must be continues, corrects or follows_from.')
    if not isinstance(summary, str) or not summary.strip() or len(summary) > MAX_RELATION_CHARS:
        raise ValueError('relation_summary must be nonblank text, at most 1200 Unicode characters.')
    summary.encode('utf-8')


def load_connections(path: str | Path, receipts_path: str | Path | None = None) -> list[dict[str, Any]]:
    ledger = Path(path).expanduser()
    values, identities = [], set()
    # JSONL boundaries are physical LF, not every Unicode text separator.
    records = []
    if ledger.exists():
        records = [json.loads(line) for line in ledger.read_text(encoding='utf-8').split('\n') if line.strip()]
    if receipts_path is not None:
        for receipt in load_micro_consolidation_review_receipts(receipts_path):
            edges = receipt.get('connections', [])
            if not isinstance(edges, list):
                raise ValueError('Review connections must be a list.')
            for edge in edges:
                if not isinstance(edge, dict) or not isinstance(edge.get('created_at'), str):
                    raise ValueError('Invalid inline connection.')
                # Preserve external append order; weave review edges by recording time.
                position = next((i for i, old in enumerate(records)
                                 if isinstance(old, dict) and isinstance(old.get('created_at'), str)
                                 and old['created_at'] > edge['created_at']), len(records))
                records.insert(position, edge)
    for value in records:
        if not isinstance(value, dict) or set(value) != set(MnionConnection.__dataclass_fields__):
            raise ValueError('Invalid connection receipt fields.')
        _validate(value['source_review_id'], value['target_review_id'],
                  value['relation_kind'], value['relation_summary'])
        identity = value['id']
        if (not isinstance(identity, str) or not _ID.fullmatch(identity) or identity in identities
                or value['created_by'] != 'agent' or not isinstance(value['created_at'], str)):
            raise ValueError('Invalid connection provenance or duplicate identity.')
        datetime.fromisoformat(value['created_at'].replace('Z', '+00:00'))
        identities.add(identity)
        values.append(value)
    return values


def build_review_connections(receipt: dict, relations: Any, candidate_routes: list[str]) -> list[dict]:
    """Resolve local new-group references before the single review append."""
    if not isinstance(relations, list) or len(relations) > MAX_CONNECTIONS:
        raise ValueError('relations must be a list with at most 8 entries')
    entries = receipt['mnions']
    edges, seen = [], set()
    fields = {'mnion_index', 'target_review_id', 'relation_kind', 'relation_summary'}
    for intent in relations:
        if not isinstance(intent, dict) or set(intent) != fields:
            raise ValueError('Each relation requires exactly mnion_index, target_review_id, relation_kind, relation_summary')
        index = intent['mnion_index']
        if type(index) is not int or not 1 <= index <= len(entries):
            raise ValueError('mnion_index must identify a new mnion in this review, starting at 1')
        source = entries[index-1]['review_id']
        target, kind, summary = (intent[k] for k in ('target_review_id', 'relation_kind', 'relation_summary'))
        _validate(source, target, kind, summary)
        if target not in candidate_routes:
            raise ValueError('Relation target must be a literal route from the pending candidate surface')
        key = (source, target, kind, summary)
        if key in seen:
            raise ValueError('Duplicate review relation')
        seen.add(key)
        edges.append(asdict(MnionConnection('connection_'+uuid4().hex, source, target, kind, summary, receipt['created_at'])))
    return edges


def _paths(state_dir=None, receipts_path=None, connections_path=None, annotations_path=None,
           db_path=None, pending_review_path=None):
    root = Path(state_dir).expanduser() if state_dir is not None else default_annotation_state_dir()
    receipts = Path(receipts_path).expanduser() if receipts_path is not None else root/'micro_consolidation_reviews.jsonl'
    ledger = Path(connections_path).expanduser() if connections_path is not None else receipts.parent/'mnion_connections.jsonl'
    annotations = annotation_path_for_receipts(receipts, annotations_path)
    db = Path(db_path).expanduser() if db_path is not None else root/'mneme_read_model.sqlite3'
    pending = Path(pending_review_path).expanduser() if pending_review_path is not None else root/'pending_review.json'
    return root, receipts, ledger, annotations, db, pending


def _separate(paths, protected_paths=()) -> None:
    root, receipts, ledger, annotations, db, pending = paths
    protected = [receipts, annotations, db, pending, root/'memory_tags.jsonl', root/'mneme_seq.json',
                 root/'config.toml', default_config_path(),
                 *(Path(str(base)+suffix) for base in (db, db.resolve())
                   for suffix in ('-journal', '-wal', '-shm')),
                 *(Path(p).expanduser() for p in protected_paths)]
    if any(ledger.resolve() == p.resolve() or (ledger.exists() and p.exists() and ledger.samefile(p))
           for p in protected):
        raise ValueError('Connection ledger must be separate from every runtime source/index artifact.')


def _signature(ledger: Path, receipts: Path) -> str:
    return json.dumps([str(ledger.resolve()), read_model._receipts_signature(ledger),
                       str(receipts.resolve()), read_model._receipts_signature(receipts)])


def _open_read(db: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(read_model._read_only_uri(db), uri=True, timeout=.05)
    conn.row_factory = sqlite3.Row
    return conn


def _fresh(ledger: Path, receipts: Path, db: Path) -> bool:
    if not db.exists():
        return False
    try:
        conn = _open_read(db)
        try:
            conn.execute('SELECT id FROM mnion_connections LIMIT 0')
            row = conn.execute('SELECT value FROM read_model_meta WHERE key=?', (_SIGNATURE_KEY,)).fetchone()
            return row is not None and row[0] == _signature(ledger, receipts)
        finally:
            conn.close()
    except sqlite3.Error:
        return False


def materialize_connections(*, receipts_path: str | Path, connections_path: str | Path,
                            db_path: str | Path) -> int:
    """Rebuild only adjacency and its marker, with schema/rows/marker atomic."""
    receipts, ledger, db = map(Path, (receipts_path, connections_path, db_path))
    signature = _signature(ledger, receipts)
    edges = load_connections(ledger, receipts)
    conn = sqlite3.connect(db, timeout=.05)
    try:
        with conn:
            conn.execute('BEGIN')
            conn.execute('''CREATE TABLE IF NOT EXISTS mnion_connections (
                seq INTEGER PRIMARY KEY, id TEXT UNIQUE NOT NULL,
                source_review_id TEXT NOT NULL, target_review_id TEXT NOT NULL,
                payload_json TEXT NOT NULL)''')
            conn.execute('CREATE INDEX IF NOT EXISTS connections_source ON mnion_connections(source_review_id,seq)')
            conn.execute('CREATE INDEX IF NOT EXISTS connections_target ON mnion_connections(target_review_id,seq)')
            conn.execute('DELETE FROM mnion_connections')
            for seq, edge in enumerate(edges):
                for route in (edge['source_review_id'], edge['target_review_id']):
                    if conn.execute('SELECT 1 FROM mnion_items WHERE review_id=?', (route,)).fetchone() is None:
                        raise ValueError('Recorded connection endpoint is unavailable in the current source.')
                conn.execute('INSERT INTO mnion_connections VALUES(?,?,?,?,?)',
                             (seq,edge['id'],edge['source_review_id'],edge['target_review_id'],
                              json.dumps(edge,ensure_ascii=False,sort_keys=True)))
            # A trigger can silently ignore/alter INSERT: successful execution is not projection proof.
            for edge in edges:
                row = conn.execute('SELECT source_review_id,target_review_id,payload_json '
                                   'FROM mnion_connections WHERE id=?', (edge['id'],)).fetchone()
                if (row is None or row[0] != edge['source_review_id'] or row[1] != edge['target_review_id']
                        or json.loads(row[2]) != edge):
                    raise ValueError('Connection projection read-back failed.')
            conn.execute(read_model.META_SCHEMA)
            conn.execute('INSERT OR REPLACE INTO read_model_meta VALUES(?,?)', (_SIGNATURE_KEY,signature))
        return len(edges)
    finally:
        conn.close()


def _prepare(paths) -> None:
    _, receipts, ledger, annotations, db, _ = paths
    read_model.ensure_read_model_fresh(receipts_path=receipts, db_path=db, annotations_path=annotations)
    if not _fresh(ledger, receipts, db):
        materialize_connections(receipts_path=receipts, connections_path=ledger, db_path=db)
    if not _fresh(ledger, receipts, db):
        raise ValueError('Source changed during projection; retry the explicit read.')


def _error(action: str, exc: Exception) -> dict[str, Any]:
    return {'ok':False,'action':action,'error':str(exc)[:240]}


def append_connection(*, source_review_id: Any, target_review_id: Any, relation_kind: Any,
                      relation_summary: Any, state_dir=None, receipts_path=None,
                      connections_path=None, annotations_path=None, db_path=None,
                      pending_review_path=None, protected_paths: Iterable[str | Path]=(),
                      retry_connection_id: Any=None) -> dict[str, Any]:
    """Explicit live authorship; retry recorded evidence by identity, never blindly append."""
    try:
        _validate(source_review_id, target_review_id, relation_kind, relation_summary)
        if retry_connection_id is not None and (not isinstance(retry_connection_id,str)
                or not _ID.fullmatch(retry_connection_id)):
            raise ValueError('retry_connection_id must be a literal recorded connection ID.')
        paths = _paths(state_dir,receipts_path,connections_path,annotations_path,db_path,pending_review_path)
        _separate(paths,protected_paths)
    except (ValueError,TypeError,OSError) as exc:
        return _error('invalid_connection_request',exc)
    _, receipts, ledger, annotations, db, pending = paths
    blocked = _pending_barrier(pending)
    if blocked is not None:
        return blocked
    try:
        # Validate originals/overlays before any append or index creation.
        sources = load_micro_consolidation_review_receipts(receipts)
        routes = {route for receipt in sources
                  for route,payload,_ in read_model._mnion_entries_from_receipt(receipt)
                  if read_model._mnion_from_payload(payload).summary}
        for route in (source_review_id,target_review_id):
            if route not in routes:
                return {'ok':False,'action':'unknown_item_route','exact_item_route':route}
        load_claim_annotations(annotations)
        edges = load_connections(ledger, receipts)
        if any(e[k] not in routes for e in edges for k in ('source_review_id', 'target_review_id')):
            raise ValueError('Existing connection evidence has an unavailable endpoint; no new evidence appended.')
    except (ValueError,TypeError,OSError) as exc:
        return _error('connection_source_unavailable',exc)
    wanted = (source_review_id,target_review_id,relation_kind,relation_summary)
    def matches(edge):
        return tuple(edge[k] for k in ('source_review_id','target_review_id','relation_kind','relation_summary')) == wanted
    if retry_connection_id is not None:
        edge = next((e for e in edges if e['id']==retry_connection_id),None)
        if edge is None or not matches(edge):
            return _error('invalid_connection_retry',ValueError('ID must name this exact already-recorded authorship.'))
    else:
        edge = next((e for e in edges if matches(e)),None)
    reused = edge is not None
    if edge is None:
        edge = asdict(MnionConnection('connection_'+uuid4().hex,*wanted,
                       datetime.now(timezone.utc).isoformat().replace('+00:00','Z')))
        try:
            encoded = (json.dumps(edge,ensure_ascii=False,sort_keys=True)+'\n').encode('utf-8')
            if ledger.exists() and ledger.stat().st_size:
                with ledger.open('rb') as handle:
                    handle.seek(-1,os.SEEK_END)
                    if handle.read(1)!=b'\n':encoded=b'\n'+encoded
            ledger.parent.mkdir(parents=True,exist_ok=True)
            with ledger.open('ab') as handle:
                handle.write(encoded);handle.flush();os.fsync(handle.fileno())
        except (OSError,UnicodeError) as exc:
            return {**_error('connection_write_failed',exc),'connection':edge,
                    'guidance':'Check this exact ID before retry; an I/O error may follow a partial write.'}
    try:
        _prepare(paths)
        conn = _open_read(db)
        try:
            row = conn.execute('SELECT payload_json FROM mnion_connections WHERE id=?',(edge['id'],)).fetchone()
            if row is None or json.loads(row[0])!=edge:
                raise ValueError('Connection projection read-back failed.')
        finally:
            conn.close()
        # Projection success alone is not durable evidence.
        if edge not in load_connections(ledger, receipts):
            raise ValueError('Connection evidence disappeared after projection.')
    except Exception as exc:
        return {**_error('connection_recorded_projection_failed',exc),'connection':edge,
                'retry_connection_id':edge['id'],'reused_connection':reused,
                'guidance':'Retry connect_items with the same authorship and retry_connection_id; do not append blindly.'}
    return {'ok':True,'action':'connection_recorded','connection':edge,
            'reused_connection':reused,'do_not_infer':_GUARDS}


def get_neighborhood(*, exact_item_route: Any, depth: Any=1, limit: Any=4,
                     state_dir=None, receipts_path=None, connections_path=None,
                     annotations_path=None, db_path=None, pending_review_path=None,
                     protected_paths: Iterable[str | Path]=()) -> dict[str, Any]:
    """A bounded bidirectional traversal view. Node bodies stay behind get_item."""
    try:
        if not is_valid_exact_item_route(exact_item_route):
            raise ValueError('exact_item_route must be a literal item route, not a hint.')
        if type(depth) is not int or not 1<=depth<=MAX_DEPTH or type(limit) is not int or not 1<=limit<=MAX_CONNECTIONS:
            raise ValueError('depth must be 1..2; limit is a total connection budget, 1..8.')
        paths = _paths(state_dir,receipts_path,connections_path,annotations_path,db_path,pending_review_path)
        _separate(paths,protected_paths)
    except (ValueError,TypeError,OSError) as exc:
        return _error('invalid_neighborhood_request',exc)
    _, receipts, ledger, annotations, db, _ = paths
    try:
        _prepare(paths)
        conn = _open_read(db)
        try:
            root = conn.execute('SELECT review_id,claim FROM mnion_items WHERE review_id=?',(exact_item_route,)).fetchone()
            if root is None:
                return {'ok':False,'action':'unknown_item_route','exact_item_route':exact_item_route}
            validate_claim(root['claim'])
            frontier=deque([(exact_item_route,0)])
            nodes={exact_item_route:dict(root)}
            edges={}
            has_more=False
            while frontier:
                route, distance=frontier.popleft()
                seen=list(edges)
                exclusion=' AND id NOT IN ('+','.join('?' for _ in seen)+')' if seen else ''
                remaining=limit-len(edges)
                # Two indexed ordered ranges bound backend work as well as output.
                # An OR followed by a global sort can scan every adjacent edge.
                candidates={}
                for column in ('source_review_id','target_review_id'):
                    for row in conn.execute('SELECT * FROM mnion_connections WHERE '+column+'=?'
                            +exclusion+' ORDER BY seq LIMIT ?', (route,*seen,remaining+1)):
                        candidates[row['id']]=row
                rows=sorted(candidates.values(),key=lambda row:row['seq'])[:remaining+1]
                if distance>=depth:
                    has_more=has_more or bool(rows)
                    continue
                has_more=has_more or len(rows)>remaining
                for row in rows[:remaining]:
                    edge=json.loads(row['payload_json'])
                    if (not isinstance(edge,dict) or set(edge)!=set(MnionConnection.__dataclass_fields__)
                            or edge['id']!=row['id'] or edge['source_review_id']!=row['source_review_id']
                            or edge['target_review_id']!=row['target_review_id']):
                        raise ValueError('Corrupt connection projection.')
                    _validate(edge['source_review_id'],edge['target_review_id'],edge['relation_kind'],edge['relation_summary'])
                    if not isinstance(edge['id'],str) or not _ID.fullmatch(edge['id']) or edge['created_by']!='agent':
                        raise ValueError('Corrupt projected provenance.')
                    if not isinstance(edge['created_at'],str):
                        raise ValueError('Corrupt projected creation time.')
                    datetime.fromisoformat(edge['created_at'].replace('Z','+00:00'))
                    edges[edge['id']]=(row['seq'],edge)
                    for endpoint in (edge['source_review_id'],edge['target_review_id']):
                        if endpoint not in nodes:
                            node=conn.execute('SELECT review_id,claim FROM mnion_items WHERE review_id=?',(endpoint,)).fetchone()
                            if node is None:raise ValueError('Projected endpoint disappeared.')
                            validate_claim(node['claim'])
                            nodes[endpoint]=dict(node);frontier.append((endpoint,distance+1))
            return {'ok':True,'root_review_id':exact_item_route,'nodes':list(nodes.values()),
                    'connections':[edge for _,edge in sorted(edges.values(),key=lambda pair:pair[0])],
                    'depth':depth,'limit':limit,
                    'has_more':has_more,'do_not_infer':_GUARDS}
        finally:
            conn.close()
    except (ValueError,TypeError,OSError,sqlite3.Error) as exc:
        return _error('neighborhood_source_unavailable',exc)
