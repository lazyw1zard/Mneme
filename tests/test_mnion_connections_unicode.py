"""Valid authored Unicode is data, never a physical JSONL record boundary."""
import json
import pytest
from mnion import connections
from mnion.mcp_server import create_server
from test_mnion_connections import A,B,C,state,snapshot,append,neighborhood
from test_mnion_claims import _call


@pytest.mark.parametrize('separator',['\u0085','\u2028','\u2029'])
def test_unicode_separator_roundtrip_retry_and_later_authorship(tmp_path,separator):
    state(tmp_path)
    originals={name:(tmp_path/name).read_bytes() for name in
               ('micro_consolidation_reviews.jsonl','memory_tags.jsonl','mneme_seq.json','config.toml')}
    meaning='A correction'+separator+'with literally preserved Unicode wording.'
    recorded=append(tmp_path,meaning=meaning)
    assert recorded['ok'], 'valid Unicode authored text must not poison evidence after append'
    edge=recorded['connection']
    assert edge['relation_summary']==meaning
    raw=(tmp_path/'mnion_connections.jsonl').read_bytes()
    assert separator.encode('utf-8') in raw and raw.count(b'\n')==1
    assert connections.load_connections(tmp_path/'mnion_connections.jsonl')==[edge]
    assert json.loads(raw)['relation_summary']==meaning
    before=snapshot(tmp_path)
    retry=append(tmp_path,meaning=meaning,retry_connection_id=edge['id'])
    assert retry['ok'] and retry['reused_connection'] and snapshot(tmp_path)==before
    later=append(tmp_path,C,B,'follows_from','A subsequent deliberate relation.')
    assert later['ok']
    stable=snapshot(tmp_path)
    view=neighborhood(tmp_path,depth=2)
    assert view['ok'] and view['connections']==[edge,later['connection']]
    assert snapshot(tmp_path)==stable
    for name,body in originals.items():assert (tmp_path/name).read_bytes()==body


@pytest.mark.parametrize('separator',['\u0085','\u2028','\u2029'])
def test_unicode_separator_portable_mcp_surface(tmp_path,separator):
    state(tmp_path)
    server=create_server(state_dir=tmp_path,config_path=tmp_path/'config.toml')
    wording='Authored correction'+separator+'must remain literally unchanged.'
    args={'source_review_id':B,'target_review_id':A,'relation_kind':'corrects','relation_summary':wording}
    recorded=_call(server,'connect_items',args)
    assert recorded['ok'], 'MCP must preserve valid Unicode text through source and projection'
    before=snapshot(tmp_path)
    retry=_call(server,'connect_items',{**args,'retry_connection_id':recorded['connection']['id']})
    assert retry['ok'] and retry['reused_connection']
    view=_call(server,'get_neighborhood',{'exact_item_route':A,'depth':1,'limit':4})
    assert view['ok'] and view['connections']==[recorded['connection']]
    assert view['connections'][0]['relation_summary']==wording
    assert snapshot(tmp_path)==before
