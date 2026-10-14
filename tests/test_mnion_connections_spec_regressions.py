"""Independent SPEC findings reproduced before parent-authored corrections."""
import os
import pytest
from mnion.annotations import append_claim_annotation
from test_mnion_connections import A,B,C,state,snapshot,append,neighborhood


def test_depth_two_returns_receipt_order_not_discovery_order(tmp_path):
    state(tmp_path)
    first=append(tmp_path,C,B,'follows_from','The later check follows a correction.')['connection']
    second=append(tmp_path,B,A,'corrects','This corrects the initial understanding.')['connection']
    before=snapshot(tmp_path)
    arc=neighborhood(tmp_path,depth=2)
    assert arc['ok'] and arc['connections']==[first,second]
    assert {n['review_id'] for n in arc['nodes']}=={A,B,C}
    assert not arc['has_more'] and snapshot(tmp_path)==before


@pytest.mark.parametrize('alias',['direct','symlink','hardlink'])
def test_core_claim_writer_protects_connection_source_beside_custom_receipts(tmp_path,alias):
    custom=tmp_path/'custom';state(custom,project=False)
    receipts=custom/'micro_consolidation_reviews.jsonl'
    edge_source=custom/'mnion_connections.jsonl';edge_source.write_bytes(b'')
    destination=edge_source
    if alias!='direct':
        destination=tmp_path/('claim-destination-'+alias)
        if alias=='symlink':destination.symlink_to(edge_source)
        else:os.link(edge_source,destination)
    before=snapshot(tmp_path)
    out=append_claim_annotation(exact_item_route=A,authored_claim='A later fixture claim.',
                               state_dir=tmp_path,receipts_path=receipts,annotations_path=destination)
    assert not out['ok'], 'claim evidence must not enter the inferred connection source'
    assert out['action']=='invalid_claim_annotation_request'
    assert snapshot(tmp_path)==before
