"""A transient entrance to an authored change, not another stored memory tier."""
from __future__ import annotations

from datetime import datetime
import json
import re
import sqlite3

from .annotations import is_valid_exact_item_route
from .connections import MnionConnection, _validate
from .micro_consolidation import MAX_CLAIM_CHARS, validate_claim

WINDOW = 4
MAX_ANCHORS = 3


def routes_in_cue(cue: str) -> list[str]:
    """Only literal complete addresses, never fuzzy words or repaired prefixes."""
    result = []
    token = r'(?<![\w:.-])review_[A-Za-z0-9_:-]+(?=\.+(?:\s|$)|[^\w:.-]|$)'
    for match in re.finditer(token, cue):
        route = match.group()
        if is_valid_exact_item_route(route) and route not in result:
            result.append(route)
            if len(result) == MAX_ANCHORS:
                break
    return result


def validate_anchors(routes):
    if not isinstance(routes, (list, tuple)) or len(routes) > MAX_ANCHORS:
        raise ValueError('anchor_routes must be a list/tuple of at most three exact routes')
    if any(not is_valid_exact_item_route(route) for route in routes):
        raise ValueError('anchor_routes require literal exact item routes, without repair')


def _candidate_hint(conn, row, anchors):
    edge = json.loads(row['payload_json'])
    if not isinstance(edge, dict) or set(edge) != set(MnionConnection.__dataclass_fields__):
        raise ValueError('unusable connection projection')
    for name in ('id', 'source_review_id', 'target_review_id'):
        if edge[name] != row[name]:
            raise ValueError('connection projection mismatch')
    _validate(edge['source_review_id'], edge['target_review_id'], edge['relation_kind'], edge['relation_summary'])
    if (not isinstance(edge['id'], str) or not re.fullmatch(r'connection_[0-9a-f]{32}', edge['id'])
            or edge['created_by'] != 'agent' or not isinstance(edge['created_at'], str)):
        raise ValueError('unusable authored provenance')
    datetime.fromisoformat(edge['created_at'].replace('Z', '+00:00'))
    nodes = []
    for route in (edge['source_review_id'], edge['target_review_id']):
        node = conn.execute('SELECT review_id, CASE WHEN length(claim)<=? THEN claim ELSE NULL END AS claim '
                            'FROM mnion_items WHERE review_id=?', (MAX_CLAIM_CHARS, route)).fetchone()
        if node is None or not isinstance(node['claim'], str) or not node['claim'].strip():
            raise ValueError('a recognizable entrance needs both endpoint claims')
        validate_claim(node['claim'])
        nodes.append(dict(node))
    root = next((r for r in anchors if r in {n['review_id'] for n in nodes}), edge['source_review_id'])
    summary = edge['relation_summary']
    return {'root_review_id': root,
            'why_visible': 'explicit_route_in_cue' if root in anchors else 'recent_authored_connection',
            'nodes': nodes,
            'connection': {key: edge[key] for key in ('id', 'source_review_id', 'target_review_id', 'relation_kind')}
                          | {'summary_preview': summary if len(summary) <= 220 else summary[:219] + '…'},
            'retrieval': {'tool': 'get_neighborhood', 'exact_item_route': root, 'depth': 1, 'limit': 4}}


def read_connected_entrance(conn: sqlite3.Connection, anchors=()) -> tuple[list[dict], str]:
    """Fixed indexed windows in the same read transaction; no repair or scans."""
    columns = ('id,seq,source_review_id,target_review_id, '
               'CASE WHEN length(payload_json)<=10000 THEN payload_json ELSE NULL END AS payload_json')
    try:
        witnessed_rows = False
        for anchored in ((True, False) if anchors else (False,)):
            candidates = {}
            if anchored:
                for route in anchors:
                    for column in ('source_review_id', 'target_review_id'):
                        for row in conn.execute(f'SELECT {columns} FROM mnion_connections WHERE {column}=? '
                                                'ORDER BY seq DESC LIMIT ?', (route, WINDOW)):
                            candidates[row['seq']] = row
            else:
                candidates = {r['seq']: r for r in conn.execute(
                    f'SELECT {columns} FROM mnion_connections ORDER BY seq DESC LIMIT ?', (WINDOW,))}
            witnessed_rows = witnessed_rows or bool(candidates)
            for seq in sorted(candidates, reverse=True):
                try:
                    return [_candidate_hint(conn, candidates[seq], anchors)], 'ok'
                except (ValueError, TypeError, KeyError, UnicodeError, RecursionError, OverflowError):
                    continue
        return [], 'unavailable' if witnessed_rows else 'ok'
    except sqlite3.Error:
        return [], 'unavailable'
