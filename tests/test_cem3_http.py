"""Real local HTTP sockets with an ephemeral test port, never a physical rack."""
import asyncio
from pathlib import Path
import aiohttp
from aiohttp import web
import pytest
from custom_components.dmx_monitor import etc_cem3 as cem

F=Path(__file__).parent/'fixtures/cem3'
DATA={key:(F/name).read_text() for key,name in [('system','system.html'),('levels','levels.xml'),('properties','properties.xml'),('spaces','spaces.xml')]}


@pytest.mark.asyncio
async def test_real_http_exact_requests_binding_closure_and_reload(monkeypatch):
    calls=[]
    async def handler(request):
        body=await request.text();calls.append((request.method,request.path,body,request.transport.get_extra_info('peername')[0]))
        kind='system' if request.path=='/index.asp' else next(k for k,v in cem.READ_QUERIES.items() if body==v)
        return web.Response(text=DATA[kind],content_type='text/html')
    app=web.Application();app.router.add_route('*','/{path:.*}',handler)
    runner=web.AppRunner(app);await runner.setup();site=web.TCPSite(runner,'127.0.0.1',0);await site.start()
    port=site._server.sockets[0].getsockname()[1]
    original=aiohttp.ClientSession;sessions=[]
    class PortSession:
        def __init__(self,**kw):self.session=original(**kw);sessions.append(self.session)
        def request(self,method,url,**kw):
            assert url.startswith('http://127.0.0.1/')
            return self.session.request(method,url.replace('http://127.0.0.1/',f'http://127.0.0.1:{port}/'),**kw)
        @property
        def closed(self):return self.session.closed
        async def close(self):await self.session.close()
    monkeypatch.setattr(cem.aiohttp,'ClientSession',PortSession)
    try:
        for _ in range(2):
            m=cem.CEM3WebMonitor(['127.0.0.1'],source_ip='127.0.0.1')
            row=await m._poll('127.0.0.1','127.0.0.1')
            assert row.online and row.dimmers['circuits_total']==72
            with pytest.raises(ValueError):await m._request('127.0.0.1','set_levels','127.0.0.1')
            await m.stop()
        assert all(s.closed for s in sessions)
        assert [(x[0],x[1],x[2]) for x in calls[:4]]==[('GET','/index.asp','')]+[('POST','/dimmerlist',cem.READ_QUERIES[k]) for k in ('levels','properties','spaces')]
        assert all(x[3]=='127.0.0.1' for x in calls)
    finally:await runner.cleanup()


@pytest.mark.asyncio
@pytest.mark.parametrize('mode',['redirect','oversize','timeout'])
async def test_real_http_rejects_redirect_oversize_and_timeout(monkeypatch,mode):
    calls=[]
    async def handler(request):
        calls.append(request.path)
        if mode=='redirect':raise web.HTTPFound('/write_config')
        if mode=='oversize':return web.Response(body=b'x'*(cem.MAX_BODY+1))
        await asyncio.sleep(.7);return web.Response(text='slow')
    app=web.Application();app.router.add_route('*','/{path:.*}',handler)
    runner=web.AppRunner(app);await runner.setup();site=web.TCPSite(runner,'127.0.0.1',0);await site.start()
    port=site._server.sockets[0].getsockname()[1];original=aiohttp.ClientSession
    class PortSession:
        def __init__(self,**kw):self.session=original(**kw)
        def request(self,method,url,**kw):return self.session.request(method,url.replace('127.0.0.1/',f'127.0.0.1:{port}/'),**kw)
        @property
        def closed(self):return self.session.closed
        async def close(self):await self.session.close()
    monkeypatch.setattr(cem.aiohttp,'ClientSession',PortSession)
    m=cem.CEM3WebMonitor(['127.0.0.1'],timeout=.5)
    try:
        with pytest.raises((ValueError,OSError,asyncio.TimeoutError)):
            await m._request('127.0.0.1','system',None)
        assert calls==['/index.asp']
    finally:await m.stop();await runner.cleanup()
