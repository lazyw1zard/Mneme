"""Later navigation authorship preserves the original memory artifact."""
import importlib
import json
import sqlite3
from dataclasses import asdict

import pytest

from mnion.active_surface import load_active_surface_from_read_model
from mnion.mcp_server import create_server
from mnion.read_model import (ensure_read_model_fresh, get_item, materialize_mnion_items_sqlite,
                              read_model_freshness)
from test_mnion_claims import INVALID, _call
from test_mcp_adapter import input_schema, run

CLAIM = '  Позднее понимание: original memory remains intact. 🧠  '
ROUTE = 'review_abcdef0123456789abcdef0123456789:mnion:1'
NEIGHBOR = ROUTE[:-1] + '10'


def _api():
    spec = importlib.util.find_spec('mnion.annotations')
    assert spec is not None, 'append-only annotation core is missing'
    return importlib.import_module('mnion.annotations')


def _state(tmp_path, packet=True, project=True):
    tmp_path.mkdir(parents=True, exist_ok=True)
    body = {'summary': 'hidden original body', 'rationale': 'hidden rationale',
            'valence': .8, 'claim': 'Original entry.'}
    receipt = {'id': ROUTE.split(':')[0] if packet else 'review_single',
               'created_at': '2020-01-01T00:00:00Z', 'grouped_ids': ['tag_a']}
    if packet:
        receipt['mnions'] = [{'review_id': ROUTE, 'mnion': body, 'grouped_ids': ['tag_a']},
                             {'review_id': NEIGHBOR, 'mnion': dict(body, claim='Neighbor entry.'),
                              'grouped_ids': ['tag_b']}]
    else:
        receipt['mnion'] = body
    receipts = tmp_path / 'micro_consolidation_reviews.jsonl'
    receipts.write_text(json.dumps(receipt) + '\n', encoding='utf-8')
    (tmp_path / 'mneme_seq.json').write_text('{"seq":17}\n')
    (tmp_path / 'memory_tags.jsonl').write_text('original captures\n')
    (tmp_path / 'config.toml').write_text('')
    if project:
        materialize_mnion_items_sqlite(receipts_path=receipts, db_path=tmp_path / 'mneme_read_model.sqlite3')
    return ROUTE if packet else 'review_single'


def _snapshot(tmp_path):
    return {str(p.relative_to(tmp_path)): (p.read_bytes(), p.stat().st_mtime_ns)
            for p in tmp_path.rglob('*') if p.is_file()}


def _append(tmp_path, route=ROUTE, claim=CLAIM, **kwargs):
    return _api().append_claim_annotation(exact_item_route=route, authored_claim=claim,
                                          state_dir=tmp_path, **kwargs)


def _model_args(tmp_path):
    return {'receipts_path': tmp_path / 'micro_consolidation_reviews.jsonl',
            'db_path': tmp_path / 'mneme_read_model.sqlite3',
            'annotations_path': tmp_path / 'claim_annotations.jsonl'}


@pytest.mark.parametrize('packet', [False, True])
def test_append_projects_exact_claim_with_later_provenance_preserving_sources(tmp_path, packet):
    route = _state(tmp_path, packet)
    source_before = _snapshot(tmp_path)
    neighbor_before = asdict(get_item(review_id=NEIGHBOR, db_path=tmp_path / 'mneme_read_model.sqlite3')) if packet else None
    result = _append(tmp_path, route)
    assert result['ok'] and result['action'] == 'claim_annotation_recorded'
    annotation = result['annotation']
    assert annotation['id'].startswith('annotation_')
    assert annotation['route'] == route and annotation['claim'] == CLAIM and annotation['created_at']
    assert json.loads((tmp_path / 'claim_annotations.jsonl').read_text()) == annotation
    for name, before in source_before.items():
        if name != 'mneme_read_model.sqlite3':
            assert _snapshot(tmp_path)[name] == before
    item = get_item(review_id=route, db_path=tmp_path / 'mneme_read_model.sqlite3')
    assert item.mnion.claim == CLAIM
    assert item.original_claim == 'Original entry.' and item.claim_annotation == annotation
    assert item.mnion.summary == 'hidden original body' and item.mnion.rationale == 'hidden rationale'
    assert item.mnion.valence == .8 and item.review_id == route
    assert item.created_at == '2020-01-01T00:00:00Z'
    if packet:
        assert asdict(get_item(review_id=NEIGHBOR, db_path=tmp_path / 'mneme_read_model.sqlite3')) == neighbor_before


