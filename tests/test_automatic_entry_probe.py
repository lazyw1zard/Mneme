"""Neutral offline fixtures, not samples from anyone's memory."""
import copy
import json
from pathlib import Path
import runpy
import subprocess
import sys

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / 'docs/experiments/automatic-entry-candidates/probe.py'


def api():
    return runpy.run_path(str(SCRIPT))


def item(n, text, tick=10, sources=()):
    return {'review_id': f'review_{n:032x}:mnion:1',
            'mnion': {'summary': text, 'claim': None, 'valence': 0.5, 'rationale': None},
            'grouped_ids': list(sources), 'receipt': {'mneme_call_seq': tick}}


def build(items, **config):
    return api()['build'](items, **config)


def test_automatic_entry_requires_no_authored_cue_and_keeps_bodies_out():
    items = [item(1, 'Queue cursor checkpoint preserves pending records.'),
             item(2, 'Queue cursor checkpoint resumes pending records.', 12)]
    before = copy.deepcopy(items)
    graph = build(items)
    assert graph['edges'] and graph['entries']
    edge = graph['edges'][0]
    assert edge['kind'] == 'association_candidate'
    assert edge['evidence']['call_gap'] == 2
    assert edge['evidence']['text_similarity'] > 0
    assert len(edge['evidence']['shared_terms']) >= 2
    assert items == before
    assert 'Queue cursor checkpoint preserves' not in json.dumps(graph)
    assert all(e['status'] == 'candidate' for e in graph['entries'])


def test_time_without_content_does_not_link():
    assert not build([item(1, 'Queue cursor checkpoint'), item(2, 'Orchard blossom petals')])['entries']


def test_same_text_outside_window_does_not_link_in_this_local_probe():
    assert not build([item(1, 'Queue cursor checkpoint'), item(2, 'Queue cursor checkpoint', 80)])['edges']


def test_missing_clock_is_not_repaired_to_zero():
    graph = build([item(1, 'Queue cursor checkpoint', None), item(2, 'Queue cursor checkpoint')])
    assert not graph['edges']
    assert graph['coverage']['unknown_clock_items'] == 1


def test_shared_source_is_distinct_from_semantic_relation():
    graph = build([item(1, 'Queue checkpoint', sources=['tag_shared']),
                   item(2, 'Orchard petals', sources=['tag_shared'])])
    edge = graph['edges'][0]
    assert edge['evidence']['shared_source_ids'] == ['tag_shared']
    assert edge['kind'] == 'association_candidate'
    assert not graph['authored_relations']


def test_chain_does_not_become_one_three_member_branch():
    graph = build([item(1, 'queue cursor checkpoint'),
                   item(2, 'queue cursor checkpoint orchard blossom petals'),
                   item(3, 'orchard blossom petals')])
    assert len(graph['edges']) == 2
    groups = {frozenset(e['member_routes']) for e in graph['entries']}
    assert len(groups) == 2
    assert all(len(group) == 2 for group in groups)
    assert item(2, '')['review_id'] in set.intersection(*(set(g) for g in groups))


def test_same_members_merge_seed_aliases_without_losing_entry_route():
    first = build([item(1, 'Queue cursor checkpoint'), item(2, 'Queue cursor checkpoint')])
    address = first['entries'][0]['id']
    grown = build([item(1, 'Queue cursor checkpoint'), item(2, 'Queue cursor checkpoint'),
                   item(3, 'Queue cursor checkpoint')])
    opened = api()['resolve'](grown, address)
    assert len(opened['member_routes']) == 3
    assert len(grown['entries']) == 1
    assert len(grown['entries'][0]['aliases']) == 3
    assert api()['resolve'](grown, 'entry_' + 'f' * 64) is None


def test_input_order_does_not_change_map_or_pointer_identity():
    items = [item(1, 'Queue cursor checkpoint'), item(2, 'Queue cursor checkpoint'),
             item(3, 'Queue cursor checkpoint')]
    assert build(items) == build(list(reversed(items)))


def test_neighbor_budget_is_real_and_reports_discarded_edges():
    graph = build([item(n, 'Queue cursor checkpoint') for n in range(1, 8)], max_neighbors=2)
    degree = {}
    for edge in graph['edges']:
        for route in edge['endpoints']:
            degree[route] = degree.get(route, 0) + 1
    assert max(degree.values()) <= 2
    assert graph['coverage']['discarded_by_degree_limit'] > 0
    assert graph['coverage']['partial'] is True


