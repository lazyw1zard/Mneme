"""Exploratory entry-map contract; no new production pointer schema or live corpus."""
import json

import pytest

from mnion.connections import append_connection, get_neighborhood
from mnion.read_model import materialize_mnion_items_sqlite


@pytest.fixture
def graph(tmp_path):
    # All nodes exist before the tests; edges are explicitly authored in disposable state.
    receipts = tmp_path / 'micro_consolidation_reviews.jsonl'
    rows = [{'id': f'review_probe{i}', 'mneme_call_seq': i,
             'created_at': '2026-01-01T00:00:00Z', 'grouped_ids': [f'tag_probe{i}'],
             'mnion': {'summary': f'BODY_ONLY_{i}: standalone original; do not preload.',
                       'valence': .5, 'claim': f'Separate understanding {i}'}}
            for i in range(5)]
    receipts.write_text(''.join(json.dumps(x)+'\n' for x in rows))
    materialize_mnion_items_sqlite(receipts_path=receipts, db_path=tmp_path/'mneme_read_model.sqlite3')
    def link(source, target, kind='continues'):
        result = append_connection(source_review_id=f'review_probe{source}',
            target_review_id=f'review_probe{target}', relation_kind=kind,
            relation_summary=f'Authored fixture {source} {kind} {target}; not inferred from dates.',
            state_dir=tmp_path)
        assert result['ok'], result
        return result['connection']
    link(1, 0)
    link(2, 0, 'follows_from')
    # Deliberately hand-authored sketch, not a new production Metapointer class.
    entry = {'knows': 'I know the alternatives behind this understanding.',
             'route': {'action': 'get_neighborhood', 'exact_item_route': 'review_probe0'}}
    return tmp_path, receipts, link, entry


def test_entry_is_not_a_story_or_automatic_expansion(graph):
    root, receipts, _, entry = graph
    before = {p: p.read_bytes() for p in root.iterdir() if p.is_file()}
    serialized = json.dumps(entry)
    assert 'BODY_ONLY' not in serialized
    assert 'nodes' not in entry and 'connections' not in entry
    assert {p: p.read_bytes() for p in before} == before
    print(json.dumps({'stage': 'entrance_only', 'body_preload': False,
                      'automatic_graph_expansion': False}))


def test_explicit_expansion_keeps_branches_and_originals(graph):
    root, receipts, _, entry = graph
    before = receipts.read_bytes()
    arc = get_neighborhood(state_dir=root, depth=1, limit=4,
                          exact_item_route=entry['route']['exact_item_route'])
    assert arc['ok'] and not arc['has_more']
    assert {n['review_id'] for n in arc['nodes']} == {'review_probe0','review_probe1','review_probe2'}
    assert {(e['source_review_id'],e['target_review_id']) for e in arc['connections']} == {
        ('review_probe1','review_probe0'), ('review_probe2','review_probe0')}
    assert 'BODY_ONLY' not in json.dumps(arc)
    assert receipts.read_bytes() == before
    print(json.dumps({'stage': 'chosen_expansion', 'branch_preservation': True,
                      'body_preload': False, 'receipts_unchanged': True}))


def test_same_entry_discovers_later_continuation(graph):
    root, receipts, link, entry = graph
    frozen_entry, before = json.dumps(entry, sort_keys=True), receipts.read_bytes()
    link(3, 1)
    arc = get_neighborhood(state_dir=root, exact_item_route='review_probe0', depth=2, limit=4)
    assert arc['ok'] and not arc['has_more']
    assert 'review_probe3' in {n['review_id'] for n in arc['nodes']}
    assert json.dumps(entry, sort_keys=True) == frozen_entry
    assert receipts.read_bytes() == before
    print(json.dumps({'stage': 'later_continuation', 'same_entry': True,
                      'new_route_discovered': True, 'semantic_entry_refresh_proved': False}))


def test_one_correction_can_hide_behind_older_edges_and_budget(graph):
    root, receipts, link, entry = graph
    frozen_entry, before = json.dumps(entry, sort_keys=True), receipts.read_bytes()
    correction = link(4, 0, 'corrects')
    limited = get_neighborhood(state_dir=root, exact_item_route='review_probe0', depth=1, limit=2)
    assert limited['ok'] and limited['has_more']
    assert correction['id'] not in {e['id'] for e in limited['connections']}
    # The graph is not missing the correction: current oldest-first truncation hides it.
    larger = get_neighborhood(state_dir=root, exact_item_route='review_probe0', depth=1, limit=4)
    assert correction['id'] in {e['id'] for e in larger['connections']}
    alternate = get_neighborhood(state_dir=root, exact_item_route='review_probe4', depth=1, limit=1)
    assert alternate['ok'] and alternate['connections'] == [correction]
    assert json.dumps(entry, sort_keys=True) == frozen_entry
    assert receipts.read_bytes() == before
    print(json.dumps({'stage': 'single_new_correction', 'hidden_at_old_budget': True,
                      'truncation_witness': limited['has_more'], 'alternate_exact_route_works': True,
                      'freshness_does_not_prove_semantic_adequacy': True}))
