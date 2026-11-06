"""Manage this Mac login session's SSH tunnel without depending on a terminal."""
import argparse
import os
from pathlib import Path
import plistlib
import subprocess
import sys

LABEL = 'dev.anydesk-web.ssh-tunnel'
ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('start', 'stop', 'status'))
    args = parser.parse_args()
    if sys.platform != 'darwin':
        parser.error('Este gerenciador exige macOS.')
    domain = f'gui/{os.getuid()}'
    service = f'{domain}/{LABEL}'
    probe = subprocess.run(['launchctl', 'print', service], capture_output=True, text=True)
    if args.action == 'status':
        print(probe.stdout if probe.returncode == 0 else 'Túnel não registrado.')
        return probe.returncode
    if args.action == 'stop':
        if probe.returncode == 0:
            subprocess.run(['launchctl', 'bootout', service], check=True)
        print('Túnel parado; a ponte e as sessões Windows foram preservadas.')
        return 0
    if probe.returncode == 0:
        print('Túnel já gerenciado pelo macOS. Use status para consultar o processo.')
        return 0
    runtime = ROOT / '.runtime'
    runtime.mkdir(exist_ok=True)
    path = runtime / 'ssh-tunnel.plist'
    config = {
        'Label': LABEL,
        'ProgramArguments': ['/usr/bin/ssh', '-N', '-o', 'BatchMode=yes',
                             '-o', 'ConnectTimeout=10', '-o', 'ExitOnForwardFailure=yes',
                             '-o', 'ServerAliveInterval=15', '-o', 'ServerAliveCountMax=3',
                             '-L', '127.0.0.1:8765:127.0.0.1:8765', 'marcos@10.0.2.141'],
        'RunAtLoad': True, 'KeepAlive': True, 'ThrottleInterval': 10,
        'StandardErrorPath': str(runtime / 'ssh-tunnel.log'),
        'StandardOutPath': str(runtime / 'ssh-tunnel.log'),
    }
    path.write_bytes(plistlib.dumps(config))
    subprocess.run(['launchctl', 'bootstrap', domain, str(path)], check=True)
    print('Túnel supervisionado nesta sessão do Mac. URL: http://127.0.0.1:8765')
    return 0


if __name__ == '__main__':
    sys.exit(main())
