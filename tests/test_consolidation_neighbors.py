"""Neutral fixtures only; all state belongs to tmp_path."""
import asyncio
import json
import sqlite3
from pathlib import Path

import pytest
from mnion.config import load_mneme_config
from mnion.read_model import materialize_mnion_items_sqlite, read_model_freshness
from mnion.mcp_server import create_server


def seed(root, seqs=(1, 10, 10, 49, 50, 51, None), project=True):
    receipts = root / 'micro_consolidation_reviews.jsonl'
    rows = []
    for i, seq in enumerate(seqs):
        rows.append({'id': f'review_seed{i}', 'mneme_call_seq': seq,
                     'created_at': '2026-01-01T00:00:00Z', 'grouped_ids': [f'tag_old{i}'],
                     'mnion': {'summary': f'Original neutral text {i}', 'valence': .5,
                               'claim': f'Understanding {i}'}})
    receipts.write_text(''.join(json.dumps(r)+'\n' for r in rows))
    db = root / 'mneme_read_model.sqlite3'
    if project:
        materialize_mnion_items_sqlite(receipts_path=receipts, db_path=db)
    return receipts, db


def test_config_defaults_and_override(tmp_path):
    p = tmp_path / 'config.toml'
    c = load_mneme_config(p)
    assert c.consolidation_neighbors.lookback_calls == 40
    assert c.consolidation_neighbors.candidate_limit == 4
    assert c.consolidation_neighbors.enabled is True
    p.write_text('[consolidation_neighbors]\nenabled=false\nlookback_calls=6\ncandidate_limit=2\n')
    c = load_mneme_config(p).consolidation_neighbors
    assert (c.enabled, c.lookback_calls, c.candidate_limit) == (False, 6, 2)


@pytest.mark.parametrize('field,value', [('lookback_calls','-1'), ('lookback_calls','true'),
    ('lookback_calls','1.5'), ('lookback_calls','"40"'), ('candidate_limit','0'),
    ('candidate_limit','false'), ('enabled','"yes"')])
def test_config_rejects_invalid_neighbors(tmp_path, field, value):
    p = tmp_path / 'config.toml'
    p.write_text(f'[consolidation_neighbors]\n{field}={value}\n')
    with pytest.raises(ValueError):
        load_mneme_config(p)


def test_temporal_candidates_are_bounded_and_not_body_preload(tmp_path):
    from mnion.neighbors import temporal_candidates
    receipts, db = seed(tmp_path)
    before = receipts.read_bytes()
    got = temporal_candidates(db_path=db, anchor_seq=50, lookback_calls=40, limit=3)
    assert got['status'] == 'ok'
    assert [x['review_id'] for x in got['candidates']] == ['review_seed4','review_seed3','review_seed1']
    assert got['has_more'] is True
    assert all(set(x) == {'review_id', 'claim', 'mneme_call_seq'} for x in got['candidates'])
    assert receipts.read_bytes() == before
    all_in_window = temporal_candidates(db_path=db, anchor_seq=50, lookback_calls=40, limit=9)
    assert [x['review_id'] for x in all_in_window['candidates']] == ['review_seed4','review_seed3','review_seed1','review_seed2']
    assert all_in_window['has_more'] is False
    assert all_in_window['reason'] == 'consolidation_call_window'


def test_unknown_sequence_excluded_and_missing_db_not_created(tmp_path):
    from mnion.neighbors import temporal_candidates
    _, db = seed(tmp_path, seqs=(None, True, '9', -1, 0))
    got = temporal_candidates(db_path=db, anchor_seq=10, lookback_calls=40, limit=8)
    assert [x['review_id'] for x in got['candidates']] == ['review_seed4']
    missing = tmp_path / 'missing.sqlite3'
    got = temporal_candidates(db_path=missing, anchor_seq=10, lookback_calls=40, limit=4)
    assert got['status'] == 'unavailable'
    assert not missing.exists()


def test_legacy_projection_is_stale_then_migrates(tmp_path):
    receipts, db = seed(tmp_path)
    with sqlite3.connect(db) as conn:
        conn.execute('DROP INDEX IF EXISTS mnion_items_call_seq')
        conn.execute('ALTER TABLE mnion_items DROP COLUMN consolidation_call_seq')
    assert read_model_freshness(receipts_path=receipts, db_path=db).status == 'stale'
    materialize_mnion_items_sqlite(receipts_path=receipts, db_path=db)
    assert read_model_freshness(receipts_path=receipts, db_path=db).status == 'fresh'


def call(server, name, args):
    result = asyncio.run(server.call_tool(name, args))
    if hasattr(result, 'structured_content'):
        return result.structured_content
    return result[1]


