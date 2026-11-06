"""Authenticated, loopback-only transport for one interactive controller."""
import asyncio
from collections import deque
from dataclasses import dataclass, field
import hashlib
import hmac
import json
from pathlib import Path
import secrets
import time
from urllib.parse import urlsplit

from aiohttp import web, WSMsgType
from .policy import validate_event, validate_id

WEB = Path(__file__).resolve().parents[1] / 'web'
COOKIE = 'bridge_session'
SESSION_TTL = 1800


@dataclass
class State:
    agent: object
    password_hash: bytes
    origin: str
    sessions: dict = field(default_factory=dict)
    failures: deque = field(default_factory=deque)
    controller: object = None
    controller_token: str | None = None
    release_fault: bool = False
    stopping: bool = False
    shutdown_event: asyncio.Event = field(default_factory=asyncio.Event)

    def release(self):
        try:
            self.release_fault = self.agent.release() is False
        except Exception:
            self.release_fault = True
        return not self.release_fault

    def session(self, token):
        now = time.monotonic()
        self.sessions = {k: v for k, v in self.sessions.items() if now - v < SESSION_TTL}
        return bool(token and token in self.sessions)


STATE = web.AppKey('state', State)
TOKEN = web.RequestKey('token', str)


@web.middleware
async def guard(request, handler):
    state = request.app[STATE]
    if request.host != urlsplit(state.origin).netloc:
        raise web.HTTPForbidden(text='Host inválido.')
    supplied = request.headers.get('Origin')
    if (supplied and supplied != state.origin) or (request.method != 'GET' or request.path == '/ws') and supplied != state.origin:
        raise web.HTTPForbidden(text='Origem inválida.')
    if request.path.startswith('/api/') and request.path != '/api/login' or request.path == '/ws':
        token = request.cookies.get(COOKIE)
        if not state.session(token):
            raise web.HTTPUnauthorized(text='Entre para acessar a ponte.')
        request[TOKEN] = token
    try:
        response = await handler(request)
    except web.HTTPException as error:
        response = error
    response.headers.update({'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
        'Referrer-Policy': 'no-referrer', 'X-Frame-Options': 'DENY',
        'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' blob:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"})
    if isinstance(response, web.HTTPException):
        raise response
    return response


async def login(request):
    state = request.app[STATE]
    now = time.monotonic()
    while state.failures and now - state.failures[0] > 60:
        state.failures.popleft()
    if len(state.failures) >= 5:
        raise web.HTTPTooManyRequests(text='Aguarde um minuto para tentar novamente.')
    try:
        body = await request.json()
        password = body.get('password') if isinstance(body, dict) else None
    except (ValueError, TypeError):
        password = None
    digest = hashlib.sha256(password.encode()).digest() if isinstance(password, str) else b''
    if not hmac.compare_digest(digest, state.password_hash):
        state.failures.append(now)
        raise web.HTTPUnauthorized(text='Senha incorreta.')
    state.session(None)  # prune expired credentials
    if len(state.sessions) >= 20:
        raise web.HTTPTooManyRequests(text='Muitas sessões abertas.')
    token = secrets.token_urlsafe(32)
    state.sessions[token] = now
    response = web.json_response({'ok': True})
    response.set_cookie(COOKIE, token, httponly=True, samesite='Strict',
                        secure=state.origin.startswith('https:'), max_age=SESSION_TTL, path='/')
    return response


async def logout(request):
    state = request.app[STATE]
    state.sessions.pop(request[TOKEN], None)
    if state.controller_token == request[TOKEN] and state.controller is not None:
        state.release()
        await state.controller.close()
    response = web.json_response({'ok': True})
    response.del_cookie(COOKIE, path='/')
    return response


async def status(request):
    return web.json_response(request.app[STATE].agent.status())


async def socket(request):
    state = request.app[STATE]
    if state.stopping or state.release_fault and not state.release():
        raise web.HTTPServiceUnavailable(text='Controle indisponível; verifique a sessão Windows.')
    if state.controller is not None:
        raise web.HTTPConflict(text='A ponte já está em uso por outro navegador.')
    ws = web.WebSocketResponse(max_msg_size=4096, heartbeat=5, compress=False)
    state.controller = ws  # reserve before await: handshake cannot race another controller
    state.controller_token = request[TOKEN]
    ticker = None
    last_ping = time.monotonic()
    outstanding = None
    geometry = None
    frame_time = 0
    sequence = 0
    rate = deque()
    send_lock = asyncio.Lock()
    viewing = True

    async def emit(data):
        async with send_lock:
            await asyncio.wait_for(ws.send_json(data), 2)

    async def tick():
        nonlocal outstanding, geometry, frame_time, sequence
        last_status = 0
        try:
            while not ws.closed:
                now = time.monotonic()
                if state.stopping or not state.session(request[TOKEN]):
                    await ws.close(code=1008, message=b'Session expired')
                    return
                if now - last_ping > 2:
                    state.release()
                if now - last_ping > 5:
                    await ws.close(code=1008, message=b'Heartbeat missing')
                    return
                current = state.agent.status()  # also enforces focus/lock guards every 100ms
                if now - last_status >= 1:
                    await emit({'type': 'status', **current})
                    last_status = now
                if viewing and outstanding is None:
                    frame = state.agent.frame()
                    if frame:
                        sequence += 1
                        outstanding = sequence
                        geometry = frame['geometry']
                        frame_time = frame.get('captured_at', now)
                        async with send_lock:
                            await asyncio.wait_for(ws.send_json({'type': 'frame', 'id': sequence,
                                'width': frame['width'], 'height': frame['height'], 'geometry': geometry}), 2)
                            await asyncio.wait_for(ws.send_bytes(frame['jpeg']), 2)
                if frame_time and now - frame_time > 2:
                    state.release()
                await asyncio.sleep(.1)
        except asyncio.CancelledError:
            raise
        except Exception:
            state.release()
            if not ws.closed:
                try:
                    await emit({'type': 'error', 'message': 'Captura indisponível. Reconecte a prévia.'})
                finally:
                    await ws.close(code=1011)

    try:
        await ws.prepare(request)
        ticker = asyncio.create_task(tick())
        await emit({'type': 'notice', 'message': 'Prévia do AnyDesk. A aceitação remota será exibida na própria janela.'})
        async for message in ws:
            if message.type != WSMsgType.TEXT:
                if message.type == WSMsgType.BINARY:
                    await ws.close(code=1003)
                continue
            now = time.monotonic()
            while rate and now - rate[0] > 1:
                rate.popleft()
            rate.append(now)
            if len(rate) > 200:
                state.release()
                await ws.close(code=1008, message=b'Rate exceeded')
                break
            try:
                if state.stopping or not state.session(request[TOKEN]):
                    raise ValueError('Sessão expirada. Entre novamente.')
                data = json.loads(message.data)
                if not isinstance(data, dict) or not isinstance(data.get('type'), str):
                    raise ValueError('Mensagem inválida.')
                kind = data['type']
                if kind == 'ping':
                    last_ping = now
                elif kind == 'ack':
                    if type(data.get('id')) is int and data['id'] == outstanding:
                        outstanding = None
                elif kind == 'status':
                    await emit({'type': 'status', **state.agent.status()})
                elif kind == 'release':
                    state.release()
                elif kind == 'select':
                    handle = data.get('window')
                    if not isinstance(handle, str) or not handle.isascii() or not handle.isdigit() or len(handle) > 20:
                        raise ValueError('Janela inválida.')
                    state.agent.select_window(int(handle))
                    geometry = None
                    outstanding = None
                    await emit({'type': 'notice', 'message': 'Janela selecionada. Aguarde a imagem.'})
                elif kind == 'connect':
                    state.agent.connect(validate_id(data.get('id')))
                    geometry = None
                    await emit({'type': 'notice', 'message': 'Solicitação enviada ao AnyDesk. Confira a aceitação na imagem.'})
                elif kind == 'activate':
                    if geometry is None or now - frame_time > 2:
                        raise ValueError('Sem imagem recente do Windows; controle indisponível.')
                    state.agent.activate()
                    await emit({'type': 'status', **state.agent.status()})
                elif kind == 'input':
                    if data.get('geometry') != geometry or geometry is None or now - frame_time > 2:
                        raise ValueError('Imagem desatualizada; controle suspenso.')
                    state.agent.input(validate_event(data.get('event')), geometry=geometry)
                elif kind == 'disconnect':
                    viewing = False
                    state.agent.disconnect()
                    await emit({'type': 'notice', 'message': state.agent.status().get('message', 'Controle encerrado.')})
                    await ws.close()
                    break
                else:
                    raise ValueError('Comando desconhecido.')
                if kind not in ('ping', 'ack', 'status'):
                    state.sessions[request[TOKEN]] = now
            except (ValueError, TypeError, KeyError, RuntimeError) as error:
                state.release()
                await emit({'type': 'error', 'message': str(error)[:180]})
    finally:
        # Release synchronously: aiohttp can cancel the handler on disconnect.
        state.release()
        if ticker:
            ticker.cancel()
        try:
            state.agent.disconnect()
        except Exception:
            state.release_fault = True
        if state.controller is ws:
            state.controller = None
            state.controller_token = None
        if ticker:
            ticker.cancel()
            await asyncio.gather(ticker, return_exceptions=True)
    return ws


async def shutdown(request):
    state = request.app[STATE]
    state.stopping = True
    if not state.release():
        state.stopping = False
        raise web.HTTPServiceUnavailable(text='Windows não confirmou a liberação das entradas; servidor mantido ativo.')
    asyncio.get_running_loop().call_later(.1, state.shutdown_event.set)
    return web.json_response({'ok': True, 'input_released': True})


async def asset(request):
    filename = request.match_info.get('name', 'index.html')
    if filename not in {'index.html', 'app.js', 'style.css'}:
        raise web.HTTPNotFound()
    return web.FileResponse(WEB / filename)


def create_app(agent, password, origin):
    app = web.Application(middlewares=[guard], client_max_size=4096)
    app[STATE] = State(agent, hashlib.sha256(password.encode()).digest(), origin.rstrip('/'))
    app.router.add_post('/api/login', login)
    app.router.add_post('/api/logout', logout)
    app.router.add_post('/api/shutdown', shutdown)
    app.router.add_get('/api/status', status)
    app.router.add_get('/ws', socket)
    app.router.add_get('/', asset)
    app.router.add_get('/{name}', asset)
    async def cleanup(app):
        state = app[STATE]
        if state.controller is not None:
            await state.controller.close(code=1001)
        agent.close()
    app.on_shutdown.append(cleanup)
    return app
