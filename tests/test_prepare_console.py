import importlib.util
from pathlib import Path
import types
import unittest
from unittest.mock import Mock, patch

spec = importlib.util.spec_from_file_location('prepare_console', Path(__file__).resolve().parents[1] / 'scripts/prepare-console.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ConsolePreparationTests(unittest.TestCase):
    def run_helper(self, other_user='', success=True):
        wts = types.SimpleNamespace(WTSUserName=1, WTSDomainName=2, WTSConnectState=3,
                                    WTSWinStationName=4, WTSActive=0)
        wts.WTSEnumerateSessions = Mock(return_value=[
            {'SessionId': 1, 'WinStationName': '', 'State': 4},
            {'SessionId': 3, 'WinStationName': 'Console', 'State': 1}])
        def query(server, sid, kind):
            return {1: ('ti-it' if sid == 1 else other_user), 2: 'TI-LOCAL', 3: 0, 4: 'Console'}[kind]
        wts.WTSQuerySessionInformation = query
        api = Mock()
        api.WTSConnectSessionW.return_value = success
        with patch.dict('sys.modules', {'win32ts': wts}), patch.object(module.sys, 'platform', 'win32'), patch.object(module.sys, 'argv', ['prepare-console.py']), patch.object(module.getpass, 'getpass', return_value='test-only') as password, patch.object(module.ctypes, 'WinDLL', return_value=api, create=True), patch.object(module.ctypes, 'get_last_error', return_value=1326, create=True), patch.object(module.ctypes, 'FormatError', return_value='rejected', create=True):
            if other_user:
                with self.assertRaisesRegex(SystemExit, 'Outra conta'):
                    module.main()
                password.assert_not_called()
                api.WTSConnectSessionW.assert_not_called()
                return
            self.assertEqual(module.main(), 0 if success else 1)
            args = api.WTSConnectSessionW.call_args.args
            self.assertEqual(args[:2], (1, 3))
            self.assertEqual(args[2].value, '')  # mutable password buffer cleared

    def test_capitalized_console_and_secret_cleanup(self):
        self.run_helper()

    def test_authentication_failure_is_reported(self):
        self.run_helper(success=False)

    def test_other_console_user_is_preserved(self):
        self.run_helper(other_user='other')
