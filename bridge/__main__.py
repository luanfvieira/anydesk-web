import argparse
import multiprocessing
from pathlib import Path
import secrets
from aiohttp import web
from .server import create_app


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--origin', default='http://127.0.0.1:8765')
    args = parser.parse_args()
    runtime = Path(__file__).resolve().parents[1] / '.runtime'
    runtime.mkdir(exist_ok=True)
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
    web.run_app(create_app(agent, password, args.origin), host='127.0.0.1', port=args.port, access_log=None)


if __name__ == '__main__':
    multiprocessing.freeze_support()
    main()