def test_partial_candidate_window_is_not_declared_complete_history():
    graph = build([item(1, 'Queue cursor checkpoint')])
    assert graph['coverage']['scope'] == 'explicit_input_only'
    assert graph['coverage']['history_complete'] is False
    assert graph['coverage']['semantic_agreement_verified'] is False


@pytest.mark.parametrize('bad', [True, -1, '10', 1.2])
def test_invalid_clocks_rejected(bad):
    with pytest.raises(ValueError):
        build([item(1, 'Queue cursor checkpoint', bad)])


@pytest.mark.parametrize('config', [{'window_calls': True}, {'window_calls': -1},
                                   {'max_neighbors': 0}, {'max_neighbors': 9},
                                   {'min_similarity': float('nan')}, {'min_similarity': True},
                                   {'min_shared_terms': 0}])
def test_invalid_config_rejected(config):
    with pytest.raises(ValueError):
        build([], **config)


def test_wrong_exact_route_is_rejected_not_repaired():
    bad = item(1, 'Queue cursor checkpoint')
    bad['review_id'] += ' '
    with pytest.raises(ValueError):
        build([bad])


def test_duplicate_routes_rejected():
    with pytest.raises(ValueError):
        build([item(1, 'Queue cursor checkpoint'), item(1, 'Orchard blossom petals')])


def test_input_bound_rejects_instead_of_silent_truncation():
    with pytest.raises(ValueError):
        build([item(n, 'Queue cursor checkpoint') for n in range(257)])


def test_russian_content_and_unicode_are_supported():
    graph = build([item(1, 'Очередь сохраняет курсор проверки и контрольную точку.'),
                   item(2, 'Очередь возобновляет курсор проверки через контрольную точку.', 11)])
    assert graph['entries']
    assert any('курсор' in e['evidence']['shared_terms'] for e in graph['edges'])


def test_generic_shared_words_do_not_establish_link():
    assert not build([item(1, 'Это память о том как мы меняем очередь'),
                      item(2, 'Это память о том как мы видим море')])['edges']


def test_contradictory_text_is_only_association_not_agreement():
    graph = build([item(1, 'Queue cursor checkpoint must persist.'),
                   item(2, 'Queue cursor checkpoint must NOT persist.')])
    assert graph['entries']
    assert graph['coverage']['semantic_agreement_verified'] is False
    assert all(e['kind'] == 'association_candidate' for e in graph['edges'])


def test_cli_build_reopen_item_and_no_source_mutation(tmp_path):
    source, mapped = tmp_path/'items.json', tmp_path/'map.json'
    items = [item(1, 'Queue cursor checkpoint'), item(2, 'Queue cursor checkpoint', 11)]
    source.write_text(json.dumps({'items': items}))
    before = source.read_bytes()
    result = subprocess.run([sys.executable, str(SCRIPT), 'build', str(source)],
                            capture_output=True, text=True, check=True)
    graph = json.loads(result.stdout)
    mapped.write_text(result.stdout)
    opened = subprocess.run([sys.executable, str(SCRIPT), 'open', str(mapped),
                             '--entry', graph['entries'][0]['id']],
                            capture_output=True, text=True, check=True)
    assert json.loads(opened.stdout)['member_routes'] == graph['entries'][0]['member_routes']
    original = subprocess.run([sys.executable, str(SCRIPT), 'item', str(source),
                               '--route', items[0]['review_id']],
                              capture_output=True, text=True, check=True)
    assert json.loads(original.stdout) == items[0]
    assert source.read_bytes() == before
    assert sorted(p.name for p in tmp_path.iterdir()) == ['items.json', 'map.json']


def test_cli_missing_pointer_is_explicit(tmp_path):
    path = tmp_path/'map.json'
    path.write_text(json.dumps(build([])))
    result = subprocess.run([sys.executable, str(SCRIPT), 'open', str(path),
                             '--entry', 'entry_'+'f'*64], capture_output=True, text=True)
    assert result.returncode == 3
    assert json.loads(result.stdout)['status'] == 'not_found'


