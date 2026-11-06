import argparse
import asyncio
import multiprocessing
from pathlib import Path
import secrets
import sys
from aiohttp import web
from .server import create_app, STATE


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--origin', default='http://127.0.0.1:8765')
    args = parser.parse_args()
    runtime = Path(__file__).resolve().parents[1] / '.runtime'
    runtime.mkdir(exist_ok=True)
    if sys.stdout is None or sys.stderr is None:
        sys.stdout = sys.stderr = (runtime / 'server.log').open('a', encoding='utf-8', buffering=1)
    password_file = runtime / 'password.txt'
    if not password_file.exists():
        with password_file.open('x', encoding='utf-8') as file:
            file.write(secrets.token_urlsafe(24))
    password = password_file.read_text(encoding='utf-8').strip()
    if len(password) < 20:
        raise RuntimeError('A senha da ponte precisa ter ao menos 20 caracteres.')
    from .windows import WindowsAgent
    agent = WindowsAgent()
    print(f'Credencial local: {password_file}', flush=True)
    async def serve():
        app = create_app(agent, password, args.origin)
        runner = web.AppRunner(app, access_log=None)
        await runner.setup()
        try:
            await web.TCPSite(runner, '127.0.0.1', args.port).start()
            print(f'Ponte em http://127.0.0.1:{args.port}', flush=True)
            await app[STATE].shutdown_event.wait()
        finally:
            await runner.cleanup()
    asyncio.run(serve())


if __name__ == '__main__':
    multiprocessing.freeze_support()
    main()
