"""A relation changes how I enter history; it never rewrites its endpoints."""
import importlib
import json
import sqlite3
from dataclasses import asdict

import pytest

from mnion.read_model import get_item, materialize_mnion_items_sqlite
from mnion.annotations import append_claim_annotation
from mnion.mcp_server import create_server
from test_mnion_claims import _call

A = 'review_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa:mnion:1'
B = 'review_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb:mnion:1'
C = 'review_cccccccccccccccccccccccccccccccc:mnion:1'
MEANING = '  This correction changed the next check; chronology alone does not prove it. 🧭  '


def api():
    spec = importlib.util.find_spec('mnion.connections')
    assert spec is not None, 'authored connection core is missing'
    return importlib.import_module('mnion.connections')


def state(path, project=True, routes=(A, B, C)):
    path.mkdir(parents=True, exist_ok=True)
    receipts = path / 'micro_consolidation_reviews.jsonl'
    rows = [{'id': route.split(':')[0], 'created_at': '2020-01-01T00:00:00Z',
             'mnions': [{'review_id': route, 'mnion': {'summary': f'Original {i}',
               'rationale': 'Original grounds', 'claim': f'Entry {i}', 'valence': .7},
               'grouped_ids': [f'tag_{i}']}]} for i, route in enumerate(routes)]
    receipts.write_text(''.join(json.dumps(r) + '\n' for r in rows))
    (path / 'mneme_seq.json').write_text('{"seq":17}\n')
    (path / 'memory_tags.jsonl').write_text('untouched captures\n')
    (path / 'config.toml').write_text('')
    if project:
        materialize_mnion_items_sqlite(receipts_path=receipts, db_path=path / 'mneme_read_model.sqlite3')


def snapshot(path):
    return {str(p.relative_to(path)): (p.read_bytes(), p.stat().st_mtime_ns)
            for p in path.rglob('*') if p.is_file()}


def append(path, source=B, target=A, kind='corrects', meaning=MEANING, **kw):
    return api().append_connection(source_review_id=source, target_review_id=target,
        relation_kind=kind, relation_summary=meaning, state_dir=path, **kw)


def neighborhood(path, root=A, **kw):
    return api().get_neighborhood(exact_item_route=root, state_dir=path, **kw)


def test_author_explicit_cross_receipt_connection_preserves_originals(tmp_path):
    state(tmp_path)
    before = snapshot(tmp_path)
    originals = [asdict(get_item(review_id=r, db_path=tmp_path / 'mneme_read_model.sqlite3')) for r in (A,B,C)]
    out = append(tmp_path)
    assert out['ok'] and out['action'] == 'connection_recorded'
    edge = out['connection']
    assert edge['source_review_id'] == B and edge['target_review_id'] == A
    assert edge['relation_kind'] == 'corrects' and edge['relation_summary'] == MEANING
    assert edge['id'].startswith('connection_') and edge['created_by'] == 'agent' and edge['created_at']
    for name, value in before.items():
        if name != 'mneme_read_model.sqlite3':
            assert snapshot(tmp_path)[name] == value
    assert [asdict(get_item(review_id=r, db_path=tmp_path / 'mneme_read_model.sqlite3')) for r in (A,B,C)] == originals
    assert api().load_connections(tmp_path / 'mnion_connections.jsonl') == [edge]
    assert neighborhood(tmp_path)['connections'] == [edge]


def test_arc_is_bounded_read_view_not_persistent_object(tmp_path):
    state(tmp_path)
    first = append(tmp_path)['connection']
    second = append(tmp_path, C, B, 'follows_from', 'The new action follows this interpretation.')['connection']
    before = snapshot(tmp_path)
    out = neighborhood(tmp_path, depth=2)
    assert out['ok'] and {n['review_id'] for n in out['nodes']} == {A,B,C}
    assert {e['id'] for e in out['connections']} == {first['id'], second['id']}
    assert all(set(n) == {'review_id', 'claim'} for n in out['nodes'])
    assert not out['has_more']
    assert snapshot(tmp_path) == before
    assert not any('arc' in p.name or 'cluster' in p.name for p in tmp_path.iterdir())


def test_no_edges_keeps_item_usable_without_writes(tmp_path):
    state(tmp_path)
    out = neighborhood(tmp_path)
    assert out['ok'] and out['connections'] == []
    assert out['nodes'] == [{'review_id': A, 'claim': 'Entry 0'}]
    before = snapshot(tmp_path)
    assert neighborhood(tmp_path) == out
    assert snapshot(tmp_path) == before
    assert not (tmp_path / 'mnion_connections.jsonl').exists()


@pytest.mark.parametrize('bad', [None, 42, True, '', 'aaaaaa', A + ' ', '"' + A + '"', A[:-1] + '01', A.split(':')[0], 'review_missing'])
@pytest.mark.parametrize('endpoint', ['source','target'])
def test_bad_or_unknown_endpoints_fail_before_any_mutation(tmp_path, bad, endpoint):
    state(tmp_path, project=False)
    before = snapshot(tmp_path)
    out = append(tmp_path, source=bad if endpoint=='source' else B, target=bad if endpoint=='target' else A)
    assert not out['ok'] and out['action'] in {'invalid_connection_request','unknown_item_route'}
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize('kind', [None, 42, True, '', 'similar', 'Corrects', ' corrects', 'corrects '])
def test_kind_not_silently_repaired(tmp_path, kind):
    state(tmp_path, project=False)
    before = snapshot(tmp_path)
    assert append(tmp_path, kind=kind)['action'] == 'invalid_connection_request'
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize('meaning', [None, True, 42, '', '  \n\u2003', 'x'*1201, '\ud800'])
def test_bad_meaning_fails_before_artifacts_exist(tmp_path, meaning):
    state(tmp_path, project=False)
    before = snapshot(tmp_path)
    assert append(tmp_path, meaning=meaning)['action'] == 'invalid_connection_request'
    assert snapshot(tmp_path) == before


