"""Local cooperative stop: authenticate, release inputs, then request process exit."""
from http.cookiejar import CookieJar
import json
from pathlib import Path
import sys
import urllib.error
import urllib.request

root = Path(__file__).resolve().parents[1]
port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
origin = f'http://127.0.0.1:{port}'
client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))
password = (root / '.runtime/password.txt').read_text().strip()
for path, data in [('/api/login', {'password': password}), ('/api/shutdown', {})]:
    request = urllib.request.Request(origin + path, json.dumps(data).encode(),
                                     {'Content-Type': 'application/json', 'Origin': origin})
    try:
        with client.open(request, timeout=10) as response:
            result = json.load(response)
    except (urllib.error.URLError, TimeoutError) as error:
        print(f'Encerramento não confirmado ({type(error).__name__}); processo preservado.', file=sys.stderr)
        sys.exit(1)
print('Liberação de entrada confirmada; encerramento solicitado.')
