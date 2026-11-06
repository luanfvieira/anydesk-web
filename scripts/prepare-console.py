"""Move the existing ti-it session to the console after Windows authentication.

Run interactively on Windows. The password is held only in memory for the Windows API call; it is never
stored or placed on the command line.
"""
import argparse
import ctypes
from ctypes import wintypes
import getpass
import sys


def main():
    if sys.platform != 'win32':
        raise SystemExit('Execute este comando no Windows, em um terminal interativo.')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--password-stdin', action='store_true', help='Read password from a private stdin pipe instead of console')
    args = parser.parse_args()
    import win32ts
    sessions = win32ts.WTSEnumerateSessions(None, 1, 0)
    matches = []
    console = None
    for session in sessions:
        sid = session['SessionId']
        username = win32ts.WTSQuerySessionInformation(None, sid, win32ts.WTSUserName)
        domain = win32ts.WTSQuerySessionInformation(None, sid, win32ts.WTSDomainName)
        if session['WinStationName'].lower() == 'console':
            console = sid
        if username.lower() == 'ti-it' and domain.lower() == 'ti-local':
            matches.append(session)
        elif session['WinStationName'].lower() == 'console' and username:
            raise SystemExit('Outra conta ocupa o console. Nenhuma sessão foi alterada.')
    if len(matches) != 1:
        raise SystemExit('É necessário haver exatamente uma sessão TI-LOCAL\\ti-it já iniciada.')
    session = matches[0]
    if session['WinStationName'].lower() == 'console' and session['State'] == win32ts.WTSActive:
        print('ti-it já está ativa no console. Confira a imagem no portal.')
        return 0
    if console is None:
        raise SystemExit('Console local não encontrado. Nenhuma sessão foi alterada.')
    print('A sessão passará ao monitor local; a conexão RDP será encerrada.', flush=True)
    if args.password_stdin:
        password = sys.stdin.readline().rstrip('\r\n')
    else:
        password = getpass.getpass('Senha de TI-LOCAL\\ti-it: ')
    if not password:
        raise SystemExit('Senha vazia; nenhuma tentativa de autenticação realizada.')
    secret = ctypes.create_unicode_buffer(password)
    del password
    api = ctypes.WinDLL('wtsapi32', use_last_error=True)
    api.WTSConnectSessionW.argtypes = [wintypes.ULONG, wintypes.ULONG, wintypes.LPWSTR, wintypes.BOOL]
    api.WTSConnectSessionW.restype = wintypes.BOOL
    try:
        success = api.WTSConnectSessionW(session['SessionId'], console, secret, True)
        error = ctypes.get_last_error() if not success else 0
    finally:
        ctypes.memset(ctypes.addressof(secret), 0, ctypes.sizeof(secret))
    if not success:
        print(f'Windows não autorizou a transferência. Erro {error}: {ctypes.FormatError(error)}')
        return 1
    current = win32ts.WTSQuerySessionInformation(None, session['SessionId'], win32ts.WTSConnectState)
    station = win32ts.WTSQuerySessionInformation(None, session['SessionId'], win32ts.WTSWinStationName)
    if current != win32ts.WTSActive or station.lower() != 'console':
        raise SystemExit('Transferência solicitada, mas o estado ativo no console não foi confirmado.')
    print('Sessão ativa no console. Abra o portal para validar a imagem; controle continua manual.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