@pytest.mark.parametrize('route', [None, 42, '', 'abcdef', ' abcdef', 'review_a ', '"review_a"',
                                  ROUTE + ' ', ROUTE[:-1] + '01', ROUTE[:-1] + '0',
                                  ROUTE[:-1] + '2', 'review_missing', ROUTE.split(':')[0]])
def test_bad_or_unknown_route_never_repairs_or_writes(tmp_path, route):
    _state(tmp_path, project=False)
    before = _snapshot(tmp_path)
    result = _append(tmp_path, route)
    assert not result['ok']
    assert result['action'] in {'invalid_claim_annotation_request', 'unknown_item_route'}
    assert _snapshot(tmp_path) == before


@pytest.mark.parametrize('packet', [False, True])
@pytest.mark.parametrize('index', ['missing', 'fresh', 'stale'])
@pytest.mark.parametrize('entrypoint', ['core', 'mcp'])
@pytest.mark.parametrize('summary', ['   ', ' \t\n\u2003'])
def test_nonmaterializable_route_rejects_annotation_without_mutation(tmp_path, packet, index, entrypoint, summary):
    route = _state(tmp_path, packet=packet, project=index == 'stale')
    receipts = tmp_path / 'micro_consolidation_reviews.jsonl'
    receipt = json.loads(receipts.read_text())
    body = receipt['mnions'][0]['mnion'] if packet else receipt['mnion']
    body['summary'] = summary
    receipts.write_text(json.dumps(receipt) + '\n')
    # Establish actual projection eligibility separately, without repairing
    # the annotation runtime index (which may be missing or still stale).
    probe_db = tmp_path / 'eligibility.sqlite3'
    assert materialize_mnion_items_sqlite(receipts_path=receipts, db_path=probe_db) == (1 if packet else 0)
    assert get_item(review_id=route, db_path=probe_db) is None
    if index == 'fresh':
        materialize_mnion_items_sqlite(receipts_path=receipts, db_path=tmp_path / 'mneme_read_model.sqlite3')
    before = _snapshot(tmp_path)
    if entrypoint == 'core':
        result = _append(tmp_path, route)
    else:
        server = create_server(state_dir=tmp_path, config_path=tmp_path / 'config.toml')
        result = _call(server, 'annotate_claim', {'exact_item_route': route, 'authored_claim': CLAIM})
    assert not result['ok'] and result['action'] == 'unknown_item_route'
    assert result['exact_item_route'] == route
    assert _snapshot(tmp_path) == before


@pytest.mark.parametrize('claim', [None, *INVALID])
def test_invalid_claim_never_repairs_or_writes(tmp_path, claim):
    _state(tmp_path, project=False)
    before = _snapshot(tmp_path)
    result = _append(tmp_path, claim=claim)
    assert not result['ok'] and result['action'] == 'invalid_claim_annotation_request'
    assert _snapshot(tmp_path) == before


@pytest.mark.parametrize('pending', ['{', '[]', '{}', json.dumps({
    'kind': 'mneme_pending_review', 'status': 'pending', 'selected_ids': ['tag_a'],
    'agent_ingress': {'rendered': 'MNEME_REVIEW_PRESSURE', 'selected_ids': ['tag_a']},
    'review_packet': {'selected_ids': ['tag_a']}, 'semantic_auto_consolidation': False})])
def test_pending_review_blocks_without_lazy_clear_even_when_receipt_covers_ids(tmp_path, pending):
    _state(tmp_path)
    (tmp_path / 'pending_review.json').write_text(pending)
    before = _snapshot(tmp_path)
    result = _append(tmp_path)
    assert not result['ok']
    assert result['action'] in {'blocked_by_pending_review', 'blocked_by_invalid_pending_review'}
    assert result['next_tool'] == 'consolidate_review'
    assert result['tool_guidance']
    assert _snapshot(tmp_path) == before


