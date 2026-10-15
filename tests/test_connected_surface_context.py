import json
import pytest
from mnion.active_surface import load_active_surface_from_read_model
from mnion.connected_surface import routes_in_cue
from test_mnion_connections import A, B, C, state, append


@pytest.mark.parametrize('text,expected', [
    ('An unrelated ordinary message.', []),
    ('Please open `'+A+'`.', [A]),
    ('prefix'+A, []),
    (A+'junk', []),
    (A.replace(':mnion:1', ':mnion:0'), []),
    (A.replace(':mnion:1', ':mnion:1:extra'), []),
    ('Please return to '+A+'.', [A]),
    (A+'.not_an_address', []),
    (A+'..suffix', []),
    (A+' '+A, [A]),
])
def test_cue_uses_complete_addresses_not_keyword_similarity(text, expected):
    assert routes_in_cue(text) == expected


def test_low_valence_connected_root_can_enter_outside_static_top_routes(tmp_path):
    from mnion.read_model import materialize_mnion_items_sqlite
    d = 'review_' + 'd'*32 + ':mnion:1'
    state(tmp_path, routes=(A, B, C, d))
    receipts = tmp_path/'micro_consolidation_reviews.jsonl'
    rows = [json.loads(line) for line in receipts.read_text().splitlines()]
    rows[-1]['mnions'][0]['mnion']['valence'] = .01
    receipts.write_text(''.join(json.dumps(row)+'\n' for row in rows))
    path = tmp_path/'mneme_read_model.sqlite3'
    materialize_mnion_items_sqlite(receipts_path=receipts, db_path=path)
    append(tmp_path, source=d, target=A)
    result = load_active_surface_from_read_model(db_path=path)
    assert d not in [r for topic in result.topics for r in topic.top_review_ids]
    assert result.connected[0]['root_review_id'] == d


def test_ineligible_anchor_falls_back_to_recent_eligible_connection(tmp_path):
    import sqlite3
    d = 'review_'+'d'*32+':mnion:1'
    state(tmp_path, routes=(A, B, C, d))
    append(tmp_path, source=B, target=A)
    newer = append(tmp_path, source=d, target=C)['connection']
    path = tmp_path/'mneme_read_model.sqlite3'
    with sqlite3.connect(path) as conn:
        conn.execute('UPDATE mnion_items SET claim=NULL WHERE review_id=?', (A,))
    result = load_active_surface_from_read_model(db_path=path, anchor_routes=[A])
    assert len(result.connected) == 1
    assert result.connected[0]['connection']['id'] == newer['id']
    assert result.connected[0]['why_visible'] == 'recent_authored_connection'


def test_provider_passes_literal_cue_anchor_without_new_tools(monkeypatch, tmp_path):
    from test_hermes_memory_provider import _load_provider_module
    state(tmp_path)
    older = append(tmp_path, source=B, target=A)['connection']
    newer = append(tmp_path, source=C, target=B)['connection']
    module = _load_provider_module(monkeypatch, tmp_path)
    provider = module.MnemeMemoryProvider({'read_model_path': str(tmp_path/'mneme_read_model.sqlite3')})
    assert newer['id'] in provider.prefetch('unrelated words', session_id='fixture')
    output = provider.prefetch('Return to `'+A+'`', session_id='fixture')
    assert older['id'] in output and 'explicit_route_in_cue' in output
    assert provider.get_tool_schemas() == []
