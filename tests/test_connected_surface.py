"""I can recognize an authored change before choosing to open its history."""
import json
import sqlite3
import time

import pytest
from mnion.active_surface import load_active_surface_from_read_model
from test_mnion_connections import A, B, C, state, append, snapshot


def load(path, **kwargs):
    return load_active_surface_from_read_model(db_path=path / 'mneme_read_model.sqlite3', **kwargs)


def test_connected_entrance_preserves_exact_nodes_direction_and_retrieval(tmp_path):
    state(tmp_path)
    edge = append(tmp_path, source=B, target=A, meaning='A correction changed my next choice.')['connection']
    before = snapshot(tmp_path)
    result = load(tmp_path)
    assert len(result.connected) == 1
    hint = result.connected[0]
    assert hint['why_visible'] == 'recent_authored_connection'
    assert hint['root_review_id'] == B
    assert hint['connection']['id'] == edge['id']
    assert hint['connection']['source_review_id'] == B
    assert hint['connection']['target_review_id'] == A
    assert hint['nodes'] == [{'review_id': B, 'claim': 'Entry 1'}, {'review_id': A, 'claim': 'Entry 0'}]
    assert hint['retrieval'] == {'tool': 'get_neighborhood', 'exact_item_route': B, 'depth': 1, 'limit': 4}
    assert 'connected_entrance: ' in result.rendered
    assert 'get_item' in result.rendered and 'get_neighborhood' in result.rendered
    assert 'Original grounds' not in result.rendered
    assert 'Original 1' not in result.rendered
    assert before == snapshot(tmp_path)


def test_explicit_anchor_beats_later_unrelated_connection(tmp_path):
    state(tmp_path)
    older = append(tmp_path, source=B, target=A)['connection']
    newer = append(tmp_path, source=C, target=B)['connection']
    assert load(tmp_path).connected[0]['connection']['id'] == newer['id']
    hint = load(tmp_path, anchor_routes=[A]).connected[0]
    assert hint['connection']['id'] == older['id']
    assert hint['root_review_id'] == A
    assert hint['why_visible'] == 'explicit_route_in_cue'
    assert hint['connection']['source_review_id'] == B  # never reverse the authored edge


def test_old_schema_is_optional_graph_unavailable_not_no_memory(tmp_path):
    state(tmp_path)
    result = load(tmp_path)
    assert result.topics and result.rendered
    assert result.connected == []
    assert result.connections_status == 'unavailable'


def test_available_zero_edges_is_honest_empty_snapshot(tmp_path):
    state(tmp_path)
    from mnion.connections import materialize_connections
    materialize_connections(receipts_path=tmp_path/'micro_consolidation_reviews.jsonl',
                            connections_path=tmp_path/'mnion_connections.jsonl',
                            db_path=tmp_path/'mneme_read_model.sqlite3')
    result = load(tmp_path)
    assert result.connections_status == 'ok' and result.connected == []
    assert result.topics


@pytest.mark.parametrize('damage', ['bad_json', 'deep_json', 'wrong_endpoint', 'no_claim'])
def test_unusable_graph_does_not_break_topic_fallback(tmp_path, damage):
    state(tmp_path)
    append(tmp_path)
    with sqlite3.connect(tmp_path/'mneme_read_model.sqlite3') as conn:
        if damage == 'bad_json':
            conn.execute("UPDATE mnion_connections SET payload_json='{' ")
        elif damage == 'deep_json':
            conn.execute('UPDATE mnion_connections SET payload_json=?', ('['*1500+'0'+']'*1500,))
        elif damage == 'wrong_endpoint':
            row = conn.execute('SELECT payload_json FROM mnion_connections').fetchone()
            edge = json.loads(row[0]); edge['source_review_id'] = C
            conn.execute('UPDATE mnion_connections SET payload_json=?', (json.dumps(edge),))
        else:
            conn.execute('UPDATE mnion_items SET claim=NULL WHERE review_id=?', (A,))
    before = snapshot(tmp_path)
    result = load(tmp_path)
    assert result.topics and not result.connected
    assert result.connections_status == 'unavailable'
    assert before == snapshot(tmp_path)


def test_summary_is_only_a_named_bounded_preview(tmp_path):
    state(tmp_path)
    text = 'Основание 🧭 ' * 75
    append(tmp_path, meaning=text)
    hint = load(tmp_path).connected[0]
    assert hint['connection']['summary_preview'] == text[:219] + '…'
    assert 'relation_summary' not in hint['connection']
    assert len(hint['connection']['summary_preview']) <= 220


def test_pure_assembler_caps_connected_entrances(tmp_path):
    from mnion.active_surface import assemble_active_surface
    state(tmp_path); append(tmp_path)
    result = load(tmp_path)
    hint = result.connected[0]
    assembled = assemble_active_surface(topics=result.topics, connected=[hint]*8, connections_status='ok')
    assert len(assembled.connected) == 1
    assert assembled.rendered.count('connected_entrance: ') == 1


def test_locked_and_missing_sources_do_not_write_or_hang(tmp_path):
    missing = tmp_path/'missing'/'db.sqlite3'
    result = load_active_surface_from_read_model(db_path=missing)
    assert not missing.parent.exists() and result.source_status == 'unavailable'
    state(tmp_path); append(tmp_path)
    before = snapshot(tmp_path)
    conn = sqlite3.connect(tmp_path/'mneme_read_model.sqlite3')
    try:
        conn.execute('BEGIN EXCLUSIVE')
        start = time.monotonic(); result = load(tmp_path)
        assert time.monotonic() - start < .5
        assert result.source_status == 'unavailable'
    finally:
        conn.rollback(); conn.close()
    assert before == snapshot(tmp_path)


def test_exact_anchor_validation_is_literal_not_normalized(tmp_path):
    state(tmp_path); append(tmp_path)
    for bad in [' '+A, A+'junk', A.split(':')[0]+':mnion:0']:
        with pytest.raises(ValueError):
            load(tmp_path, anchor_routes=[bad])


def test_index_ranges_bound_work_for_large_degree(tmp_path, monkeypatch):
    state(tmp_path); append(tmp_path)
    path = tmp_path/'mneme_read_model.sqlite3'
    with sqlite3.connect(path) as conn:
        template = json.loads(conn.execute('SELECT payload_json FROM mnion_connections').fetchone()[0])
        for i in range(1, 5001):
            edge = dict(template, id=f'connection_{i:032x}')
            conn.execute('INSERT INTO mnion_connections (id,seq,source_review_id,target_review_id,payload_json) '
                         'VALUES (?,?,?,?,?)', (edge['id'],i, B,A,json.dumps(edge)))
    import mnion.active_surface as surface
    original = surface.sqlite3.connect
    instructions = [0]
    def bounded(*args, **kwargs):
        conn = original(*args, **kwargs)
        def progress():
            instructions[0] += 1
            return instructions[0] > 40  # 4000 VM instructions including topic fallback
        conn.set_progress_handler(progress, 100)
        return conn
    monkeypatch.setattr(surface.sqlite3, 'connect', bounded)
    result = load(tmp_path, anchor_routes=[A])
    assert len(result.connected) == 1
    assert result.connected[0]['why_visible'] == 'explicit_route_in_cue'
    assert instructions[0] <= 40
