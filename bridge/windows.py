"""Windows-only window capture and guarded input. Never captures the desktop."""
import ctypes
from ctypes import wintypes
from io import BytesIO
import multiprocessing as mp
import os
from pathlib import Path
import subprocess
import time

import win32api
import win32con
import win32gui
import win32process
import win32ts
from PIL import Image
from .policy import KEYS, map_point, validate_event, validate_id

EXE = Path(r'C:\Program Files (x86)\AnyDesk\AnyDesk.exe')
user32 = ctypes.WinDLL('user32', use_last_error=True)
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
kernel32.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
user32.PrintWindow.argtypes = [wintypes.HWND, wintypes.HDC, wintypes.UINT]
user32.OpenInputDesktop.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
user32.OpenInputDesktop.restype = wintypes.HANDLE
user32.CloseDesktop.argtypes = [wintypes.HANDLE]


class MI(ctypes.Structure):
    _fields_ = [('dx', wintypes.LONG), ('dy', wintypes.LONG), ('mouseData', wintypes.DWORD),
                ('dwFlags', wintypes.DWORD), ('time', wintypes.DWORD), ('dwExtraInfo', ctypes.c_size_t)]


class KI(ctypes.Structure):
    _fields_ = [('wVk', wintypes.WORD), ('wScan', wintypes.WORD), ('dwFlags', wintypes.DWORD),
                ('time', wintypes.DWORD), ('dwExtraInfo', ctypes.c_size_t)]


class IU(ctypes.Union):
    _fields_ = [('mi', MI), ('ki', KI)]


class INPUT(ctypes.Structure):
    _anonymous_ = ('u',)
    _fields_ = [('type', wintypes.DWORD), ('u', IU)]


user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]


def send_key(vk, down):
    flags = 0 if down else 2
    if vk in (33, 34, 35, 36, 37, 38, 39, 40, 45, 46, 163, 165):
        flags |= 1
    event = INPUT(type=1, ki=KI(wVk=vk, dwFlags=flags))
    if user32.SendInput(1, ctypes.byref(event), ctypes.sizeof(INPUT)) != 1:
        raise RuntimeError('Windows recusou a entrada de teclado.')


def send_mouse(flags, data=0):
    event = INPUT(type=0, mi=MI(mouseData=data & 0xffffffff, dwFlags=flags))
    if user32.SendInput(1, ctypes.byref(event), ctypes.sizeof(INPUT)) != 1:
        raise RuntimeError('Windows recusou a entrada de mouse.')


def identity(hwnd):
    if not win32gui.IsWindow(hwnd):
        return None
    _, pid = win32process.GetWindowThreadProcessId(hwnd)
    try:
        process = win32api.OpenProcess(0x1000, False, pid)
        try:
            buffer = ctypes.create_unicode_buffer(32768)
            length = wintypes.DWORD(len(buffer))
            if not kernel32.QueryFullProcessImageNameW(int(process), 0, buffer, ctypes.byref(length)):
                return None
            path = buffer.value
        finally:
            process.Close()
        if os.path.normcase(path) != os.path.normcase(str(EXE)):
            return None
        return pid
    except Exception:
        return None


def windows():
    result = []
    def visit(hwnd, _):
        if win32gui.IsWindowVisible(hwnd) and identity(hwnd):
            _, _, w, h = win32gui.GetClientRect(hwnd)
            if w >= 200 and h >= 100:
                result.append(hwnd)
    win32gui.EnumWindows(visit, None)
    return result