def pending(root, *, limit=2, lookback=40, enabled=True):
    seed(root, seqs=(1, 8, 9))
    (root/'mneme_seq.json').write_text('{"seq":10}')
    config = root/'config.toml'
    config.write_text(f'[review_pressure]\ncall_seq_interval=2\npacket_limit=2\n'
                      f'[consolidation_neighbors]\nenabled={str(enabled).lower()}\nlookback_calls={lookback}\ncandidate_limit={limit}\n')
    server = create_server(state_dir=root, config_path=config)
    call(server, 'capture', {'delta':'Copper kettle observation.', 'valence':.8,'hooks':['kettle']})
    got = call(server, 'capture', {'delta':'Violet window observation.', 'valence':.8,'hooks':['window']})
    assert got['review_pressure']['needed']
    return server, got


def test_pending_exposes_frozen_candidates_and_redirects(tmp_path):
    server, got = pending(tmp_path)
    surface = got['review_packet']['neighbors']
    assert surface['anchor_seq'] == 12
    assert [x['review_id'] for x in surface['candidates']] == ['review_seed2','review_seed1']
    assert surface['has_more'] is True
    saved = json.loads((tmp_path/'pending_review.json').read_text())
    assert saved['review_packet']['neighbors'] == surface
    again = call(server,'capture',{'delta':'Do not append while pending.', 'valence':.2})
    assert again['review_packet']['neighbors'] == surface


def relation(target='review_seed2', index=1):
    return {'mnion_index':index,'target_review_id':target,'relation_kind':'continues',
            'relation_summary':'New understanding continues the opened original; shared topic alone is not the ground.'}


def review_args(got):
    return {'selected_ids':got['review_packet']['selected_ids'],
            'member_ids':got['review_packet']['selected_ids'], 'summary':'A new neutral understanding.',
            'valence':.7, 'claim':'A new understanding from two observations.'}


def test_review_and_relation_share_receipt_and_reopen(tmp_path):
    server, got = pending(tmp_path)
    old = (tmp_path/'micro_consolidation_reviews.jsonl').read_bytes()
    args = review_args(got)
    args['relations'] = [relation()]
    result = call(server,'consolidate_review',args)
    assert result['ok'], result
    assert len(result['connections']) == 1
    route = result['review_id']
    edge = result['connections'][0]
    assert edge['source_review_id'] == route
    assert edge['target_review_id'] == 'review_seed2'
    receipts = (tmp_path/'micro_consolidation_reviews.jsonl').read_bytes()
    assert receipts.startswith(old)
    assert len(receipts[len(old):].split(b'\n')) == 2
    last = json.loads(receipts[len(old):])
    assert last['connections'] == result['connections']
    assert not (tmp_path/'mnion_connections.jsonl').exists()
    opened = call(server,'get_neighborhood',{'exact_item_route':route})
    assert opened['connections'] == [edge]
    assert call(server,'get_item',{'review_id':'review_seed2'})['item']['mnion']['summary'] == 'Original neutral text 2'
    assert not (tmp_path/'pending_review.json').exists()


@pytest.mark.parametrize('bad', [relation(' review_seed2'),relation('review_missing'),relation(index=0),
    relation(index=True), {**relation(),'relation_kind':'same_topic'}, {**relation(),'relation_summary':''},
    {**relation(),'unexpected':1}, 'bad', None])
def test_invalid_relations_leave_receipt_and_latch_unchanged(tmp_path,bad):
    server, got = pending(tmp_path)
    paths = [tmp_path/'micro_consolidation_reviews.jsonl',tmp_path/'pending_review.json',tmp_path/'mneme_seq.json']
    before = [p.read_bytes() for p in paths]
    args = review_args(got);args['relations']=[bad]
    result = call(server,'consolidate_review',args)
    assert result['ok'] is False
    assert [p.read_bytes() for p in paths] == before


def test_zero_links_and_disabled_neighbors_preserve_legacy_flow(tmp_path):
    server, got = pending(tmp_path, enabled=False)
    assert got['review_packet']['neighbors']['status'] == 'disabled'
    result = call(server,'consolidate_review',review_args(got))
    assert result['ok'], result
    assert not result.get('connections')


def test_projection_failure_retry_reuses_receipt_and_rejects_changed_authorship(tmp_path, monkeypatch):
    import mnion.connections as connections
    server, got = pending(tmp_path)
    args = review_args(got); args['relations'] = [relation()]
    real = connections.materialize_connections
    def fail(**kwargs):
        raise ValueError('injected adjacency failure')
    monkeypatch.setattr(connections, 'materialize_connections', fail)
    result = call(server, 'consolidate_review', args)
    assert result['action'] == 'review_recorded_read_model_failed'
    assert (tmp_path/'pending_review.json').exists()
    recorded = (tmp_path/'micro_consolidation_reviews.jsonl').read_bytes()
    changed = {**args, 'summary':'Changed authorship must not replace recorded content.'}
    rejected = call(server, 'consolidate_review', changed)
    assert rejected['ok'] is False
    assert (tmp_path/'micro_consolidation_reviews.jsonl').read_bytes() == recorded
    monkeypatch.setattr(connections, 'materialize_connections', real)
    retry = call(server, 'consolidate_review', args)
    assert retry['ok'], retry
    assert retry['review_id'] == result['review_ids'][0]
    assert (tmp_path/'micro_consolidation_reviews.jsonl').read_bytes() == recorded


