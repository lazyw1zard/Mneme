"""Small candidate surfaces: acquisition is not semantic relation authorship."""
from pathlib import Path
import sqlite3


from .annotations import is_valid_exact_item_route
from .micro_consolidation import validate_claim


def validate_candidate_surface(surface):
    """Validate the optional snapshot as data; absence is handled by legacy callers."""
    if not isinstance(surface, dict) or surface.get('status') not in {'ok', 'disabled', 'unavailable'}:
        raise ValueError('Invalid neighbor status')
    candidates = surface.get('candidates')
    if not isinstance(candidates, list) or type(surface.get('has_more')) is not bool:
        raise ValueError('Invalid neighbor candidates or has_more')
    if surface['status'] != 'ok':
        if candidates or surface['has_more']:
            raise ValueError('Unavailable/disabled neighbors cannot carry candidates')
        return
    for name, minimum in (('anchor_seq', 0), ('lookback_calls', 0), ('limit', 1)):
        if type(surface.get(name)) is not int or not minimum <= surface[name] <= 9223372036854775806:
            raise ValueError('Invalid neighbor '+name)
    if surface.get('reason') != 'consolidation_call_window' or len(candidates) > surface['limit']:
        raise ValueError('Invalid neighbor origin or candidate count')
    if surface['has_more'] and len(candidates) != surface['limit']:
        raise ValueError('Overflow requires a full bounded candidate set')
    seen = set()
    low = max(0, surface['anchor_seq']-surface['lookback_calls'])
    for node in candidates:
        if not isinstance(node, dict) or set(node) != {'review_id', 'claim', 'mneme_call_seq'}:
            raise ValueError('Invalid neighbor node')
        route, seq = node['review_id'], node['mneme_call_seq']
        if not is_valid_exact_item_route(route) or route in seen:
            raise ValueError('Invalid or duplicate neighbor route')
        validate_claim(node['claim'])
        if type(seq) is not int or not low <= seq <= surface['anchor_seq']:
            raise ValueError('Neighbor outside the declared call window')
        seen.add(route)


def temporal_candidates(*, db_path, anchor_seq, lookback_calls, limit):
    for name, value, minimum in (('anchor_seq', anchor_seq, 0),
                                 ('lookback_calls', lookback_calls, 0), ('limit', limit, 1)):
        if type(value) is not int or not minimum <= value <= 9223372036854775806:
            raise ValueError(f'{name} must be a bounded integer >= {minimum}')
    surface = {'status': 'ok', 'reason': 'consolidation_call_window',
               'anchor_seq': anchor_seq, 'lookback_calls': lookback_calls,
               'limit': limit, 'candidates': [], 'has_more': False,
               'boundary': 'Partial temporal candidates, not semantic relevance or evidence; open selected originals before authoring relations.'}
    path = Path(db_path).expanduser()
    if not path.exists():
        return {**surface, 'status': 'unavailable'}
    try:
        with sqlite3.connect(path.resolve().as_uri()+'?mode=ro', uri=True, timeout=.05) as conn:
            # The compound index bounds acquisition work, including ties; no body reads.
            rows = conn.execute('SELECT review_id, claim, consolidation_call_seq FROM mnion_items '
                                'WHERE consolidation_call_seq >= ? AND consolidation_call_seq <= ? '
                                'ORDER BY consolidation_call_seq DESC, review_id ASC LIMIT ?',
                                (max(0, anchor_seq-lookback_calls), anchor_seq, limit+1)).fetchall()
    except sqlite3.Error:
        return {**surface, 'status': 'unavailable'}
    surface['has_more'] = len(rows) > limit
    surface['candidates'] = [{'review_id': route, 'claim': claim, 'mneme_call_seq': seq}
                             for route, claim, seq in rows[:limit]]
    try:
        validate_candidate_surface(surface)
    except (ValueError, TypeError):
        return {**surface, 'status': 'unavailable', 'candidates': [], 'has_more': False}
    return surface