def test_last_append_wins_not_timestamp_and_explicit_reads_repair_annotation_staleness(tmp_path):
    _state(tmp_path)
    first = _append(tmp_path)['annotation']
    ledger = tmp_path / 'claim_annotations.jsonl'
    prefix = ledger.read_bytes()
    second = _append(tmp_path, claim='Newest entry.')['annotation']
    assert first['id'] != second['id'] and ledger.read_bytes().startswith(prefix)
    # Imported ledger order, not a clock, is authoritative.
    second['created_at'] = '1900-01-01T00:00:00Z'
    with ledger.open('a', encoding='utf-8') as handle:
        handle.write(json.dumps(dict(second, id='annotation_imported', claim='Last appended.')) + '\n')
    args = _model_args(tmp_path)
    assert read_model_freshness(**args).status == 'stale'
    db_before = args['db_path'].read_bytes()
    surface = load_active_surface_from_read_model(db_path=args['db_path'])
    assert 'Newest entry.' in surface.rendered and 'Last appended.' not in surface.rendered
    assert args['db_path'].read_bytes() == db_before
    refresh = ensure_read_model_fresh(**args)
    assert refresh.refreshed and refresh.after.status == 'fresh'
    item = get_item(review_id=ROUTE, db_path=args['db_path'])
    assert item.mnion.claim == 'Last appended.' and item.claim_annotation['id'] == 'annotation_imported'


def test_read_model_failure_records_id_and_retry_does_not_duplicate(tmp_path, monkeypatch):
    _state(tmp_path)
    import mnion.read_model as rm
    original = rm.materialize_mnion_items_sqlite
    def fail(**kwargs):
        raise sqlite3.OperationalError('projection failed')
    monkeypatch.setattr(rm, 'materialize_mnion_items_sqlite', fail)
    result = _append(tmp_path)
    assert not result['ok'] and result['action'] == 'claim_annotation_recorded_projection_failed'
    annotation_id = result['annotation']['id']
    assert result['retry_annotation_id'] == annotation_id
    before = (tmp_path / 'claim_annotations.jsonl').read_bytes()
    monkeypatch.setattr(rm, 'materialize_mnion_items_sqlite', original)
    retried = _append(tmp_path, retry_annotation_id=annotation_id)
    assert retried['ok'] and retried['reused_annotation']
    assert (tmp_path / 'claim_annotations.jsonl').read_bytes() == before
    assert get_item(review_id=ROUTE, db_path=tmp_path / 'mneme_read_model.sqlite3').claim_annotation['id'] == annotation_id
    mismatch = _append(tmp_path, claim='different', retry_annotation_id=annotation_id)
    assert not mismatch['ok'] and mismatch['action'] == 'invalid_annotation_retry'
    assert (tmp_path / 'claim_annotations.jsonl').read_bytes() == before


def test_migration_and_freshness_metadata_roll_back_together(tmp_path):
    _state(tmp_path)
    _api()
    args = _model_args(tmp_path)
    annotation = {'id': 'annotation_imported', 'route': ROUTE, 'claim': CLAIM, 'created_at': '2026-01-01Z',
                  'kind': 'mnion_claim_annotation'}
    args['annotations_path'].write_text(json.dumps(annotation) + '\n')
    with sqlite3.connect(args['db_path']) as conn:
        conn.execute('ALTER TABLE mnion_items DROP COLUMN claim_annotation_json')
        columns = conn.execute('PRAGMA table_info(mnion_items)').fetchall()
        rows = conn.execute('SELECT * FROM mnion_items ORDER BY review_id').fetchall()
        meta = conn.execute('SELECT * FROM read_model_meta ORDER BY key').fetchall()
        conn.execute("CREATE TRIGGER fail_overlay BEFORE INSERT ON mnion_items BEGIN SELECT RAISE(ABORT, 'overlay failed'); END")
    with pytest.raises(sqlite3.IntegrityError, match='overlay failed'):
        ensure_read_model_fresh(**args)
    assert read_model_freshness(**args).status == 'stale'
    with sqlite3.connect(args['db_path']) as conn:
        assert conn.execute('PRAGMA table_info(mnion_items)').fetchall() == columns
        assert conn.execute('SELECT * FROM mnion_items ORDER BY review_id').fetchall() == rows
        assert conn.execute('SELECT * FROM read_model_meta ORDER BY key').fetchall() == meta
        conn.execute('DROP TRIGGER fail_overlay')
    assert ensure_read_model_fresh(**args).after.status == 'fresh'
    assert get_item(review_id=ROUTE, db_path=args['db_path']).mnion.claim == CLAIM


