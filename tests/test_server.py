import asyncio
import unittest
import aiohttp
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
from bridge.server import create_app, STATE


class Agent:
    def __init__(self):
        self.ids = []
        self.events = []
        self.releases = 0
        self.closed = False
    def status(self):
        return {'available': True, 'focused': True, 'armed': False, 'size': [100, 50], 'message': 'preview'}
    def frame(self):
        return {'jpeg': b'jpeg', 'width': 100, 'height': 50, 'geometry': 'window:100:50'}
    def connect(self, remote_id): self.ids.append(remote_id)
    def activate(self): pass
    def input(self, event, geometry=None): self.events.append((event, geometry))
    def release(self): self.releases += 1
    def disconnect(self): self.release()
    def close(self): self.closed = True


class ServerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.agent = Agent()
        self.app = create_app(self.agent, 'test-only-passphrase', 'http://127.0.0.1:8765')
        self.client = TestClient(TestServer(self.app), cookie_jar=aiohttp.CookieJar(unsafe=True))
        await self.client.start_server()
        self.origin = str(self.client.make_url('/')).rstrip('/')
        self.app[STATE].origin = self.origin
        self.headers = {'Origin': self.origin}
    async def asyncTearDown(self):
        await self.client.close()
    async def login(self):
        r = await self.client.post('/api/login', json={'password': 'test-only-passphrase'}, headers=self.headers)
        self.assertEqual(r.status, 200)
    async def ws(self):
        return await self.client.ws_connect('/ws', headers=self.headers)
    async def until(self, ws, kind):
        for _ in range(20):
            m = await ws.receive(timeout=2)
            if m.type == aiohttp.WSMsgType.TEXT:
                data = m.json()
                if data['type'] == kind:
                    return data
        self.fail(f'No {kind} message')

    async def test_auth_and_origin_are_required_for_control(self):
        self.assertEqual((await self.client.get('/api/status')).status, 401)
        r = await self.client.post('/api/login', json={'password': 'test-only-passphrase'}, headers={'Origin': 'https://foreign.test'})
        self.assertEqual(r.status, 403)
        with self.assertRaises(aiohttp.WSServerHandshakeError):
            await self.ws()
        await self.login()
        self.assertEqual((await self.client.get('/api/status')).status, 200)
        with self.assertRaises(aiohttp.WSServerHandshakeError):
            await self.client.ws_connect('/ws', headers={'Origin': 'https://foreign.test'})

    async def test_invalid_id_does_not_reach_process_boundary(self):
        await self.login()
        ws = await self.ws()
        await ws.send_json({'type': 'connect', 'id': '123;calc'})
        await self.until(ws, 'error')
        self.assertEqual(self.agent.ids, [])
        await ws.send_json({'type': 'connect', 'id': '123 456 789'})
        await self.until(ws, 'notice')
        self.assertEqual(self.agent.ids, ['123456789'])
        await ws.close()

    async def test_only_one_controller_and_close_releases(self):
        await self.login()
        ws = await self.ws()
        with self.assertRaises(aiohttp.WSServerHandshakeError) as ctx:
            await self.ws()
        self.assertEqual(ctx.exception.status, 409)
        await ws.close()
        await asyncio.sleep(.05)
        self.assertGreater(self.agent.releases, 0)
        next_ws = await self.ws()
        await next_ws.close()

    async def test_stale_geometry_rejected(self):
        await self.login()
        ws = await self.ws()
        await self.until(ws, 'frame')
        await ws.send_json({'type': 'input', 'geometry': 'old', 'event': {'type': 'key', 'code': 'KeyA', 'down': True}})
        await self.until(ws, 'error')
        self.assertEqual(self.agent.events, [])
        await ws.close()

    async def test_malformed_message_rejected_without_crash(self):
        await self.login()
        ws = await self.ws()
        await ws.send_str('[]')
        await self.until(ws, 'error')
        await ws.send_str('{')
        await self.until(ws, 'error')
        await ws.send_json({'type': 'status'})
        await self.until(ws, 'status')
        await ws.close()

    async def test_login_throttles_and_logout_revokes(self):
        for _ in range(5):
            await self.client.post('/api/login', json={'password': 'wrong'}, headers=self.headers)
        r = await self.client.post('/api/login', json={'password': 'wrong'}, headers=self.headers)
        self.assertEqual(r.status, 429)

    async def test_logout_closes_controller_and_revokes_cookie(self):
        await self.login()
        ws = await self.ws()
        r = await self.client.post('/api/logout', headers=self.headers)
        self.assertEqual(r.status, 200)
        self.assertEqual((await self.client.get('/api/status')).status, 401)
        self.assertGreater(self.agent.releases, 0)
        await ws.close()

    async def test_oversized_message_closes_and_releases(self):
        await self.login()
        ws = await self.ws()
        await ws.send_str('x' * 5000)
        for _ in range(10):
            msg = await ws.receive(timeout=2)
            if msg.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                break
        await ws.close()
        await asyncio.sleep(.05)
        self.assertGreater(self.agent.releases, 0)

    async def test_frame_ack_provides_backpressure(self):
        await self.login()
        ws = await self.ws()
        first = await self.until(ws, 'frame')
        await ws.send_json({'type': 'ack', 'id': first['id']})
        second = await self.until(ws, 'frame')
        self.assertGreater(second['id'], first['id'])
        await ws.close()

    async def test_expired_session_cannot_send_input(self):
        await self.login()
        ws = await self.ws()
        self.app[STATE].sessions.clear()
        await ws.send_json({'type': 'input', 'geometry': 'window:100:50', 'event': {'type': 'key', 'code': 'KeyA', 'down': True}})
        await asyncio.sleep(.1)
        self.assertEqual(self.agent.events, [])
        await ws.close()
