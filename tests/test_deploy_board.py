import importlib.util
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    'deploy_board', Path(__file__).resolve().parents[1] / 'scripts/deploy_board.py')
deploy_board = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(deploy_board)


class DeploymentTests(unittest.TestCase):
    def test_package_excludes_secrets_and_normalizes_shell_lines(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in deploy_board.APP_FILES:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'example\r\n')
            for name in ('static/ui/app.js', 'static/ui/app.css', 'day/113.bmp',
                         '5x8.bdf', 'settings.toml', 'runtime/settings.toml',
                         '.env', 'cachedArticles.json'):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('private' if 'settings' in name else 'data')
            (root / 'node_modules/vite').mkdir(parents=True)
            with patch.object(deploy_board, 'ROOT', root), \
                 patch.object(deploy_board.shutil, 'which', return_value='npm'), \
                 patch.object(deploy_board.subprocess, 'run') as command:
                archive_path = deploy_board.build_package()
            command.assert_called_once()
            with tarfile.open(archive_path) as archive:
                names = archive.getnames()
                self.assertIn('main.py', names)
                self.assertIn('static/ui/app.js', names)
                self.assertIn('static/ui/app.css', names)
                self.assertIn('day/113.bmp', names)
                self.assertIn('5x8.bdf', names)
                self.assertNotIn('settings.toml', names)
                self.assertNotIn('runtime/settings.toml', names)
                self.assertNotIn('.env', names)
                self.assertNotIn('cachedArticles.json', names)
                self.assertEqual(archive.extractfile('run.sh').read(), b'example\n')

    def test_remote_helpers_compile(self):
        compile(deploy_board.INSPECT, 'inspect', 'exec')
        compile(deploy_board.INSTALL, 'install', 'exec')


if __name__ == '__main__':
    unittest.main()