def test_mcp_explicit_annotation_tool_and_selected_item_provenance(tmp_path):
    _state(tmp_path)
    server = create_server(state_dir=tmp_path, config_path=tmp_path / 'config.toml')
    tools = {tool.name: tool for tool in run(server.list_tools())}
    assert set(tools) == {'capture', 'consolidate_review', 'list_topics', 'get_item', 'annotate_claim'}
    schema = input_schema(tools['annotate_claim'])
    assert set(schema['required']) == {'exact_item_route', 'authored_claim'}
    assert 'later' in tools['annotate_claim'].description.lower()
    result = _call(server, 'annotate_claim', {'exact_item_route': ROUTE, 'authored_claim': CLAIM})
    assert result['ok']
    item = _call(server, 'get_item', {'review_id': ROUTE})['item']
    assert item['original_claim'] == 'Original entry.'
    assert item['claim_annotation'] == result['annotation']
    assert item['mnion']['claim'] == CLAIM
    topics = _call(server, 'list_topics', {})['topics']
    assert topics[0]['item_count'] == 2
    assert topics[0]['top_review_ids'] == [ROUTE, NEIGHBOR]
    assert topics[0]['route_claims'] == {ROUTE: CLAIM, NEIGHBOR: 'Neighbor entry.'}
    surface = load_active_surface_from_read_model(db_path=tmp_path / 'mneme_read_model.sqlite3')
    assert CLAIM in surface.rendered and 'hidden original' not in surface.rendered


@pytest.mark.parametrize('target', ['micro_consolidation_reviews.jsonl', 'mneme_read_model.sqlite3',
                                  'pending_review.json', 'mneme_seq.json', 'memory_tags.jsonl'])
def test_annotation_path_cannot_alias_protected_artifacts(tmp_path, target):
    _state(tmp_path)
    before = _snapshot(tmp_path)
    result = _append(tmp_path, annotations_path=tmp_path / target)
    assert not result['ok'] and result['action'] == 'invalid_claim_annotation_request'
    assert _snapshot(tmp_path) == before


@pytest.mark.parametrize('artifact', ['ledger_path', 'state_path', 'config_path',
                                      'receipts_path', 'read_model_path', 'pending_review_path'])
@pytest.mark.parametrize('alias', ['equal', 'symlink', 'hardlink'])
def test_mcp_annotation_rejects_actual_custom_artifact_aliases(tmp_path, artifact, alias):
    _state(tmp_path, project=False)
    custom = tmp_path / 'custom'
    custom.mkdir()
    target = custom / artifact
    if artifact == 'receipts_path':
        target.write_bytes((tmp_path / 'micro_consolidation_reviews.jsonl').read_bytes())
    else:
        # An empty capture ledger reproduces the irreversible append, without
        # corrupt JSON masking the missing configured-path protection.
        target.write_bytes(b'')
    destination = target if alias == 'equal' else custom / 'annotation_alias'
    if alias == 'symlink':
        destination.symlink_to(target)
    elif alias == 'hardlink':
        import os
        os.link(target, destination)
    options = {'state_dir': tmp_path, 'config_path': tmp_path / 'config.toml',
               'annotations_path': destination, artifact: target}
    server = create_server(**options)
    before = _snapshot(tmp_path)
    result = _call(server, 'annotate_claim', {'exact_item_route': ROUTE, 'authored_claim': CLAIM})
    assert not result['ok'] and result['action'] == 'invalid_claim_annotation_request'
    assert _snapshot(tmp_path) == before


@pytest.mark.parametrize('alias', ['equal', 'symlink', 'hardlink'])
def test_core_annotation_rejects_explicit_protected_path_aliases(tmp_path, alias):
    _state(tmp_path, project=False)
    target = tmp_path / 'custom_capture.jsonl'
    target.write_bytes(b'')
    destination = target if alias == 'equal' else tmp_path / 'annotation_alias'
    if alias == 'symlink':
        destination.symlink_to(target)
    elif alias == 'hardlink':
        import os
        os.link(target, destination)
    before = _snapshot(tmp_path)
    result = _append(tmp_path, annotations_path=destination, protected_paths=[target])
    assert not result['ok'] and result['action'] == 'invalid_claim_annotation_request'
    assert _snapshot(tmp_path) == before


@pytest.mark.parametrize('entrypoint', ['core', 'mcp'])
def test_annotation_rejects_environment_selected_config_path(tmp_path, monkeypatch, entrypoint):
    _state(tmp_path, project=False)
    config = tmp_path / 'custom_config.toml'
    config.write_bytes(b'')
    monkeypatch.setenv('MNEME_CONFIG', str(config))
    before = _snapshot(tmp_path)
    if entrypoint == 'core':
        result = _append(tmp_path, annotations_path=config)
    else:
        server = create_server(state_dir=tmp_path, annotations_path=config)
        result = _call(server, 'annotate_claim', {'exact_item_route': ROUTE, 'authored_claim': CLAIM})
    assert not result['ok'] and result['action'] == 'invalid_claim_annotation_request'
    assert _snapshot(tmp_path) == before


