"""Independent read-only review probes; only tmp_path state is used."""
import sys
import json
import importlib.util
from pathlib import Path
import pytest
import test_consolidation_neighbors as f

@pytest.mark.parametrize('mutation', ['disabled_nonempty','bad_claim','over_limit','bad_has_more','missing_status'])
def test_surface_rejected_before_authorship(tmp_path, mutation):
    server, got = f.pending(tmp_path)
    latch = tmp_path/'pending_review.json'
    saved = json.loads(latch.read_text())
    s = saved['review_packet']['neighbors']
    if mutation == 'disabled_nonempty': s['status'] = 'disabled'
    elif mutation == 'bad_claim': s['candidates'][0]['claim'] = {'not':'a claim'}
    elif mutation == 'over_limit': s['candidates'] *= 10
    elif mutation == 'bad_has_more': s['has_more'] = 'false'
    elif mutation == 'missing_status': del s['status']
    latch.write_text(json.dumps(saved))
    before = (tmp_path/'micro_consolidation_reviews.jsonl').read_bytes()
    args=f.review_args(got); args['relations']=[f.relation()]
    done = f.call(server,'consolidate_review',args)
    print('PROBE',mutation,json.dumps({'ok':done['ok'],'action':done['action'],'receipt_appended':(tmp_path/'micro_consolidation_reviews.jsonl').read_bytes()!=before}))
    assert done['ok'] is False
    assert (tmp_path/'micro_consolidation_reviews.jsonl').read_bytes()==before


def test_retry_with_invalid_boolean_index_is_rejected(tmp_path, monkeypatch):
    import mnion.connections as connections
    server, got=f.pending(tmp_path)
    args=f.review_args(got);args['relations']=[f.relation()]
    real=connections.materialize_connections
    def fail(**kw): raise ValueError('isolated projection fault')
    monkeypatch.setattr(connections,'materialize_connections',fail)
    first=f.call(server,'consolidate_review',args)
    assert first['action']=='review_recorded_read_model_failed'
    monkeypatch.setattr(connections,'materialize_connections',real)
    args['relations'][0]['mnion_index']=True
    done=f.call(server,'consolidate_review',args)
    print('PROBE boolean_retry',json.dumps({'ok':done['ok'],'action':done['action']}))
    assert done['ok'] is False


def test_missing_attempt_does_not_duplicate_receipt_on_retry(tmp_path,monkeypatch):
    import mnion.connections as connections
    server,got=f.pending(tmp_path)
    latch=tmp_path/'pending_review.json'; saved=json.loads(latch.read_text());del saved['created_at'];latch.write_text(json.dumps(saved))
    args=f.review_args(got);args['relations']=[f.relation()]
    real=connections.materialize_connections
    def fail(**kw): raise ValueError('isolated projection fault')
    monkeypatch.setattr(connections,'materialize_connections',fail)
    first=f.call(server,'consolidate_review',args)
    before=(tmp_path/'micro_consolidation_reviews.jsonl').read_bytes()
    monkeypatch.setattr(connections,'materialize_connections',real)
    done=f.call(server,'consolidate_review',args)
    after=(tmp_path/'micro_consolidation_reviews.jsonl').read_bytes()
    print('PROBE missing_attempt',json.dumps({'first_action':first['action'],'retry_ok':done['ok'],'before_lines':len(before.split(b'\n'))-1,'after_lines':len(after.split(b'\n'))-1,'retry_reused':done.get('review_id')==(first.get('review_ids') or [None])[0]}))
    assert after==before


def test_no_item_relations_rejected_then_empty_links_close(tmp_path):
    server,got=f.pending(tmp_path)
    args={'selected_ids':got['review_packet']['selected_ids'],'mnions':[], 'reviewed_noise_ids':got['review_packet']['selected_ids'],'relations':[f.relation()]}
    before=(tmp_path/'micro_consolidation_reviews.jsonl').read_bytes()
    assert not f.call(server,'consolidate_review',args)['ok']
    assert (tmp_path/'micro_consolidation_reviews.jsonl').read_bytes()==before
    args['relations']=[]
    done=f.call(server,'consolidate_review',args)
    assert done['ok'] and done['review_ids']==[] and not done['connections']


def test_literal_relation_unicode_roundtrip(tmp_path):
    server,got=f.pending(tmp_path)
    args=f.review_args(got);args['relations']=[{**f.relation(),'relation_summary':'Literal first\u2028second\u0085third.'}]
    done=f.call(server,'consolidate_review',args)
    assert done['ok'],done
    arc=f.call(server,'get_neighborhood',{'exact_item_route':done['review_id']})
    assert arc['connections'][0]['relation_summary']==args['relations'][0]['relation_summary']


@pytest.mark.parametrize('lazy_capture', [False,True])
def test_connection_projection_requires_readback(tmp_path,monkeypatch,lazy_capture):
    import sqlite3
    import mnion.connections as connections
    server,got=f.pending(tmp_path)
    args=f.review_args(got);args['relations']=[f.relation()]
    if lazy_capture:
        real=connections.materialize_connections
        def fail(**kw): raise ValueError('isolated first projection fault')
        monkeypatch.setattr(connections,'materialize_connections',fail)
        first=f.call(server,'consolidate_review',args)
        assert first['action']=='review_recorded_read_model_failed'
        monkeypatch.setattr(connections,'materialize_connections',real)
    with sqlite3.connect(tmp_path/'mneme_read_model.sqlite3') as c:
        c.execute('CREATE TABLE IF NOT EXISTS mnion_connections(seq INTEGER PRIMARY KEY, id TEXT UNIQUE NOT NULL,source_review_id TEXT NOT NULL,target_review_id TEXT NOT NULL,payload_json TEXT NOT NULL)')
        c.execute("CREATE TRIGGER ignore_edge BEFORE INSERT ON mnion_connections BEGIN SELECT RAISE(IGNORE); END")
    done=f.call(server,'capture',{'delta':'Distinct observation after failed projection.','valence':.2}) if lazy_capture else f.call(server,'consolidate_review',args)
    with sqlite3.connect(tmp_path/'mneme_read_model.sqlite3') as c:
        rows=c.execute('SELECT count(*) FROM mnion_connections').fetchone()[0]
    print('PROBE projection_readback',json.dumps({'lazy_capture':lazy_capture,'ok':done['ok'],'action':done.get('action'),'latch_exists':(tmp_path/'pending_review.json').exists(),'projected_connections':rows}))
    assert (tmp_path/'pending_review.json').exists()
    assert not done['ok']


def test_temporal_reader_rejects_malformed_exact_route(tmp_path):
    import sqlite3
    from mnion.neighbors import temporal_candidates
    _,db=f.seed(tmp_path,seqs=(8,))
    with sqlite3.connect(db) as c:
        c.execute("UPDATE mnion_items SET review_id='tag_not_an_item', claim='neutral' ")
    got=temporal_candidates(db_path=db, anchor_seq=10,lookback_calls=40,limit=4)
    print('PROBE malformed_route',json.dumps(got))
    assert got['status']=='unavailable' or got['candidates']==[]