def capture_worker(pipe):
    """Capture exactly one HWND with WGC; never enumerate/select a monitor."""
    print("WGC worker starting", flush=True)
    from windows_capture import WindowsCapture
    print("WGC imported", flush=True)
    import threading
    dwm = ctypes.WinDLL('dwmapi')
    dwm.DwmGetWindowAttribute.argtypes = [wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD]
    target = None
    control = None
    latest = None
    diagnosed = False
    lock = threading.Lock()
    try:
        while True:
            hwnd, width, height = pipe.recv()
            if target != (hwnd, width, height):
                if control:
                    control.stop()
                target = (hwnd, width, height)
                latest = None
                capture = WindowsCapture(window_hwnd=hwnd, cursor_capture=True,
                                         draw_border=True, minimum_update_interval=100)

                @capture.event
                def on_frame_arrived(frame, capture_control):
                    nonlocal latest, diagnosed
                    try:
                        bounds = wintypes.RECT()
                        if dwm.DwmGetWindowAttribute(hwnd, 9, ctypes.byref(bounds), ctypes.sizeof(bounds)) != 0:
                            return
                        rect = (bounds.left, bounds.top, bounds.right, bounds.bottom)
                        if not diagnosed:
                            print('WGC geometry:', frame.width, frame.height, rect, win32gui.GetWindowRect(hwnd), win32gui.GetClientRect(hwnd), win32gui.ClientToScreen(hwnd, (0, 0)), flush=True)
                            diagnosed = True
                        if (frame.width, frame.height) != (rect[2]-rect[0], rect[3]-rect[1]):
                            rect = win32gui.GetWindowRect(hwnd)
                        if (frame.width, frame.height) != (rect[2]-rect[0], rect[3]-rect[1]):
                            return
                        left, top = win32gui.ClientToScreen(hwnd, (0, 0))
                        x, y = left - rect[0], top - rect[1]
                        if x < 0 or y < 0 or x + width > frame.width or y + height > frame.height:
                            return
                        pixels = frame.frame_buffer[y:y+height, x:x+width, :3][:, :, ::-1]
                        im = Image.fromarray(pixels)
                        im.thumbnail((1600, 1000))
                        output = BytesIO()
                        im.save(output, format='JPEG', quality=75)
                        value = (hwnd, width, height, im.width, im.height, output.getvalue())
                        with lock:
                            latest = value
                    except Exception:
                        with lock:
                            latest = None

                @capture.event
                def on_closed():
                    nonlocal latest
                    with lock:
                        latest = None

                control = capture.start_free_threaded()
                print("WGC started", target, flush=True)
                # First frame is asynchronous; subsequent requests read a bounded latest-frame cache.
                time.sleep(.15)
            with lock:
                value = latest
            pipe.send(value if control and not control.is_finished() else None)
    except (EOFError, BrokenPipeError):
        pass
    finally:
        if control:
            control.stop()