@pytest.mark.parametrize('entrypoint', ['core', 'mcp'])
@pytest.mark.parametrize('suffix', ['-journal', '-wal', '-shm'])
@pytest.mark.parametrize('alias', ['equal_missing', 'equal_existing', 'destination_symlink',
                                   'destination_hardlink', 'configured_db_symlink',
                                   'resolved_db_symlink'])
def test_annotation_rejects_sqlite_auxiliary_paths_without_mutation(tmp_path, entrypoint, suffix, alias):
    import os
    from pathlib import Path

    _state(tmp_path, project=alias != 'equal_missing')
    actual_db = tmp_path / 'mneme_read_model.sqlite3'
    db = actual_db
    if alias in {'configured_db_symlink', 'resolved_db_symlink'}:
        db = tmp_path / 'configured_index.sqlite3'
        db.symlink_to(actual_db)
    auxiliary_base = actual_db if alias == 'resolved_db_symlink' else db
    auxiliary = Path(str(auxiliary_base) + suffix)
    destination = auxiliary
    if alias in {'destination_symlink', 'destination_hardlink'}:
        auxiliary.write_bytes(b'')
        destination = tmp_path / 'annotation_alias.jsonl'
        if alias == 'destination_symlink':
            destination.symlink_to(auxiliary)
        else:
            os.link(auxiliary, destination)
    before = _snapshot(tmp_path)
    if entrypoint == 'core':
        result = _append(tmp_path, db_path=db, annotations_path=destination)
    else:
        server = create_server(state_dir=tmp_path, config_path=tmp_path / 'config.toml',
                               read_model_path=db, annotations_path=destination)
        result = _call(server, 'annotate_claim', {'exact_item_route': ROUTE, 'authored_claim': CLAIM})
    evidence = destination.read_bytes() if destination.exists() else None
    assert not result['ok'], f'SQLite auxiliary ledger falsely succeeded: evidence prefix={evidence[:32] if evidence else evidence!r}'
    assert result['action'] == 'invalid_claim_annotation_request'
    assert _snapshot(tmp_path) == before
    assert destination.exists() == (alias in {'destination_symlink', 'destination_hardlink'})


@pytest.mark.parametrize('entrypoint', ['core', 'mcp'])
@pytest.mark.parametrize('damage', ['missing', 'corrupt', 'changed', 'new_latest'])
def test_annotation_verifies_durable_receipt_after_projection_commit(tmp_path, monkeypatch, entrypoint, damage):
    _state(tmp_path)
    import mnion.read_model as rm

    original = rm.materialize_mnion_items_sqlite
    before = _snapshot(tmp_path)
    committed = []
    def materialize_then_damage(**kwargs):
        count = original(**kwargs)
        ledger = kwargs['annotations_path']
        annotation = json.loads(ledger.read_text())
        # A real committed projection exists before evidence is lost/changed.
        assert rm.get_item(review_id=ROUTE, db_path=kwargs['db_path']).claim_annotation == annotation
        committed.append(annotation)
        if damage == 'missing':
            ledger.unlink()
        elif damage == 'corrupt':
            ledger.write_bytes(b'\xff')
        elif damage == 'changed':
            ledger.write_text(json.dumps(dict(annotation, claim='Changed after commit.')) + '\n')
        else:
            with ledger.open('a') as handle:
                handle.write(json.dumps(dict(annotation, id='annotation_new_latest', claim='New latest.')) + '\n')
        return count
    monkeypatch.setattr(rm, 'materialize_mnion_items_sqlite', materialize_then_damage)
    if entrypoint == 'core':
        result = _append(tmp_path)
    else:
        server = create_server(state_dir=tmp_path, config_path=tmp_path / 'config.toml')
        result = _call(server, 'annotate_claim', {'exact_item_route': ROUTE, 'authored_claim': CLAIM})
    assert not result['ok'] and result['action'] == 'claim_annotation_recorded_projection_failed'
    assert result['annotation'] == committed[0]
    assert result['retry_annotation_id'] == committed[0]['id']
    assert not result['reused_annotation']
    after = _snapshot(tmp_path)
    assert all(after[name] == value for name, value in before.items() if name != 'mneme_read_model.sqlite3')


