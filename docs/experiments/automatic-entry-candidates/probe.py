#!/usr/bin/env python3
"""Offline, model-free association probe. Explicit JSON in; derived map on stdout.

No state defaults, network, agent calls, semantic promotion or writes. Association
is not agreement, chronology of events, an authored relation, or a mature engram.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import unicodedata

VERSION = 'lexical-call-window-v1'
MAX_ITEMS = 256
MAX_BYTES = 8 * 1024 * 1024
ROUTE = re.compile(r'review_[0-9a-f]{32}(?::mnion:[1-9][0-9]*)?\Z')
ENTRY = re.compile(r'entry_[0-9a-f]{64}\Z')
STOP = set('''the and for with that this from into when then than should could would
through current memory memories tag tags mnion mnions about have been were are was
это этой этот того тому том как что чтобы когда тогда для при или уже ещё еще
так также только есть быть было были будет будут меня мне мы наш наши она они его
память памяти мнион мнионы мнионов'''.split())
GUARDS = [
    'Association candidates, not verified semantic agreement or causal relations.',
    'Call distance is consolidation-clock distance, not event occurrence time.',
    'Explicit input is partial history; missing candidates do not establish absence.',
    'Text overlap is a lexical proxy, not embeddings or synonym-level understanding.',
    'No engram promotion, Dream, reinforcement, host ingress or original mutation.',
]


def _digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def _route(value):
    if not isinstance(value, str) or len(value) > 256 or not ROUTE.fullmatch(value):
        raise ValueError('Expected an unmodified exact item route')
    return value


def _tokens(text):
    text = unicodedata.normalize('NFKC', text).lower().replace('ё', 'е')
    return Counter(t for t in re.findall(r'[^\W_]+', text, re.UNICODE)
                   if len(t) > 2 and not t.isdecimal() and t not in STOP)


def _items(values):
    if not isinstance(values, list) or len(values) > MAX_ITEMS:
        raise ValueError('Explicit input must contain at most 256 items')
    result, seen = [], set()
    for value in values:
        if not isinstance(value, dict):
            raise ValueError('Each item must be an object')
        route = _route(value.get('review_id'))
        if route in seen:
            raise ValueError('Duplicate item route')
        seen.add(route)
        body = value.get('mnion')
        if not isinstance(body, dict):
            raise ValueError('Missing mnion body')
        summary, claim = body.get('summary'), body.get('claim')
        if not isinstance(summary, str) or not summary.strip() or len(summary) > 16384:
            raise ValueError('Expected nonblank summary, at most 16384 characters in this probe')
        if claim is not None and (not isinstance(claim, str) or len(claim) > 240):
            raise ValueError('Invalid optional claim')
        receipt = value.get('receipt', {})
        if not isinstance(receipt, dict):
            raise ValueError('Invalid receipt wrapper')
        tick = receipt.get('mneme_call_seq')
        if tick is not None and (type(tick) is not int or not 0 <= tick <= 2**63-1):
            raise ValueError('Clock must be a nonnegative integer or unknown')
        sources = value.get('grouped_ids', [])
        if (not isinstance(sources, list) or len(sources) > 64
                or any(not isinstance(s, str) or not s or s != s.strip() or len(s) > 200 for s in sources)
                or len(set(sources)) != len(sources)):
            raise ValueError('Invalid source-tag routes')
        # Count summary and claim as one feature family, not independent votes.
        terms = _tokens(summary + ' ' + (claim or ''))
        result.append({'route': route, 'claim': claim, 'tick': tick,
                       'sources': set(sources), 'terms': terms})
    return sorted(result, key=lambda i: i['route'])


def build(values, *, window_calls=40, min_similarity=0.25, min_shared_terms=2,
          max_neighbors=4):
    """Derive a bounded graph and clique-shaped entry candidates, never mnions."""
    if type(window_calls) is not int or not 0 <= window_calls <= 2**63-1:
        raise ValueError('Invalid window_calls')
    if type(max_neighbors) is not int or not 1 <= max_neighbors <= 8:
        raise ValueError('Invalid max_neighbors (1..8)')
    if type(min_shared_terms) is not int or not 1 <= min_shared_terms <= 64:
        raise ValueError('Invalid min_shared_terms')
    if (type(min_similarity) not in (int, float) or not math.isfinite(min_similarity)
            or not 0 < min_similarity <= 1):
        raise ValueError('Invalid min_similarity')
    items = _items(values)
    by_route = {i['route']: i for i in items}
    df = Counter(t for i in items for t in i['terms'])
    vectors, norms = {}, {}
    for item in items:
        vector = {t: count * (1 + math.log((1 + len(items))/(1 + df[t])))
                  for t, count in item['terms'].items()}
        vectors[item['route']] = vector
        norms[item['route']] = math.sqrt(sum(v*v for _, v in sorted(vector.items())))
    # Index overlap rather than unconditionally comparing all pairs. The explicit
    # corpus cap additionally bounds degenerate very-common-term postings.
    postings = defaultdict(list)
    for item in items:
        for term in sorted(item['terms']):
            postings[('text', term)].append(item['route'])
        for source in sorted(item['sources']):
            postings[('source', source)].append(item['route'])
    pairs = set()
    for routes in postings.values():
        for pos, left in enumerate(routes):
            pairs.update((left, right) for right in routes[pos+1:])
    eligible = []
    for left, right in sorted(pairs):
        a, b = by_route[left], by_route[right]
        if a['tick'] is None or b['tick'] is None:
            continue
        gap = abs(a['tick']-b['tick'])
        if gap > window_calls:
            continue
        va, vb = vectors[left], vectors[right]
        shared = sorted(set(va) & set(vb), key=lambda t: (-(va[t]*vb[t]), t))
        norm = norms[left] * norms[right]
        similarity = min(1.0, sum(va[t]*vb[t] for t in sorted(shared))/norm) if norm else 0.0
        sources = sorted(a['sources'] & b['sources'])
        if not sources and (len(shared) < min_shared_terms or similarity < min_similarity):
            continue
        eligible.append({'endpoints': [left, right], 'kind': 'association_candidate',
                         'evidence': {'call_gap': gap, 'text_similarity': round(similarity, 6),
                                      'shared_terms': [t if len(t) <= 64 else
                                                       t[:48]+'…#'+hashlib.sha256(t.encode()).hexdigest()[:12]
                                                       for t in shared[:8]],
                                      'shared_terms_abbreviated': any(len(t) > 64 for t in shared[:8]),
                                      'shared_term_count': len(shared),
                                      'shared_source_ids': sources[:8],
                                      'shared_source_count': len(sources),
                                      'source_evidence_partial': len(sources) > 8}})
    # Separate evidence components; no invented probability or learned weight.
    eligible.sort(key=lambda e: (-bool(e['evidence']['shared_source_count']),
                                 -e['evidence']['text_similarity'], e['evidence']['call_gap'],
                                 e['endpoints']))
    edges, adjacent = [], {r: set() for r in by_route}
    discarded = 0
    for edge in eligible:
        a, b = edge['endpoints']
        if len(adjacent[a]) >= max_neighbors or len(adjacent[b]) >= max_neighbors:
            discarded += 1
            continue
        edges.append(edge)
        adjacent[a].add(b)
        adjacent[b].add(a)
    edge_lookup = {tuple(e['endpoints']): e for e in edges}
    groups = {}
    for edge in edges:
        a, b = edge['endpoints']
        members = {a, b}
        # Greedy complete-link cover, not connected components and not a claim
        # to enumerate every maximal clique. Shared nodes across groups are OK.
        for route in sorted(adjacent[a] & adjacent[b]):
            if all(route in adjacent[member] for member in members):
                members.add(route)
        key = tuple(sorted(members))
        alias = 'entry_' + _digest([VERSION, edge['endpoints']])
        groups.setdefault(key, []).append({'id': alias, 'seed_routes': [a, b]})
    entries = []
    for members, seeds in sorted(groups.items()):
        seeds.sort(key=lambda s: s['id'])
        terms = Counter()
        for pos, left in enumerate(members):
            for right in members[pos+1:]:
                terms.update(edge_lookup[(left, right)]['evidence']['shared_terms'])
        entries.append({'id': seeds[0]['id'], 'aliases': [s['id'] for s in seeds],
                        'seeds': seeds, 'status': 'candidate', 'member_routes': list(members),
                        'cue': {'shared_terms': sorted(terms, key=lambda t: (-terms[t], t))[:8],
                                'claims': [{'review_id': r, 'claim': by_route[r]['claim']}
                                           for r in members if by_route[r]['claim'] is not None][:2]}})
    config = {'window_calls': window_calls, 'min_similarity': min_similarity,
              'min_shared_terms': min_shared_terms, 'max_neighbors': max_neighbors}
    fingerprint = _digest([{'review_id': i['route'], 'claim': i['claim'], 'tick': i['tick'],
                            'sources': sorted(i['sources']), 'terms': dict(i['terms'])} for i in items])
    return {'algorithm': VERSION, 'input_fingerprint': fingerprint, 'config': config,
            'nodes': [{'review_id': i['route'], 'claim': i['claim'],
                       'consolidation_call_seq': i['tick']} for i in items],
            'edges': sorted(edges, key=lambda e: e['endpoints']), 'entries': entries,
            'authored_relations': [],
            'coverage': {'scope': 'explicit_input_only', 'history_complete': False,
                         'semantic_agreement_verified': False,
                         'input_items': len(items),
                         'unknown_clock_items': sum(i['tick'] is None for i in items),
                         'overlap_pairs_examined': len(pairs),
                         'discarded_by_degree_limit': discarded, 'partial': bool(discarded),
                         'candidate_cover': 'greedy_complete_link_not_all_maximal_cliques'},
            'guards': GUARDS.copy()}


def resolve(graph, address):
    """Resolve only an exact generated address; no nearest-pointer fallback."""
    if not isinstance(address, str) or not ENTRY.fullmatch(address):
        raise ValueError('Invalid literal entry address')
    if not isinstance(graph, dict) or graph.get('algorithm') != VERSION:
        raise ValueError('Unsupported map')
    nodes, entries = graph.get('nodes'), graph.get('entries')
    if not isinstance(nodes, list) or len(nodes) > MAX_ITEMS or not isinstance(entries, list):
        raise ValueError('Invalid map')
    routes = {_route(n['review_id']) for n in nodes}
    if len(entries) > MAX_ITEMS * 8:
        raise ValueError('Invalid candidate count')
    found = None
    for entry in entries:
        aliases = entry.get('aliases')
        members = entry.get('member_routes')
        if (not isinstance(aliases, list) or not aliases or len(aliases) > MAX_ITEMS * 8
                or any(not isinstance(a, str) or not ENTRY.fullmatch(a) for a in aliases)
                or entry.get('id') not in aliases or entry.get('status') != 'candidate'
                or not isinstance(members, list) or not 2 <= len(members) <= 9
                or len(set(members)) != len(members)
                or any(_route(r) not in routes for r in members)):
            raise ValueError('Invalid entry')
        if address in aliases:
            if found is not None:
                raise ValueError('Ambiguous entry address')
            found = entry
    return found


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key')
        result[key] = value
    return result


def _read(path):
    with Path(path).open('rb') as stream:
        raw = stream.read(MAX_BYTES+1)
    if len(raw) > MAX_BYTES:
        raise ValueError('Input exceeds probe byte bound')
    return json.loads(raw, object_pairs_hook=_unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite JSON number')))


def encode_output(result):
    """Check serialized UTF-8 bytes, including LF, before emitting any output."""
    rendered = json.dumps(result, ensure_ascii=False, sort_keys=True,
                          indent=2, allow_nan=False)+'\n'
    if len(rendered.encode('utf-8')) > MAX_BYTES:
        raise ValueError('Output exceeds the read-compatible byte bound')
    return rendered


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='command', required=True)
    building = subs.add_parser('build')
    building.add_argument('input')
    building.add_argument('--window-calls', type=int, default=40)
    building.add_argument('--min-similarity', type=float, default=0.25)
    building.add_argument('--min-shared-terms', type=int, default=2)
    building.add_argument('--max-neighbors', type=int, default=4)
    opening = subs.add_parser('open')
    opening.add_argument('input')
    opening.add_argument('--entry', required=True)
    original = subs.add_parser('item')
    original.add_argument('input')
    original.add_argument('--route', required=True)
    args = parser.parse_args()
    try:
        data = _read(args.input)
        if args.command == 'build':
            if not isinstance(data, dict) or 'items' not in data:
                raise ValueError('Expected explicit {items: [...]} export')
            result = build(data['items'], window_calls=args.window_calls,
                           min_similarity=args.min_similarity,
                           min_shared_terms=args.min_shared_terms, max_neighbors=args.max_neighbors)
        elif args.command == 'open':
            result = resolve(data, args.entry)
        else:
            _route(args.route)
            if not isinstance(data, dict) or 'items' not in data:
                raise ValueError('Expected explicit item export')
            _items(data['items'])
            result = next((i for i in data['items'] if i['review_id'] == args.route), None)
        if result is None:
            print(json.dumps({'status': 'not_found'}))
            return 3
        sys.stdout.write(encode_output(result))
        return 0
    except (OSError, ValueError, TypeError, KeyError, AttributeError, RecursionError):
        # Do not echo raw input bodies, paths or decoder exception fragments.
        print('Invalid or unavailable explicit input; no writes performed.', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