class WindowsAgent:
    def __init__(self):
        self.hwnd = None
        self.pid = None
        self.owned = set()
        self.keys = set()
        self.buttons = set()
        self.worker = None
        self.pipe = None
        self.pending = None
        self.before = None
        self.connect_started = 0
        self.message = 'Prévia local do AnyDesk; nenhuma conexão iniciada pela ponte.'
        self.geometry = None
        self.last_frame = 0
        self.armed = False
        self._choose()

    def _choose(self):
        candidates = windows()
        if self.before is not None:
            created = [h for h in candidates if h not in self.before]
            if len(created) == 1:
                self.release()
                self.hwnd = created[0]
                self.pid = identity(self.hwnd)
                self.owned.add((self.hwnd, self.pid))
                self.before = None
            elif time.monotonic() - self.connect_started > 10:
                self.before = None
                self.message = 'Confira a aceitação na janela do AnyDesk. A ponte não confirma o estado remoto.'
        if self.hwnd and identity(self.hwnd) == self.pid:
            return
        self.release()
        self.hwnd = candidates[0] if len(candidates) == 1 else None
        self.pid = identity(self.hwnd) if self.hwnd else None

    def _desktop_ready(self):
        handle = user32.OpenInputDesktop(0, False, 0x0100)  # DESKTOP_SWITCHDESKTOP
        if not handle:
            return False
        user32.CloseDesktop(handle)
        # A disconnected RDP session is not an interactive input destination.
        import win32ts
        session = win32ts.ProcessIdToSessionId(os.getpid())
        return win32ts.WTSQuerySessionInformation(None, session, win32ts.WTSConnectState) == 0

    def status(self):
        self._choose()
        available = bool(self.hwnd and win32gui.IsWindowVisible(self.hwnd)
                         and not win32gui.IsIconic(self.hwnd) and self._desktop_ready())
        focused = bool(available and win32gui.GetForegroundWindow() == self.hwnd)
        if not focused:
            self.release()
        size = list(win32gui.GetClientRect(self.hwnd)[2:]) if available else None
        return {'available': available, 'focused': focused, 'armed': self.armed,
                'title': win32gui.GetWindowText(self.hwnd) if available else '',
                'size': size, 'message': self.message if available else 'Janela AnyDesk indisponível, minimizada ou sessão bloqueada.',
                'remote_state': 'unverified'}

    def _reset_worker(self):
        if self.worker:
            self.worker.terminate()
            self.worker.join(timeout=1)
        if self.pipe:
            self.pipe.close()
        self.worker = self.pipe = self.pending = None

    def frame(self):
        status = self.status()
        if not status['available']:
            self.geometry = None
            return None
        width, height = status['size']
        if not 1 <= width <= 7680 or not 1 <= height <= 4320:
            return None
        if not self.worker:
            self.pipe, child = mp.Pipe()
            self.worker = mp.Process(target=capture_worker, args=(child,), daemon=True)
            self.worker.start()
            child.close()
        result = None
        if self.pending and self.pipe.poll():
            captured = self.pipe.recv()
            self.pending = None
            if captured:
                hwnd, w, h, fw, fh, jpeg = captured
                if hwnd == self.hwnd and (w, h) == (width, height):
                    self.geometry = (hwnd, self.pid, w, h)
                    self.last_frame = time.monotonic()
                    result = {'jpeg': jpeg, 'width': fw, 'height': fh,
                              'geometry': f'{hwnd}:{self.pid}:{w}:{h}'}
        if self.pending and time.monotonic() - self.pending > 10:
            self.release()
            self._reset_worker()
            raise RuntimeError('Captura demorou demais; entrada suspensa.')
        if not self.pending and self.pipe:
            self.pipe.send((self.hwnd, width, height))
            self.pending = time.monotonic()
        return result

    def connect(self, remote_id):
        remote_id = validate_id(remote_id)
        self.release()
        if self.before is not None:
            raise ValueError('Aguarde a solicitação anterior.')
        self.before = set(windows())
        self.connect_started = time.monotonic()
        subprocess.Popen([str(EXE), remote_id, '--plain'], close_fds=True)
        self.message = 'Conexão solicitada. Aguarde a aceitação e confira a imagem do AnyDesk.'

    def activate(self):
        if not self.status()['available']:
            raise ValueError('Janela indisponível.')
        # Do not steal focus using undocumented Alt-key injection or AttachThreadInput.
        try:
            win32gui.SetForegroundWindow(self.hwnd)
        except Exception:
            pass
        if win32gui.GetForegroundWindow() != self.hwnd:
            raise ValueError('Clique na janela do AnyDesk no Windows para permitir o controle.')
        self.armed = True

    def input(self, event, geometry=None):
        event = validate_event(event)
        state = self.status()
        current = (self.hwnd, self.pid, *(state['size'] or (0, 0)))
        expected = ':'.join(map(str, current))
        if not self.armed or not state['focused'] or self.geometry != current or geometry != expected or time.monotonic() - self.last_frame > 2:
            self.release()
            raise ValueError('Controle suspenso: foco ou imagem mudou. Ative novamente.')
        kind = event['type']
        if kind == 'key':
            code, down = event['code'], event['down']
            # These combinations could activate the Windows shell instead of the remote session.
            if down and ((self.keys & {'AltLeft', 'AltRight'} and code in ('Tab', 'Escape', 'F4')) or
                         (self.keys & {'ControlLeft', 'ControlRight'} and code == 'Escape')):
                self.release()
                raise ValueError('Atalho reservado pelo Windows da ponte.')
            send_key(KEYS[code], down)
            (self.keys.add if down else self.keys.discard)(code)
            return
        width, height = state['size']
        x, y = map_point(event['x'], event['y'], width, height)
        point = win32gui.ClientToScreen(self.hwnd, (x, y))
        hit = win32gui.WindowFromPoint(point)
        if win32gui.GetAncestor(hit, 2) != self.hwnd:
            self.release()
            raise ValueError('Outra janela cobre o ponto selecionado.')
        win32api.SetCursorPos(point)
        if win32gui.GetForegroundWindow() != self.hwnd:
            self.release()
            raise ValueError('A janela perdeu o foco.')
        if kind == 'button':
            button, down = event['button'], event['down']
            flags = {0: (2, 4), 1: (32, 64), 2: (8, 16)}[button]
            send_mouse(flags[0 if down else 1])
            (self.buttons.add if down else self.buttons.discard)(button)
        elif kind == 'wheel':
            send_mouse(0x0800, -int(event['delta']))

    def release(self):
        self.armed = False
        for code in list(self.keys):
            try:
                send_key(KEYS[code], False)
            finally:
                self.keys.discard(code)
        for button in list(self.buttons):
            try:
                send_mouse({0: 4, 1: 64, 2: 16}[button])
            finally:
                self.buttons.discard(button)

    def disconnect(self):
        self.release()
        if self.hwnd and (self.hwnd, self.pid) in self.owned and identity(self.hwnd) == self.pid:
            win32gui.PostMessage(self.hwnd, win32con.WM_CLOSE, 0, 0)
            self.owned.discard((self.hwnd, self.pid))
            self.message = 'Encerramento solicitado à janela criada pela ponte.'
        else:
            self.message = 'Controle encerrado. A janela compartilhada do AnyDesk foi preservada.'
        self.before = None
        self.geometry = None

    def close(self):
        self.release()
        self._reset_worker()