def test_imported_ledger_without_final_newline_can_be_extended_append_only(tmp_path):
    _state(tmp_path)
    record = {'id': 'annotation_imported', 'kind': 'mnion_claim_annotation', 'route': ROUTE,
              'claim': 'Imported entry.', 'created_at': '2026-01-01Z'}
    ledger = tmp_path / 'claim_annotations.jsonl'
    ledger.write_text(json.dumps(record))
    prefix = ledger.read_bytes()
    result = _append(tmp_path)
    assert result['ok']
    assert ledger.read_bytes().startswith(prefix)
    assert len(_api().load_claim_annotations(ledger)) == 2


def test_malformed_source_id_is_not_repaired_for_authorship(tmp_path):
    _state(tmp_path, packet=False, project=False)
    receipts = tmp_path / 'micro_consolidation_reviews.jsonl'
    receipt = json.loads(receipts.read_text())
    receipt['id'] = ' review_single '
    receipts.write_text(json.dumps(receipt) + '\n')
    before = _snapshot(tmp_path)
    result = _append(tmp_path, route='review_single')
    assert not result['ok'] and result['action'] == 'unknown_item_route'
    assert _snapshot(tmp_path) == before


@pytest.mark.parametrize('contents', ['{', '[]\n', '{}\n'])
def test_corrupt_sidecar_fails_closed_without_projection_or_append(tmp_path, contents):
    _state(tmp_path)
    (tmp_path / 'claim_annotations.jsonl').write_text(contents)
    before = _snapshot(tmp_path)
    result = _append(tmp_path)
    assert not result['ok'] and result['action'] == 'annotation_source_unavailable'
    assert _snapshot(tmp_path) == before


@pytest.mark.parametrize('corruption', ['invalid_json', 'invalid_claim', 'invalid_valence'])
@pytest.mark.parametrize('neighbor', [False, True])
def test_corrupt_receipt_source_never_appends_or_repairs(tmp_path, corruption, neighbor):
    _state(tmp_path)
    receipts = tmp_path / 'micro_consolidation_reviews.jsonl'
    if corruption == 'invalid_json':
        receipts.write_text('{')
    else:
        receipt = json.loads(receipts.read_text())
        payload = receipt['mnions'][1 if neighbor else 0]['mnion']
        payload['claim' if corruption == 'invalid_claim' else 'valence'] = []
        receipts.write_text(json.dumps(receipt) + '\n')
    before = _snapshot(tmp_path)
    result = _append(tmp_path)
    assert not result['ok'] and result['action'] == 'annotation_source_unavailable'
    assert _snapshot(tmp_path) == before


def test_missing_state_unknown_route_creates_nothing(tmp_path):
    root = tmp_path / 'does-not-exist'
    result = _append(root)
    assert result['action'] == 'unknown_item_route'
    assert not root.exists()


def test_projection_missing_item_reports_recorded_id(tmp_path, monkeypatch):
    _state(tmp_path)
    import mnion.read_model as rm
    monkeypatch.setattr(rm, 'get_item', lambda **kwargs: None)
    result = _append(tmp_path)
    assert result['action'] == 'claim_annotation_recorded_projection_failed'
    assert result['retry_annotation_id'] == json.loads((tmp_path / 'claim_annotations.jsonl').read_text())['id']


def test_annotated_shared_surface_is_read_only_bounded_and_body_free(tmp_path, monkeypatch):
    _state(tmp_path)
    assert _append(tmp_path, claim='🧠' * 240)['ok']
    original = sqlite3.connect
    def connect(*args, **kwargs):
        conn = original(*args, **kwargs)
        def authorize(action, table, column, *_):
            if action == sqlite3.SQLITE_READ and table == 'mnion_items' and column in {
                    'summary', 'rationale', 'receipt_json', 'grouped_ids_json', 'claim_annotation_json'}:
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK
        conn.set_authorizer(authorize)
        return conn
    before = _snapshot(tmp_path)
    monkeypatch.setattr(sqlite3, 'connect', connect)
    db = tmp_path / 'mneme_read_model.sqlite3'
    core = load_active_surface_from_read_model(db_path=db)
    assert core.source_status == 'ok' and '🧠' * 240 in core.rendered
    from test_hermes_memory_provider import _load_provider_module
    from test_claude_code_surface import _run
    module = _load_provider_module(monkeypatch, tmp_path)
    provider = module.MnemeMemoryProvider(config={'read_model_path': str(db)})
    provider.initialize(session_id='annotations')
    assert provider.prefetch('unrelated', session_id='annotations') == core.rendered
    assert _run('--state-dir', str(tmp_path))['rendered'] == core.rendered
    # Test helper writes plugin fixtures outside runtime sources.
    after = _snapshot(tmp_path)
    assert all(after[name] == value for name, value in before.items())