def test_capture_cannot_lazy_clear_unprojected_connections(tmp_path, monkeypatch):
    import mnion.connections as connections
    server, got = pending(tmp_path)
    args = review_args(got); args['relations'] = [relation()]
    real = connections.materialize_connections
    def fail(**kwargs):
        raise ValueError('injected adjacency failure')
    monkeypatch.setattr(connections, 'materialize_connections', fail)
    assert call(server,'consolidate_review',args)['ok'] is False
    seq = (tmp_path/'mneme_seq.json').read_bytes()
    again = call(server,'capture',{'delta':'Wait for full closure.', 'valence':.2})
    assert again['action'] == 'redirected_to_pending_review'
    assert (tmp_path/'pending_review.json').exists()
    assert (tmp_path/'mneme_seq.json').read_bytes() == seq
    monkeypatch.setattr(connections, 'materialize_connections', real)
    resumed = call(server,'capture',{'delta':'A distinct passage after repair.', 'valence':.2})
    assert resumed['ok'], resumed
    assert not (tmp_path/'pending_review.json').exists()


def test_multigroup_relations_and_standalone_same_id_retry(tmp_path):
    server, got = pending(tmp_path)
    ids = got['review_packet']['selected_ids']
    args = {'selected_ids':ids, 'mnions':[
        {'summary':'First independent understanding.', 'valence':.5, 'member_ids':[ids[0]]},
        {'summary':'Second independent understanding.', 'valence':.6, 'member_ids':[ids[1]]}],
        'relations':[relation(index=2)]}
    done = call(server,'consolidate_review',args)
    assert done['ok'], done
    edge = done['connections'][0]
    assert edge['source_review_id'] == done['review_ids'][1]
    same = call(server,'connect_items',{k:v for k,v in edge.items() if k in ('source_review_id','target_review_id','relation_kind','relation_summary')})
    assert same['ok'] and same['reused_connection']
    assert same['connection']['id'] == edge['id']
    assert not (tmp_path/'mnion_connections.jsonl').exists()


def test_temporal_query_is_indexed_and_bounded_with_many_ties(tmp_path, monkeypatch):
    from mnion import neighbors
    _, db = seed(tmp_path, seqs=[8]*2000)
    statements, steps = [], []
    real = sqlite3.connect
    def instrument(*args, **kwargs):
        conn = real(*args, **kwargs)
        conn.set_trace_callback(statements.append)
        conn.set_progress_handler(lambda: steps.append(1) or 0, 100)
        return conn
    monkeypatch.setattr(neighbors.sqlite3, 'connect', instrument)
    got = neighbors.temporal_candidates(db_path=db, anchor_seq=10, lookback_calls=40, limit=4)
    assert got['has_more'] and len(got['candidates']) == 4
    assert len(steps) < 10
    assert not any('summary' in q.lower() or 'receipt_json' in q.lower() for q in statements)


def test_migration_failure_rolls_back_sequence_column_and_marker(tmp_path, monkeypatch):
    from mnion import read_model
    receipts, db = seed(tmp_path)
    with sqlite3.connect(db) as conn:
        conn.execute('DROP INDEX mnion_items_call_seq')
        conn.execute('ALTER TABLE mnion_items DROP COLUMN consolidation_call_seq')
        conn.execute("CREATE TRIGGER fail_insert BEFORE INSERT ON mnion_items BEGIN SELECT RAISE(ABORT, 'fixture'); END")
    with pytest.raises(sqlite3.DatabaseError):
        read_model.materialize_mnion_items_sqlite(receipts_path=receipts, db_path=db)
    with sqlite3.connect(db) as conn:
        assert 'consolidation_call_seq' not in {r[1] for r in conn.execute('PRAGMA table_info(mnion_items)')}
        conn.execute('DROP TRIGGER fail_insert')
    read_model.materialize_mnion_items_sqlite(receipts_path=receipts, db_path=db)
    assert read_model.read_model_freshness(receipts_path=receipts, db_path=db).status == 'fresh'


@pytest.mark.parametrize('bad_surface', [None, [], {'status':'ok','candidates':'bad'},
    {'status':'ok','candidates':[{'review_id':' review_seed2','claim':'x','mneme_call_seq':9}]}])
