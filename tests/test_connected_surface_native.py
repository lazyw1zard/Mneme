"""Optional actual Hermes plugin/MemoryManager smoke, no inference or live state."""
import json
import os
from pathlib import Path
import subprocess
import pytest


def test_native_connected_ingress(tmp_path):
    runtime = os.environ.get('MNEME_TEST_HERMES_PYTHON')
    source = os.environ.get('MNEME_TEST_HERMES_ROOT')
    if not runtime or not source:
        pytest.skip('Set native Hermes source and interpreter paths for integration')
    repo = Path(__file__).resolve().parents[1]
    env = {k:v for k,v in os.environ.items() if not k.startswith(('HERMES_', 'MNEME_', 'XDG_'))}
    for key, folder in [('HOME','home'), ('HERMES_HOME','hermes'), ('XDG_STATE_HOME','state'),
                        ('XDG_CONFIG_HOME','config'), ('XDG_DATA_HOME','data'),
                        ('XDG_CACHE_HOME','cache'), ('TMPDIR','tmp')]:
        path = tmp_path/folder; path.mkdir(); env[key] = str(path)
    env.update(PYTHONPATH=os.pathsep.join([source, str(repo/'src')]),
               PYTHONDONTWRITEBYTECODE='1', CONNECTED_PLUGIN=str(repo/'adapters/hermes_memory_provider/mneme'))
    worker = r'''
import hashlib,json,os
from pathlib import Path
from mnion.read_model import materialize_mnion_items_sqlite
from mnion.connections import append_connection
home=Path(os.environ['HERMES_HOME']);(home/'plugins').mkdir()
(home/'plugins/mneme').symlink_to(os.environ['CONNECTED_PLUGIN'],target_is_directory=True)
state=home/'mneme';state.mkdir()
os.environ['MNEME_STATE_DIR']=str(state)
os.environ['MNEME_CONFIG']=str(home/'mneme.toml');(home/'mneme.toml').write_text('')
(home/'config.yaml').write_text('memory:\n  provider: mneme\nplugins:\n  mneme:\n    state_dir: '+json.dumps(str(state))+'\n')
a,b,c=['review_'+letter*32+':mnion:1' for letter in 'abc']
receipts=state/'micro_consolidation_reviews.jsonl'
rows=[{'id':route.split(':')[0],'created_at':'2026-01-01T00:00:00Z',
       'mnions':[{'review_id':route,'grouped_ids':[],
       'mnion':{'summary':'PRIVATE BODY '+letter,'rationale':'PRIVATE RATIONALE',
                'claim':'Navigation '+letter,'valence':.7}}]} for route,letter in zip([a,b,c],'abc')]
receipts.write_text(''.join(json.dumps(row)+'\n' for row in rows))
materialize_mnion_items_sqlite(receipts_path=receipts,db_path=state/'mneme_read_model.sqlite3')
older=append_connection(source_review_id=b,target_review_id=a,relation_kind='corrects',
                        relation_summary='An authored correction changed a check.',state_dir=state)['connection']
newer=append_connection(source_review_id=c,target_review_id=b,relation_kind='continues',
                        relation_summary='A separate continuation.',state_dir=state)['connection']
def snapshot():return {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in state.iterdir() if p.is_file()}
before=snapshot()
from plugins.memory import load_memory_provider
from agent.memory_manager import MemoryManager
from agent.turn_context import compose_user_api_content
provider=load_memory_provider('mneme');assert provider is not None
provider.initialize('native-connected')
manager=MemoryManager();manager.add_provider(provider)
first=manager.prefetch_all('Unrelated ordinary message',session_id='native-connected')
assert newer['id'] in first and 'recent_authored_connection' in first
original='Return to `'+a+'`'
second=manager.prefetch_all(original,session_id='native-connected')
assert older['id'] in second and 'explicit_route_in_cue' in second
wire=compose_user_api_content(original,second,'')
assert second in wire and 'connected_entrance: ' in wire
assert 'PRIVATE BODY' not in wire and 'PRIVATE RATIONALE' not in wire
assert provider.get_tool_schemas()==[] and snapshot()==before
print(json.dumps({'native_loader':True,'native_prefetch':True,'native_composition':True,
                  'anchored_selection':True,'source_unchanged':True,'inference':False}))
'''
    result = subprocess.run([runtime, '-B', '-c', worker], env=env, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report['native_loader'] and report['native_composition'] and report['source_unchanged']