def test_custom_annotation_ledger_participates_in_mcp_explicit_repair(tmp_path):
    _state(tmp_path)
    ledger = tmp_path / 'custom' / 'annotations.jsonl'
    assert _append(tmp_path, annotations_path=ledger)['ok']
    server = create_server(state_dir=tmp_path, annotations_path=ledger, config_path=tmp_path / 'config.toml')
    result = _call(server, 'get_item', {'review_id': ROUTE})
    assert result['ok'] and not result['read_model_refreshed']
    entry = dict(result['item']['claim_annotation'], id='annotation_external', claim='External append.')
    with ledger.open('a') as handle:
        handle.write(json.dumps(entry) + '\n')
    result = _call(server, 'get_item', {'review_id': ROUTE})
    assert result['read_model_refreshed'] and result['item']['mnion']['claim'] == 'External append.'
    assert _call(server, 'list_topics', {})['topics'][0]['route_claims'][ROUTE] == 'External append.'


@pytest.mark.parametrize('packet', [False, True])
def test_real_mcp_stdio_annotation_single_and_packet(tmp_path, packet):
    import asyncio
    import os
    import sys
    from pathlib import Path
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from test_mcp_adapter import _interval_config

    config = _interval_config(tmp_path)
    env = dict(os.environ)
    for key, directory in {'HOME': 'home', 'HERMES_HOME': 'hermes', 'XDG_STATE_HOME': 'xdg-state',
                           'XDG_CONFIG_HOME': 'xdg-config', 'TMPDIR': 'tmp'}.items():
        directory = tmp_path / directory
        directory.mkdir()
        env[key] = str(directory)
    env.update(MNEME_STATE_DIR=str(tmp_path / 'state'), MNEME_CONFIG=str(config),
               PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=str(Path(__file__).resolve().parents[1] / 'src'))

    async def smoke():
        params = StdioServerParameters(command=sys.executable, args=['-m', 'mnion.mcp_server'], env=env)
        async with stdio_client(params) as (reader, writer):
            async with ClientSession(reader, writer) as session:
                await session.initialize()
                def unpack(response):
                    assert not getattr(response, 'isError', getattr(response, 'is_error', False))
                    structured = getattr(response, 'structuredContent', getattr(response, 'structured_content', None))
                    return structured if structured is not None else json.loads(response.content[0].text)
                async def call(name, **args):
                    return unpack(await session.call_tool(name, args))
                assert 'annotate_claim' in {tool.name for tool in (await session.list_tools()).tools}
                first = await call('capture', delta='The exact memory route should stay stable under later annotation.', valence=.9)
                second = await call('capture', delta='Later navigation is not original authorship or evidence of an event.', valence=.8)
                ids = second['review_packet']['selected_ids']
                state = Path(env['MNEME_STATE_DIR'])
                before = _snapshot(state)
                blocked = await call('annotate_claim', exact_item_route='review_missing', authored_claim=CLAIM)
                assert blocked['action'] == 'blocked_by_pending_review' and _snapshot(state) == before
                group = {'summary': 'original semantic body', 'valence': .8, 'member_ids': ids}
                args = {'selected_ids': ids, **({'mnions': [dict(group, member_ids=[ids[0]]),
                         dict(group, member_ids=[ids[1]])]} if packet else group)}
                review = await call('consolidate_review', **args)
                assert review['ok']
                route = review['review_ids'][0]
                assert (':mnion:1' in route) == packet
                before = _snapshot(state)
                invalid = await call('annotate_claim', exact_item_route=route + ' ', authored_claim=CLAIM)
                assert invalid['action'] == 'invalid_claim_annotation_request' and _snapshot(state) == before
                annotation = await call('annotate_claim', exact_item_route=route, authored_claim=CLAIM)
                assert annotation['ok']
                opened = await call('get_item', review_id=route)
                assert opened['item']['claim_annotation'] == annotation['annotation']
                assert opened['item']['original_claim'] is None and opened['item']['mnion']['claim'] == CLAIM
                topics = await call('list_topics')
                assert any(t['route_claims'].get(route) == CLAIM for t in topics['topics'])
                assert all(_snapshot(state)[name] == value for name, value in before.items()
                           if name != 'mneme_read_model.sqlite3')
                retry = await call('annotate_claim', exact_item_route=route, authored_claim=CLAIM,
                                   retry_annotation_id=annotation['annotation']['id'])
                assert retry['ok'] and retry['reused_annotation']
                assert len((state / 'claim_annotations.jsonl').read_text().splitlines()) == 1
                if packet:
                    neighbor = await call('get_item', review_id=review['review_ids'][1])
                    assert neighbor['item']['mnion']['claim'] is None and neighbor['item']['claim_annotation'] is None
                print('MCP STDIO', 'packet' if packet else 'single', 'verified:', route, annotation['annotation']['id'])
    asyncio.run(smoke())


