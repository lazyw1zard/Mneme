"""Hostile boundaries stay inside disposable fixtures, never working memory."""
import json
import os
import sqlite3
from dataclasses import asdict

import pytest
from mnion import connections
from mnion.mcp_server import create_server
from test_mnion_connections import A,B,C,MEANING,state,snapshot,append,neighborhood
from test_mnion_claims import _call


def test_existing_dangling_evidence_blocks_new_append_before_repair(tmp_path):
    state(tmp_path,project=False)
    edge=asdict(connections.MnionConnection('connection_'+'a'*32,B,'review_missing','corrects',MEANING,'2020-01-01T00:00:00Z'))
    (tmp_path/'mnion_connections.jsonl').write_text(json.dumps(edge)+'\n')
    before=snapshot(tmp_path)
    out=append(tmp_path)
    assert out['action']=='connection_source_unavailable'
    assert snapshot(tmp_path)==before


@pytest.mark.parametrize('payload',[[],{}, {'id':'broken'}, 'not an object'])
def test_corrupt_index_rows_return_structured_unavailable(tmp_path,payload):
    state(tmp_path);append(tmp_path)
    with sqlite3.connect(tmp_path/'mneme_read_model.sqlite3') as db:
        db.execute('UPDATE mnion_connections SET payload_json=?',(json.dumps(payload),))
    before=snapshot(tmp_path)
    out=neighborhood(tmp_path)
    assert not out['ok'] and out['action']=='neighborhood_source_unavailable'
    assert snapshot(tmp_path)==before


def test_high_degree_reader_bounds_backend_work_not_just_display(tmp_path,monkeypatch):
    routes=[A]+[f'review_many{i}' for i in range(1500)]
    state(tmp_path,routes=routes)
    ledger=tmp_path/'mnion_connections.jsonl'
    edges=[asdict(connections.MnionConnection('connection_'+f'{i:032x}',r,A,'continues',
           'Independent disposable branch.', '2020-01-01T00:00:00Z')) for i,r in enumerate(routes[1:])]
    ledger.write_text(''.join(json.dumps(e)+'\n' for e in edges))
    connections.materialize_connections(receipts_path=tmp_path/'micro_consolidation_reviews.jsonl',
                                      connections_path=ledger,db_path=tmp_path/'mneme_read_model.sqlite3')
    original=connections._open_read
    steps=[]
    def bounded(db):
        conn=original(db);counter=[0]
        def progress():
            counter[0]+=100;steps.append(100)
            return int(counter[0]>5000)
        conn.set_progress_handler(progress,100)
        return conn
    monkeypatch.setattr(connections,'_open_read',bounded)
    out=neighborhood(tmp_path,limit=2)
    assert out['ok'] and out['has_more'] and len(out['connections'])==2
    assert sum(steps)<10000


@pytest.mark.parametrize('alias',['direct','symlink','hardlink'])
@pytest.mark.parametrize('artifact',['receipts','db','capture','counter','config','annotations','pending','db-wal','db-journal','db-shm'])
def test_actual_configured_paths_are_protected_core_and_mcp(tmp_path,artifact,alias):
    state(tmp_path)
    custom=tmp_path/'custom';custom.mkdir()
    defaults={'receipts':tmp_path/'micro_consolidation_reviews.jsonl','db':tmp_path/'mneme_read_model.sqlite3',
              'capture':tmp_path/'memory_tags.jsonl','counter':tmp_path/'mneme_seq.json',
              'config':tmp_path/'config.toml','annotations':tmp_path/'claim_annotations.jsonl',
              'pending':tmp_path/'pending_review.json'}
    actual={k:custom/(k+'.file') for k in defaults}
    for name,path in actual.items():
        path.write_bytes(defaults[name].read_bytes() if defaults[name].exists() else b'')
    for suffix in ('wal','journal','shm'):
        (custom/('db.file-'+suffix)).write_bytes(b'auxiliary canary')
    target=custom/('db.file-'+artifact[3:]) if artifact.startswith('db-') else actual[artifact]
    destination=target
    if alias!='direct':
        destination=tmp_path/('alias-'+alias)
        if alias=='symlink':destination.symlink_to(target)
        else:os.link(target,destination)
    before=snapshot(tmp_path)
    kw=dict(state_dir=tmp_path,receipts_path=actual['receipts'],db_path=actual['db'],
            annotations_path=actual['annotations'],pending_review_path=actual['pending'],
            connections_path=destination,protected_paths=[actual['capture'],actual['counter'],actual['config']])
    out=connections.append_connection(source_review_id=B,target_review_id=A,
        relation_kind='corrects',relation_summary=MEANING,**kw)
    assert out['action']=='invalid_connection_request' and snapshot(tmp_path)==before
    server=create_server(state_dir=tmp_path,receipts_path=actual['receipts'],read_model_path=actual['db'],
        annotations_path=actual['annotations'],pending_review_path=actual['pending'],
        ledger_path=actual['capture'],state_path=actual['counter'],config_path=actual['config'],
        connections_path=destination)
    out=_call(server,'connect_items',{'source_review_id':B,'target_review_id':A,
              'relation_kind':'corrects','relation_summary':MEANING})
    assert out['action']=='invalid_connection_request' and snapshot(tmp_path)==before


def test_annotation_refresh_keeps_relation_and_updates_navigation(tmp_path):
    from mnion.annotations import append_claim_annotation
    state(tmp_path);edge=append(tmp_path)['connection']
    assert append_claim_annotation(exact_item_route=B,authored_claim='Changed entry, not a changed body.',state_dir=tmp_path)['ok']
    out=neighborhood(tmp_path)
    assert out['connections']==[edge]
    assert next(n['claim'] for n in out['nodes'] if n['review_id']==B)=='Changed entry, not a changed body.'


def test_depth_boundary_reports_witness_without_loading_next_body(tmp_path):
    state(tmp_path);append(tmp_path);append(tmp_path,C,B,'follows_from','An explicit dependency.')
    out=neighborhood(tmp_path,depth=1)
    assert {n['review_id'] for n in out['nodes']}=={A,B}
    assert len(out['connections'])==1 and out['has_more']


def test_post_projection_evidence_loss_is_not_success(tmp_path,monkeypatch):
    state(tmp_path)
    original=connections._open_read
    def remove_once(db):
        conn=original(db)
        # Remove after materialization; _fresh also uses this helper so wait for rows.
        try:
            present=conn.execute('SELECT COUNT(*) FROM mnion_connections').fetchone()[0]
        except sqlite3.Error:present=0
        if present:
            (tmp_path/'mnion_connections.jsonl').unlink(missing_ok=True)
        return conn
    monkeypatch.setattr(connections,'_open_read',remove_once)
    out=append(tmp_path)
    assert not out['ok'] and out['action']=='connection_recorded_projection_failed'
    assert out['retry_connection_id']==out['connection']['id']


@pytest.mark.parametrize('claim',['x'*241,b'not Unicode text'])
@pytest.mark.parametrize('route',[A,B])
def test_corrupt_navigation_claim_cannot_escape_bounded_reader(tmp_path,claim,route):
    state(tmp_path);append(tmp_path)
    with sqlite3.connect(tmp_path/'mneme_read_model.sqlite3') as db:
        db.execute('UPDATE mnion_items SET claim=? WHERE review_id=?',(claim,route))
    before=snapshot(tmp_path)
    out=neighborhood(tmp_path)
    assert not out['ok'], 'corrupt navigation escaped as a successful view'
    assert out['action']=='neighborhood_source_unavailable'
    assert snapshot(tmp_path)==before