def test_self_edge_is_not_a_meaningful_relation(tmp_path):
    state(tmp_path, project=False)
    before = snapshot(tmp_path)
    assert append(tmp_path, A, A)['action'] == 'invalid_connection_request'
    assert snapshot(tmp_path) == before


def test_whitespace_item_cannot_acquire_connection(tmp_path):
    state(tmp_path, project=False)
    receipts = tmp_path / 'micro_consolidation_reviews.jsonl'
    rows = [json.loads(line) for line in receipts.read_text().splitlines()]
    rows[0]['mnions'][0]['mnion']['summary'] = ' \u2003 '
    receipts.write_text(''.join(json.dumps(r)+'\n' for r in rows))
    before = snapshot(tmp_path)
    assert append(tmp_path)['action'] == 'unknown_item_route'
    assert snapshot(tmp_path) == before


def test_invalid_pending_latch_is_not_cleared(tmp_path):
    state(tmp_path)
    (tmp_path/'pending_review.json').write_text('{}')
    before=snapshot(tmp_path)
    out=append(tmp_path)
    assert out['action']=='blocked_by_invalid_pending_review'
    assert snapshot(tmp_path)==before


@pytest.mark.parametrize('name', ['micro_consolidation_reviews.jsonl','memory_tags.jsonl','mneme_seq.json','config.toml','pending_review.json','claim_annotations.jsonl','mneme_read_model.sqlite3','mneme_read_model.sqlite3-journal','mneme_read_model.sqlite3-wal','mneme_read_model.sqlite3-shm'])
def test_connection_ledger_must_not_alias_runtime_artifact(tmp_path, name):
    state(tmp_path)
    before=snapshot(tmp_path)
    out=append(tmp_path,connections_path=tmp_path/name)
    assert out['action']=='invalid_connection_request'
    assert snapshot(tmp_path)==before


def test_claim_writer_cannot_use_connection_ledger(tmp_path):
    state(tmp_path)
    before=snapshot(tmp_path)
    out=append_claim_annotation(exact_item_route=A,authored_claim='later',state_dir=tmp_path,
                              annotations_path=tmp_path/'mnion_connections.jsonl')
    assert out['action']=='invalid_claim_annotation_request'
    assert snapshot(tmp_path)==before


def test_retry_and_identical_call_do_not_duplicate_evidence(tmp_path):
    state(tmp_path)
    first=append(tmp_path)
    before=snapshot(tmp_path)
    retry=append(tmp_path,retry_connection_id=first['connection']['id'])
    same=append(tmp_path)
    assert retry['ok'] and same['ok'] and retry['reused_connection'] and same['reused_connection']
    assert retry['connection']==same['connection']==first['connection']
    assert snapshot(tmp_path)==before
    mismatch=append(tmp_path,meaning='different',retry_connection_id=first['connection']['id'])
    assert mismatch['action']=='invalid_connection_retry' and snapshot(tmp_path)==before


def test_projection_failure_retains_id_for_safe_retry(tmp_path,monkeypatch):
    state(tmp_path)
    original=api().materialize_connections
    def fail(**kw): raise sqlite3.OperationalError('isolated injected failure')
    monkeypatch.setattr(api(),'materialize_connections',fail)
    out=append(tmp_path)
    assert out['action']=='connection_recorded_projection_failed'
    saved=(tmp_path/'mnion_connections.jsonl').read_bytes()
    monkeypatch.setattr(api(),'materialize_connections',original)
    retry=append(tmp_path,retry_connection_id=out['retry_connection_id'])
    assert retry['ok'] and retry['reused_connection']
    assert (tmp_path/'mnion_connections.jsonl').read_bytes()==saved


def test_overflow_depth_and_cycles_are_bounded(tmp_path):
    routes=[A,B,C]+[f'review_node{i}' for i in range(12)]
    state(tmp_path,routes=routes)
    for route in routes[1:]: append(tmp_path,route,A)
    append(tmp_path,A,B,'continues','A reciprocal interpretation, not a traversal loop.')
    out=neighborhood(tmp_path,depth=2,limit=3)
    assert out['ok'] and len(out['connections'])==3 and len(out['nodes'])<=4 and out['has_more']


@pytest.mark.parametrize('kw', [{'depth':0},{'depth':3},{'depth':True},{'limit':0},{'limit':9},{'limit':True}])
def test_invalid_read_bounds_do_not_repair_storage(tmp_path,kw):
    state(tmp_path,project=False)
    before=snapshot(tmp_path)
    assert neighborhood(tmp_path,**kw)['action']=='invalid_neighborhood_request'
    assert snapshot(tmp_path)==before


def test_mcp_exposes_same_core_and_small_route_view(tmp_path):
    state(tmp_path)
    server=create_server(state_dir=tmp_path)
    out=_call(server,'connect_items',{'source_review_id':B,'target_review_id':A,
             'relation_kind':'corrects','relation_summary':MEANING})
    assert out['ok']
    read=_call(server,'get_neighborhood',{'exact_item_route':A,'depth':1,'limit':4})
    assert read['ok'] and read['connections']==[out['connection']]
