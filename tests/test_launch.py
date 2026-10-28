"""Repository launcher and default dashboard entry point regression checks."""
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

import run
from sss_pdf.cli import main


class LaunchTests(unittest.TestCase):
    def test_no_command_opens_dashboard(self):
        with patch('sss_pdf.web.main') as serve:
            self.assertEqual(main([]), 0)
            serve.assert_called_once_with(host='127.0.0.1', port=8765, open_browser=True)

    def test_server_can_run_without_browser_for_ci(self):
        with patch('sss_pdf.web.main') as serve:
            self.assertEqual(main(['serve', '--no-browser', '--port', '9876']), 0)
            serve.assert_called_once_with(host='127.0.0.1', port=9876, open_browser=False)

    def test_first_launch_installs_once_then_starts_web(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'pyproject.toml').write_text('[project]\nname="example"\n')
            def create_environment(environment):
                python = environment / ('Scripts/python.exe' if run.sys.platform == 'win32' else 'bin/python')
                python.parent.mkdir(parents=True)
                python.touch()
            with patch.object(run, 'ROOT', root), patch('run.venv.EnvBuilder') as builder, patch('run.subprocess.run') as install, patch('run.subprocess.call', return_value=0) as launch:
                builder.return_value.create.side_effect = create_environment
                self.assertEqual(run.main(['--no-browser', '--port', '9876']), 0)
                self.assertEqual(run.main(['--install-only']), 0)
                builder.return_value.create.assert_called_once()
                install.assert_called_once()
                self.assertEqual(install.call_args.args[0][-2:], ['-e', str(root)])
                self.assertEqual(launch.call_args.args[0][-4:], ['serve', '--port', '9876', '--no-browser'])
                (root / 'pyproject.toml').write_text('[project]\nname="changed"\n')
                self.assertEqual(run.main(['--install-only']), 0)
                self.assertEqual(install.call_count, 2)


if __name__ == '__main__':
    unittest.main()
