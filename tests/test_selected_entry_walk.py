"""TDD for an experimental selected walk, not a production pointer schema."""
import copy
import importlib.util
from pathlib import Path

import pytest

PATH = Path(__file__).resolve().parents[1] / 'docs/experiments/metapointer-entry-map/selected_walk.py'


@pytest.fixture
def walk():
    assert PATH.exists(), 'Missing selected-walk experiment: expected TDD RED'
    spec = importlib.util.spec_from_file_location('selected_walk', PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def evidence():
    entry = {'knows': 'I know a grounded choice and its continuation.',
             'route': {'action': 'get_neighborhood', 'exact_item_route': 'review_fixture0'}}
    view = {'ok': True, 'root_review_id': 'review_fixture0',
            'nodes': [{'review_id': 'review_fixture0', 'claim': 'origin'},
                      {'review_id': 'review_fixture1', 'claim': 'first branch'},
                      {'review_id': 'review_fixture2', 'claim': 'other branch'}],
            'connections': [{'id': 'fixture-edge', 'source_review_id': 'review_fixture1',
                             'target_review_id': 'review_fixture0', 'relation_kind': 'follows_from',
                             'relation_summary': 'Explicit grounds, not topic similarity.'}],
            'has_more': True}
    return entry, view


def test_expansion_is_explicit_and_does_not_open_bodies(walk, evidence):
    entry, view = evidence
    before = copy.deepcopy(evidence)
    calls = []
    def read(route, *, depth, limit):
        calls.append((route, depth, limit))
        return view
    opened = walk.expand_entry(entry, read, depth=1, limit=3)
    assert calls == [('review_fixture0', 1, 3)]
    assert opened == view and opened['has_more'] is True
    opened['nodes'].clear()
    assert evidence == before


@pytest.mark.parametrize('route', [' review_fixture0', 'review_fixture0 ', '', None])
def test_bad_entry_rejected_before_read(walk, evidence, route):
    entry, _ = evidence
    entry['route']['exact_item_route'] = route
    with pytest.raises(ValueError):
        walk.expand_entry(entry, lambda *a, **k: pytest.fail('must not read'))


@pytest.mark.parametrize('depth,limit', [(True, 3), (0, 3), (3, 3), (1, True), (1, 0), (1, 9)])
def test_expansion_bounds_are_literal(walk, evidence, depth, limit):
    with pytest.raises(ValueError):
        walk.expand_entry(evidence[0], lambda *a, **k: pytest.fail('must not read'), depth=depth, limit=limit)


def test_wrong_root_and_unavailable_view_reject(walk, evidence):
    for result in ({'ok': False, 'reason': 'unavailable'}, dict(evidence[1], root_review_id='review_fixture9')):
        with pytest.raises(ValueError):
            walk.expand_entry(evidence[0], lambda *a, **k: result)


def test_selected_originals_are_separate_exact_and_unchanged(walk, evidence):
    calls = []
    item = {'ok': True, 'item': {'review_id': 'review_fixture1',
            'mnion': {'summary': 'INTACT original text', 'valence': .6, 'rationale': 'original grounds'},
            'grouped_ids': ['tag_fixture'], 'created_at': 'fixture-time'}}
    original = copy.deepcopy(item)
    def read(route):
        calls.append(route)
        return item
    result = walk.open_selected(evidence[1], ['review_fixture1'], read)
    assert calls == ['review_fixture1'] and result == [item]
    result[0]['item']['mnion']['summary'] = 'modified result'
    assert item == original


@pytest.mark.parametrize('routes', [['review_fixture9'], ['review_fixture1', ' review_fixture2'],
                                   ['review_fixture1', 'review_fixture1'], 'review_fixture1'])
def test_entire_selection_validated_before_any_body_read(walk, evidence, routes):
    with pytest.raises(ValueError):
        walk.open_selected(evidence[1], routes, lambda *a: pytest.fail('must not read'))


def test_no_selection_is_a_valid_no_body_path(walk, evidence):
    assert walk.open_selected(evidence[1], [], lambda *a: pytest.fail('must not read')) == []


def test_wrong_item_or_failed_return_is_not_success(walk, evidence):
    for result in ({'ok': False}, {'ok': True, 'item': {'review_id': 'review_fixture2'}}):
        with pytest.raises(ValueError):
            walk.open_selected(evidence[1], ['review_fixture1'], lambda *a: result)


def test_selection_cap_is_explicit_and_precedes_reads(walk, evidence):
    with pytest.raises(ValueError):
        walk.open_selected(evidence[1], ['review_fixture0', 'review_fixture1'],
                           lambda *a: pytest.fail('must not read'), max_originals=1)
    with pytest.raises(ValueError):
        walk.open_selected(evidence[1], [], lambda *a: pytest.fail('must not read'), max_originals=True)
