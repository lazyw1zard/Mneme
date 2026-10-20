"""Disposable independent QUALITY probes; never imports runtime state."""
from pathlib import Path
import json
import sqlite3
import pytest
import test_consolidation_neighbors as f
from mnion.mcp_server import create_server

@pytest.mark.parametrize('alias_kind', ['journal', 'hardlink', 'symlink'])
def test_combined_alias_preflight(tmp_path, alias_kind):
    server, got = f.pending(tmp_path)
    db=tmp_path/'mneme_read_model.sqlite3'
    connection=tmp_path/'edge-alias.jsonl'
    if alias_kind=='journal': connection=Path(str(db)+'-journal')
    elif alias_kind=='hardlink': connection.hardlink_to(tmp_path/'memory_tags.jsonl')
    else: connection.symlink_to(tmp_path/'memory_tags.jsonl')
    server=create_server(state_dir=tmp_path, config_path=tmp_path/'config.toml', connections_path=connection)
    protected=[tmp_path/'memory_tags.jsonl',tmp_path/'mneme_seq.json',tmp_path/'micro_consolidation_reviews.jsonl',tmp_path/'pending_review.json']
    before=[p.read_bytes() for p in protected]
    args=f.review_args(got);args['relations']=[f.relation()]
    result=f.call(server,'consolidate_review',args)
    assert not result['ok'],result
    assert [p.read_bytes() for p in protected]==before


def test_lazy_recovery_journal_alias_preserves_connection_evidence(tmp_path, monkeypatch):
    import mnion.connections as connections
    server, got=f.pending(tmp_path)
    args=f.review_args(got);args['relations']=[f.relation()]
    real=connections.materialize_connections
    def fail(**kw): raise ValueError('disposable initial fault')
    monkeypatch.setattr(connections,'materialize_connections',fail)
    first=f.call(server,'consolidate_review',args)
    assert first['action']=='review_recorded_read_model_failed',first
    monkeypatch.setattr(connections,'materialize_connections',real)
    receipts=tmp_path/'micro_consolidation_reviews.jsonl'
    written=json.loads(receipts.read_text().split('\n')[-2])
    external={**written['connections'][0], 'id':'connection_'+'a'*32,
              'source_review_id':'review_seed1','target_review_id':'review_seed2',
              'relation_summary':'External authored evidence must not be deleted.'}
    journal=Path(str(tmp_path/'mneme_read_model.sqlite3')+'-journal')
    journal.write_text(json.dumps(external)+'\n')
    before=journal.read_bytes()
    alias=create_server(state_dir=tmp_path,config_path=tmp_path/'config.toml',connections_path=journal)
    result=f.call(alias,'capture',{'delta':'Separate post-recovery observation.', 'valence':.2})
    print('LAZY_ALIAS',json.dumps({'result_ok':result['ok'],'action':result.get('action'),
           'journal_exists':journal.exists(),'pending_exists':(tmp_path/'pending_review.json').exists(),
           'evidence_preserved':journal.exists() and journal.read_bytes()==before}))
    assert journal.exists() and journal.read_bytes()==before

@pytest.mark.parametrize('bad', [True,1,'bad',{},[f.relation()]*9,
    [{**f.relation(),'mnion_index':1.0}], [{**f.relation(),'target_review_id':['review_seed2']}],
    [{**f.relation(),'relation_summary':'x'*1201}], [f.relation(),f.relation()]])
def test_invalid_relation_probes(tmp_path,bad):
    server,got=f.pending(tmp_path)
    protected=[tmp_path/'micro_consolidation_reviews.jsonl',tmp_path/'pending_review.json',tmp_path/'mneme_seq.json']
    before=[p.read_bytes() for p in protected]
    args=f.review_args(got);args['relations']=bad
    result=f.call(server,'consolidate_review',args)
    assert result['ok'] is False,result
    assert [p.read_bytes() for p in protected]==before


def test_candidate_migration_journal_alias_preserves_connection_evidence(tmp_path):
    f.seed(tmp_path,seqs=(1,8,9))
    (tmp_path/'mneme_seq.json').write_text('{"seq":10}')
    config=tmp_path/'config.toml'
    config.write_text('[review_pressure]\ncall_seq_interval=2\npacket_limit=2\n')
    db=tmp_path/'mneme_read_model.sqlite3'
    with sqlite3.connect(db) as conn:
        conn.execute('DROP INDEX mnion_items_call_seq')
        conn.execute('ALTER TABLE mnion_items DROP COLUMN consolidation_call_seq')
    external={'id':'connection_'+'b'*32,'source_review_id':'review_seed1',
              'target_review_id':'review_seed2','relation_kind':'continues',
              'relation_summary':'Preexisting authored evidence must remain intact.',
              'created_at':'2026-01-01T00:00:00Z','created_by':'agent'}
    journal=Path(str(db)+'-journal')
    journal.write_text(json.dumps(external)+'\n')
    before=journal.read_bytes()
    server=create_server(state_dir=tmp_path,config_path=config,connections_path=journal)
    f.call(server,'capture',{'delta':'Copper kettle observation.', 'valence':.8})
    result=f.call(server,'capture',{'delta':'Violet window observation.', 'valence':.8})
    print('ACQUISITION_ALIAS',json.dumps({'ok':result['ok'],'neighbors':result['review_packet'].get('neighbors'),
          'journal_exists':journal.exists(),'evidence_preserved':journal.exists() and journal.read_bytes()==before}))
    assert journal.exists() and journal.read_bytes()==before


def test_reverse_and_standalone_projection_merge(tmp_path):
    server,got=f.pending(tmp_path)
    args=f.review_args(got);args['relations']=[f.relation()]
    result=f.call(server,'consolidate_review',args)
    assert result['ok'],result
    reverse=f.call(server,'get_neighborhood',{'exact_item_route':'review_seed2'})
    assert reverse['connections']==result['connections'],reverse
    external=f.call(server,'connect_items', {'source_review_id':'review_seed1', 'target_review_id':'review_seed2',
       'relation_kind':'corrects','relation_summary':'A separate authored correction.'})
    assert external['ok'],external
    merged=f.call(server,'get_neighborhood',{'exact_item_route':'review_seed2'})
    assert {x['id'] for x in merged['connections']}=={result['connections'][0]['id'],external['connection']['id']}
