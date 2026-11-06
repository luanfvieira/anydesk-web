"""Isolate WGC callback from bridge transport. Captures only the selected AnyDesk HWND."""
from pathlib import Path
from bridge.windows import WindowsAgent
from windows_capture import WindowsCapture

agent=WindowsAgent()
print('Target:', agent.hwnd, agent.status(), flush=True)
assert agent.hwnd
capture=WindowsCapture(window_hwnd=agent.hwnd, cursor_capture=True, draw_border=True)
@capture.event
def on_frame_arrived(frame, control):
    print('Direct frame:',frame.width,frame.height,flush=True)
    frame.save_as_image(str(Path(__file__).resolve().parents[1]/'.runtime/wgc-direct.png'))
    control.stop()
@capture.event
def on_closed():
    print('Direct capture closed',flush=True)
capture.start()