@pytest.mark.parametrize('packet', [False, True])
def test_real_mcp_stdio_annotation_of_old_receipts(tmp_path, packet):
    import asyncio
    import os
    import sys
    from pathlib import Path
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    state = tmp_path / 'state'
    route = _state(state, packet=packet, project=False)
    before = _snapshot(state)
    env = dict(os.environ)
    for key, name in {'HOME': 'home', 'HERMES_HOME': 'hermes',
                      'XDG_CONFIG_HOME': 'xdg-config', 'XDG_STATE_HOME': 'xdg-state',
                      'TMPDIR': 'tmp'}.items():
        directory = tmp_path / name
        directory.mkdir()
        env[key] = str(directory)
    env.update(MNEME_STATE_DIR=str(state), MNEME_CONFIG=str(state / 'config.toml'),
               PYTHONDONTWRITEBYTECODE='1',
               PYTHONPATH=str(Path(__file__).resolve().parents[1] / 'src'))

    async def smoke():
        params = StdioServerParameters(command=sys.executable,
                                       args=['-m', 'mnion.mcp_server'], env=env)
        async with stdio_client(params) as (reader, writer):
            async with ClientSession(reader, writer) as session:
                await session.initialize()
                tools = {tool.name for tool in (await session.list_tools()).tools}
                assert tools == {'capture', 'consolidate_review', 'get_item',
                                 'list_topics', 'annotate_claim'}
                async def call(name, **arguments):
                    response = await session.call_tool(name, arguments)
                    assert not getattr(response, 'isError', getattr(response, 'is_error', False))
                    result = getattr(response, 'structuredContent',
                                     getattr(response, 'structured_content', None))
                    return result if result is not None else json.loads(response.content[0].text)
                for malformed in (route + ' ', route + ':mnion:0', 'review_missing'):
                    result = await call('annotate_claim', exact_item_route=malformed,
                                        authored_claim=CLAIM)
                    assert not result['ok'] and _snapshot(state) == before
                annotation = await call('annotate_claim', exact_item_route=route,
                                        authored_claim=CLAIM)
                assert annotation['ok']
                item = (await call('get_item', review_id=route))['item']
                assert item['mnion'] == {'summary': 'hidden original body',
                                         'rationale': 'hidden rationale', 'valence': .8,
                                         'claim': CLAIM}
                assert item['review_id'] == route and item['created_at'] == '2020-01-01T00:00:00Z'
                assert item['original_claim'] == 'Original entry.'
                assert item['claim_annotation'] == annotation['annotation']
                topics = (await call('list_topics'))['topics']
                assert sum(topic['item_count'] for topic in topics) == (2 if packet else 1)
                assert any(topic['route_claims'].get(route) == CLAIM for topic in topics)
                assert all(_snapshot(state)[name] == value for name, value in before.items())
                snapshot = _snapshot(state)
                rejected = await call('annotate_claim', exact_item_route=route, authored_claim='bad\nclaim')
                assert not rejected['ok'] and _snapshot(state) == snapshot
                assert len((state / 'claim_annotations.jsonl').read_text().splitlines()) == 1
                if packet:
                    neighbor = (await call('get_item', review_id=NEIGHBOR))['item']
                    assert neighbor['mnion']['claim'] == 'Neighbor entry.'
                    assert neighbor['claim_annotation'] is None
                print('OLD RECEIPT MCP STDIO:', 'packet' if packet else 'single',
                      'tools=5 items=' + str(2 if packet else 1),
                      'annotations=1 rejected=4 originals=unchanged')
    asyncio.run(smoke())
