"""Run inside the approved session; never connects to a remote ID."""
import json
import argparse
from pathlib import Path
import time
from PIL import Image, ImageStat
from io import BytesIO
from bridge.windows import WindowsAgent


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument('--hwnd', type=int)
    args = parser.parse_args()
    agent = WindowsAgent()
    if args.hwnd:
        from bridge.windows import identity
        assert identity(args.hwnd), 'Selected window is not AnyDesk'
        agent.hwnd, agent.pid = args.hwnd, identity(args.hwnd)
    try:
        status = agent.status()
        if agent.hwnd:
            import ctypes
            from ctypes import wintypes
            affinity=wintypes.DWORD()
            ctypes.windll.user32.GetWindowDisplayAffinity(agent.hwnd, ctypes.byref(affinity))
            cloaked=wintypes.DWORD()
            ctypes.windll.dwmapi.DwmGetWindowAttribute(agent.hwnd,14,ctypes.byref(cloaked),4)
            print('Window flags:', affinity.value, cloaked.value, flush=True)
        if not status['available']:
            import win32gui, win32ts, os
            from bridge.windows import identity, windows
            details=[]
            def visit(h, _):
                if identity(h):
                    details.append({'hwnd':h,'title':win32gui.GetWindowText(h),'visible':bool(win32gui.IsWindowVisible(h)),'minimized':bool(win32gui.IsIconic(h)),'client':win32gui.GetClientRect(h)})
            win32gui.EnumWindows(visit,None)
            print(json.dumps({'candidates':windows(),'windows':details,'session':win32ts.ProcessIdToSessionId(os.getpid())}), flush=True)
        assert status['available'], status
        frame = None
        deadline = time.monotonic() + 20
        while frame is None and time.monotonic() < deadline:
            frame = agent.frame()
            time.sleep(.1)
        assert frame and frame['jpeg'], 'Window capture unavailable'
        im = Image.open(BytesIO(frame['jpeg']))
        im.save(root / '.runtime' / 'probe.png')
        assert max(ImageStat.Stat(im.crop((50, 80, im.width-50, im.height-30))).stddev) > 5, 'Blank client content despite nonblank window frame'
        im.save(root / '.runtime' / 'probe.png')
        print(json.dumps({'status': status, 'size': im.size, 'capture': 'window-only', 'stddev': ImageStat.Stat(im).stddev}))
    finally:
        agent.close()


if __name__ == '__main__':
    main()
