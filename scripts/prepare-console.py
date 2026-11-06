"""Move the existing ti-it session to the console after Windows authentication.

Run interactively on Windows. The password prompt belongs to tscon; this script
never reads, stores, or places a password on the command line.
"""
import subprocess
import sys


def main():
    if sys.platform != 'win32':
        raise SystemExit('Execute este comando no Windows, em um terminal interativo.')
    import win32ts
    sessions = win32ts.WTSEnumerateSessions(None, 1, 0)
    matches = []
    for session in sessions:
        sid = session['SessionId']
        username = win32ts.WTSQuerySessionInformation(None, sid, win32ts.WTSUserName)
        domain = win32ts.WTSQuerySessionInformation(None, sid, win32ts.WTSDomainName)
        if username.lower() == 'ti-it' and domain.lower() == 'ti-local':
            matches.append(session)
        elif session['WinStationName'] == 'console' and username:
            raise SystemExit('Outra conta ocupa o console. Nenhuma sessão foi alterada.')
    if len(matches) != 1:
        raise SystemExit('É necessário haver exatamente uma sessão TI-LOCAL\\ti-it já iniciada.')
    session = matches[0]
    if session['WinStationName'] == 'console' and session['State'] == win32ts.WTSActive:
        print('ti-it já está ativa no console. Confira a imagem no portal.')
        return 0
    print('O Windows pedirá a senha de TI-LOCAL\\ti-it, não a senha do portal.', flush=True)
    print('A sessão passará ao monitor local; a conexão RDP será encerrada.', flush=True)
    result = subprocess.run(['tscon.exe', str(session['SessionId']), '/dest:console', '/password:*'])
    if result.returncode:
        print('Windows não autorizou a transferência. A captura sem RDP não foi habilitada.')
        return result.returncode
    current = win32ts.WTSQuerySessionInformation(None, session['SessionId'], win32ts.WTSConnectState)
    station = win32ts.WTSQuerySessionInformation(None, session['SessionId'], win32ts.WTSWinStationName)
    if current != win32ts.WTSActive or station != 'console':
        raise SystemExit('Transferência solicitada, mas o estado ativo no console não foi confirmado.')
    print('Sessão ativa no console. Abra o portal para validar a imagem; controle continua manual.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
