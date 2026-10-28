"""Selected-walk experiment over existing readers; no storage or product API.

The agent authors the entrance and chooses originals AFTER explicit expansion.
This module only checks literal addresses/bounds and preserves returned evidence.
It does not choose routes, synthesize a story, refresh an entrance, or infer edges.
"""
from copy import deepcopy

from mnion.annotations import is_valid_exact_item_route


def _count(value, low, high):
    if type(value) is not int or not low <= value <= high:
        raise ValueError('A literal integer within the declared bound is required')


def _route(value):
    if not is_valid_exact_item_route(value):
        raise ValueError('A literal exact route is required; input is not repaired')
    return value


def _view(value, *, edge_limit=8):
    if not isinstance(value, dict) or value.get('ok') is not True:
        raise ValueError('Neighborhood is unavailable; not an empty successful walk')
    root = _route(value.get('root_review_id'))
    nodes, edges = value.get('nodes'), value.get('connections')
    if (not isinstance(nodes, list) or not isinstance(edges, list)
            or type(value.get('has_more')) is not bool
            or len(edges) > edge_limit or len(nodes) > 2 * edge_limit + 1):
        raise ValueError('Invalid or out-of-bound neighborhood')
    routes = []
    for node in nodes:
        if not isinstance(node, dict) or set(node) - {'review_id', 'claim'}:
            raise ValueError('Expected route/claim nodes, not preloaded bodies')
        routes.append(_route(node.get('review_id')))
    if root not in routes or len(set(routes)) != len(routes):
        raise ValueError('Missing root or duplicate node identity')
    return set(routes)


def expand_entry(entry, reader, *, depth=1, limit=4):
    """Explicitly expand a hand-authored sketch; reader performs no body reads."""
    _count(depth, 1, 2)
    _count(limit, 1, 8)
    if (not isinstance(entry, dict) or set(entry) != {'knows', 'route'}
            or not isinstance(entry['knows'], str) or not entry['knows'].strip()):
        raise ValueError('Expected an authored entrance sketch')
    route = entry['route']
    if (not isinstance(route, dict) or set(route) != {'action', 'exact_item_route'}
            or route.get('action') != 'get_neighborhood'):
        raise ValueError('Only explicit neighborhood expansion is supported')
    root = _route(route['exact_item_route'])
    result = reader(root, depth=depth, limit=limit)
    _view(result, edge_limit=limit)
    if result['root_review_id'] != root:
        raise ValueError('The returned root differs from the selected entrance')
    return deepcopy(result)


def open_selected(view, routes, reader, *, max_originals=3):
    """Open only the separately chosen visible originals; no implicit expansion."""
    _count(max_originals, 1, 8)
    visible = _view(view)
    if not isinstance(routes, list) or len(routes) > max_originals:
        raise ValueError('Expected a bounded explicit selection')
    for route in routes:
        _route(route)
    if len(set(routes)) != len(routes) or any(r not in visible for r in routes):
        raise ValueError('Selected originals must be distinct visible exact routes')
    results = []
    for route in routes:
        result = reader(route)
        item = result.get('item') if isinstance(result, dict) else None
        if (not isinstance(result, dict) or result.get('ok') is not True
                or not isinstance(item, dict) or item.get('review_id') != route):
            raise ValueError('Original retrieval failed or returned a different item')
        results.append(deepcopy(result))
    return results