def test_cli_duplicate_json_keys_fail_closed(tmp_path):
    path = tmp_path/'bad.json'
    path.write_text('{"items": [], "items": []}')
    result = subprocess.run([sys.executable, str(SCRIPT), 'build', str(path)],
                            capture_output=True, text=True)
    assert result.returncode == 2
    assert not result.stdout


def test_source_only_candidate_can_be_route_only_not_invented_cue():
    graph = build([item(1, 'Queue checkpoint', sources=['tag_shared']),
                   item(2, 'Orchard petals', sources=['tag_shared'])])
    assert graph['entries'][0]['cue'] == {'shared_terms': [], 'claims': []}


def test_removed_seed_returns_missing_not_similar_candidate():
    first = build([item(1, 'Queue cursor checkpoint'), item(2, 'Queue cursor checkpoint')])
    later = build([item(1, 'Queue cursor checkpoint'), item(3, 'Queue cursor checkpoint')])
    assert later['entries']
    assert api()['resolve'](later, first['entries'][0]['id']) is None


def test_cli_oversized_input_fails_without_echoing_source(tmp_path):
    path = tmp_path/'huge.json'
    path.write_bytes(b' ' * (api()['MAX_BYTES']+1))
    result = subprocess.run([sys.executable, str(SCRIPT), 'build', str(path)],
                            capture_output=True, text=True)
    assert result.returncode == 2
    assert not result.stdout
    assert 'Traceback' not in result.stderr


def test_unknown_clock_coverage_is_separate_from_degree_pruning():
    graph = build([item(1, 'Queue cursor checkpoint', None)])
    assert graph['coverage']['partial'] is False
    assert graph['coverage']['unknown_clock_items'] == 1
    assert graph['coverage']['history_complete'] is False


def test_cli_long_shared_terms_map_can_be_reopened(tmp_path):
    source, mapped = tmp_path/'long-items.json', tmp_path/'long-map.json'
    text = 'a'*8000 + ' ' + 'b'*8000
    items = [item(n, text) for n in range(256)]
    source.write_text(json.dumps({'items': items}))
    before = source.read_bytes()
    result = subprocess.run([sys.executable, str(SCRIPT), 'build', str(source)],
                            capture_output=True, text=True, check=True)
    assert len(result.stdout.encode()) <= api()['MAX_BYTES']
    graph = json.loads(result.stdout)
    assert graph['entries']
    assert all(e['evidence']['shared_terms_abbreviated'] for e in graph['edges'])
    assert max(len(t) for e in graph['edges'] for t in e['evidence']['shared_terms']) <= 64
    mapped.write_text(result.stdout)
    reopened = subprocess.run([sys.executable, str(SCRIPT), 'open', str(mapped),
                               '--entry', graph['entries'][0]['id']],
                              capture_output=True, text=True, check=True)
    assert json.loads(reopened.stdout)['id'] == graph['entries'][0]['id']
    assert source.read_bytes() == before


def test_serialized_output_bound_counts_utf8_bytes_and_newline():
    encode = api()['encode_output']
    with pytest.raises(ValueError):
        encode({'payload': '界'*(api()['MAX_BYTES']//3)})
    assert json.loads(encode({'payload': '界'})) == {'payload': '界'}


def test_overlong_exact_route_rejected_not_truncated():
    value = item(1, 'Queue cursor checkpoint')
    value['review_id'] = 'review_'+'a'*32+':mnion:'+'1'*300
    with pytest.raises(ValueError):
        build([value])


def test_same_abbreviated_prefix_does_not_become_full_token_match():
    graph = build([item(1, 'x'*100+'alpha cursor'),
                   item(2, 'x'*100+'bravo cursor')])
    assert not graph['edges']


def test_exact_serialized_byte_boundary_includes_utf8_and_lf():
    module = api()
    encode, limit = module['encode_output'], module['MAX_BYTES']
    framing = len(encode({'payload': ''}).encode('utf-8'))
    count, remainder = divmod(limit-framing, len('界'.encode('utf-8')))
    payload = '界'*count+'a'*remainder
    assert len(encode({'payload': payload}).encode('utf-8')) == limit
    with pytest.raises(ValueError):
        encode({'payload': payload+'a'})
