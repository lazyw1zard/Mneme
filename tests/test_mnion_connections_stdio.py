"""Real MCP stdio verification, entirely inside disposable neutral state."""
import asyncio
import json
import os
from pathlib import Path
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from test_mnion_connections import A,B,C,MEANING,state,snapshot


def test_real_stdio_connected_fragment_and_retry(tmp_path):
    fixture=tmp_path/'state';state(fixture,project=False)
    before=snapshot(fixture)
    env=os.environ.copy()
    for name in list(env):
        if name.startswith(('MNEME_','HERMES_','XDG_')):env.pop(name)
    for name,folder in [('HOME','home'),('HERMES_HOME','hermes'),('XDG_STATE_HOME','xdg-state'),
                        ('XDG_CONFIG_HOME','xdg-config'),('XDG_DATA_HOME','xdg-data'),
                        ('XDG_CACHE_HOME','xdg-cache'),('TMPDIR','tmp')]:
        path=tmp_path/folder;path.mkdir();env[name]=str(path)
    env.update(MNEME_STATE_DIR=str(fixture),MNEME_CONFIG=str(fixture/'config.toml'),
               PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(Path(__file__).resolve().parents[1]/'src'))
    async def exercise():
        params=StdioServerParameters(command=sys.executable,args=['-B','-m','mnion.mcp_server'],env=env,cwd=str(tmp_path))
        async with stdio_client(params) as (reader,writer):
            async with ClientSession(reader,writer) as session:
                await session.initialize()
                tools={t.name for t in (await session.list_tools()).tools}
                assert tools=={'capture','consolidate_review','list_topics','get_item','annotate_claim','connect_items','get_neighborhood'}
                async def call(name,**args):
                    response=await session.call_tool(name,args)
                    assert not getattr(response,'isError',getattr(response,'is_error',False))
                    structured=getattr(response,'structuredContent',getattr(response,'structured_content',None))
                    return structured if structured is not None else json.loads(response.content[0].text)
                invalid=await call('connect_items',source_review_id=B+' ',target_review_id=A,
                                   relation_kind='corrects',relation_summary=MEANING)
                assert not invalid['ok'] and snapshot(fixture)==before
                originals={r:(await call('get_item',review_id=r))['item'] for r in (A,B,C)}
                edge=await call('connect_items',source_review_id=B,target_review_id=A,
                                 relation_kind='corrects',relation_summary=MEANING)
                assert edge['ok']
                edge2=await call('connect_items',source_review_id=C,target_review_id=B,
                                  relation_kind='follows_from',relation_summary='The next choice follows the correction.')
                assert edge2['ok']
                projected=snapshot(fixture)
                arc=await call('get_neighborhood',exact_item_route=A,depth=2,limit=4)
                assert arc['ok'] and len(arc['connections'])==2 and len(arc['nodes'])==3 and not arc['has_more']
                assert snapshot(fixture)==projected
                retry=await call('connect_items',source_review_id=B,target_review_id=A,
                                  relation_kind='corrects',relation_summary=MEANING,
                                  retry_connection_id=edge['connection']['id'])
                assert retry['ok'] and retry['reused_connection'] and snapshot(fixture)==projected
                for r in (A,B,C):assert (await call('get_item',review_id=r))['item']==originals[r]
                for name in ('micro_consolidation_reviews.jsonl','memory_tags.jsonl','mneme_seq.json','config.toml'):
                    assert snapshot(fixture)[name]==before[name]
                print('CONNECTION MCP STDIO: tools=7 nodes=3 edges=2 retries=no_append originals=unchanged')
    asyncio.run(exercise())
