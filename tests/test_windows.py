import sys
import time
import unittest
from unittest.mock import patch


@unittest.skipUnless(sys.platform == 'win32', 'Native adapter regression tests run on Windows')
class WindowsTests(unittest.TestCase):
    def agent(self):
        from bridge.windows import WindowsAgent
        with patch.object(WindowsAgent, '_choose'):
            return WindowsAgent()

    def test_release_attempts_all_and_keeps_failed_keys(self):
        agent = self.agent()
        agent.keys = {'KeyA', 'KeyB'}
        agent.buttons = {0}
        calls = []
        def key(vk, down):
            calls.append(vk)
            if vk == 65:
                raise RuntimeError('rejected')
        with patch('bridge.windows.send_key', side_effect=key), patch('bridge.windows.send_mouse') as mouse:
            self.assertFalse(agent.release())
            self.assertEqual(set(calls), {65, 66})
            mouse.assert_called_once()
            self.assertEqual(agent.keys, {'KeyA'})
            self.assertEqual(agent.buttons, set())
            self.assertFalse(agent.armed)

    def test_cached_frame_cannot_refresh_capture_time(self):
        agent = self.agent()
        agent.hwnd, agent.pid = 10, 20
        agent.worker = True
        agent.pending = time.monotonic()
        agent.armed = True
        class Pipe:
            def poll(self): return True
            def recv(self): return (10, 100, 50, 100, 50, b'jpeg', time.monotonic() - 10)
            def send(self, value): pass
        agent.pipe = Pipe()
        with patch.object(agent, 'status', return_value={'available': True, 'size': [100, 50]}):
            self.assertIsNone(agent.frame())
        self.assertEqual(agent.last_frame, 0)
        self.assertFalse(agent.armed)

    def test_disconnect_never_closes_unknown_native_window(self):
        agent = self.agent()
        agent.hwnd, agent.pid = 10, 20
        agent.owned = {(10, 20)}
        with patch('bridge.windows.identity', return_value=20), patch('bridge.windows.win32gui.PostMessage') as post:
            agent.disconnect()
            post.assert_not_called()
        self.assertIn('preservada', agent.message)

    def test_select_only_verified_anydesk_window(self):
        agent = self.agent()
        with patch('bridge.windows.identity', return_value=None):
            with self.assertRaises(ValueError):
                agent.select_window(123)
        with patch('bridge.windows.identity', return_value=456), patch('bridge.windows.windows', return_value=[123]):
            agent.select_window(123)
            self.assertEqual((agent.hwnd, agent.pid), (123, 456))
            self.assertFalse(agent.armed)

    def test_activate_brings_selected_window_forward(self):
        agent = self.agent()
        agent.hwnd = 123
        foreground = [999]
        def foreground_target(hwnd):
            foreground[0] = hwnd
        with patch.object(agent, 'status', return_value={'available': True}), patch('bridge.windows.focus_window', side_effect=foreground_target, create=True), patch('bridge.windows.win32gui.GetForegroundWindow', side_effect=lambda: foreground[0]):
            agent.activate()
            self.assertTrue(agent.armed)
            self.assertEqual(foreground[0], 123)