def test_corrupt_neighbor_snapshot_blocks_without_receipt(tmp_path, bad_surface):
    server, got = pending(tmp_path)
    latch = tmp_path/'pending_review.json'
    saved = json.loads(latch.read_text()); saved['review_packet']['neighbors'] = bad_surface
    latch.write_text(json.dumps(saved))
    before = (tmp_path/'micro_consolidation_reviews.jsonl').read_bytes()
    args = review_args(got); args['relations'] = [relation()]
    done = call(server,'consolidate_review',args)
    assert done['ok'] is False
    assert (tmp_path/'micro_consolidation_reviews.jsonl').read_bytes() == before


def test_corrupt_existing_connection_source_blocks_combined_append(tmp_path):
    server, got = pending(tmp_path)
    (tmp_path/'mnion_connections.jsonl').write_text('{"broken":true}\n')
    before = (tmp_path/'micro_consolidation_reviews.jsonl').read_bytes()
    args = review_args(got); args['relations'] = [relation()]
    done = call(server,'consolidate_review',args)
    assert done['ok'] is False
    assert (tmp_path/'micro_consolidation_reviews.jsonl').read_bytes() == before


def test_connection_path_alias_does_not_destroy_capture_source(tmp_path):
    server, got = pending(tmp_path)
    config = tmp_path/'config.toml'
    alias_server = create_server(state_dir=tmp_path,config_path=config,
                                 connections_path=tmp_path/'memory_tags.jsonl')
    before = (tmp_path/'memory_tags.jsonl').read_bytes()
    args = review_args(got);args['relations']=[relation()]
    done = call(alias_server,'consolidate_review',args)
    assert done['ok'] is False
    assert (tmp_path/'memory_tags.jsonl').read_bytes() == before
    assert len((tmp_path/'micro_consolidation_reviews.jsonl').read_text().splitlines()) == 3


def test_relations_schema_and_description_explain_optional_authorship(tmp_path):
    server = create_server(state_dir=tmp_path)
    tools = asyncio.run(server.list_tools())
    tool = next(t for t in tools if t.name == 'consolidate_review')
    schema = getattr(tool,'inputSchema',getattr(tool,'input_schema',{}))
    field = schema['properties']['relations']
    assert 'mnion_index' in json.dumps(field)
    assert 'Open selected' in tool.description


def test_real_mcp_stdio_neighbors_and_integrated_relation(tmp_path):
    import os
    import sys
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from mnion.micro_consolidation import load_micro_consolidation_review_receipts
    seed(tmp_path, seqs=(0,))
    (tmp_path/'config.toml').write_text('[review_pressure]\ncall_seq_interval=2\npacket_limit=2\n[consolidation_neighbors]\nlookback_calls=40\ncandidate_limit=1\n')
    env = dict(os.environ, MNEME_STATE_DIR=str(tmp_path), MNEME_CONFIG=str(tmp_path/'config.toml'))
    params = StdioServerParameters(command=sys.executable,args=['-B','-m','mnion.mcp_server'],env=env)
    def unpack(result):
        if getattr(result,'isError',False):
            raise AssertionError(result)
        return getattr(result,'structuredContent',None) or json.loads(result.content[0].text)
    async def exercise():
        async with stdio_client(params) as (reader,writer):
            async with ClientSession(reader,writer) as session:
                await session.initialize()
                schemas = await session.list_tools()
                assert len(schemas.tools) == 7
                await session.call_tool('capture',{'delta':'Copper vessel test observation.','valence':.9})
                got = unpack(await session.call_tool('capture',{'delta':'Violet horizon test observation.','valence':.8}))
                assert got['review_packet']['neighbors']['candidates'][0]['review_id'] == 'review_seed0'
                original = unpack(await session.call_tool('get_item',{'review_id':'review_seed0'}))
                assert original['item']['mnion']['summary'] == 'Original neutral text 0'
                args = review_args(got); args['relations']=[relation('review_seed0')]
                done = unpack(await session.call_tool('consolidate_review',args))
                assert done['ok'], done
                route = done['review_id']
                opened = unpack(await session.call_tool('get_item',{'review_id':route}))
                assert opened['item']['mnion']['summary'] == args['summary']
                arc = unpack(await session.call_tool('get_neighborhood',{'exact_item_route':route}))
                assert arc['connections'] == done['connections']
                return done
    done = asyncio.run(exercise())
    assert len(load_micro_consolidation_review_receipts(tmp_path/'micro_consolidation_reviews.jsonl')) == 2
    assert not (tmp_path/'pending_review.json').exists()
    assert json.loads((tmp_path/'mneme_seq.json').read_text())['seq'] == 2
