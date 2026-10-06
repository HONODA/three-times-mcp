import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location('three_times_installer', ROOT / 'integrations/quick-install/install.py')
INSTALLER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INSTALLER)
BUILDER_SPEC = importlib.util.spec_from_file_location('bundle_builder', ROOT / 'integrations/quick-install/build_bundle.py')
BUILDER = importlib.util.module_from_spec(BUILDER_SPEC)
BUILDER_SPEC.loader.exec_module(BUILDER)


class InstallerTest(unittest.TestCase):
    def test_exported_bundle_installs_independently_of_source_checkout(self):
        with tempfile.TemporaryDirectory(prefix='three times ') as temp:
            temp = Path(temp)
            archive = temp / 'installer.zip'
            BUILDER.build(archive)
            with zipfile.ZipFile(archive) as bundle:
                self.assertTrue(bundle.getinfo('three-times-mcp/Install-codex.command').external_attr >> 16 & 0o111)
                bundle.extractall(temp / 'downloads')
            source = temp / 'downloads' / 'three-times-mcp'
            destination = temp / 'persistent storage'
            roots = INSTALLER.prepare(source, destination, sys.executable)
            sentinel = destination / 'unrelated-user-file.txt'
            sentinel.write_text('keep me')
            # Reinstall updates our assets without deleting unrelated files.
            INSTALLER.prepare(source, destination, sys.executable)
            self.assertEqual(sentinel.read_text(), 'keep me')
            config = json.loads((destination / 'mcp.json').read_text())['mcpServers']['simple-painter']
            self.assertNotIn(str(ROOT), config['args'][0])
            self.assertNotIn(str(source), config['args'][0])
            # Deleting the unpacked download must not break the installed adapter.
            import shutil
            shutil.rmtree(source)
            request = {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize',
                       'params': {'protocolVersion': 'unsupported-future-version'}}
            completed = subprocess.run([config['command'], *config['args']],
                                       input=json.dumps(request) + '\n', text=True,
                                       capture_output=True, timeout=10, check=True)
            self.assertEqual(json.loads(completed.stdout)['result']['protocolVersion'], '2025-06-18')
            for target, root in roots.items():
                plugin = root / 'plugins' / 'simple-painter'
                self.assertTrue((plugin / 'skills/canvas-collaboration/SKILL.md').exists())
                self.assertEqual(json.loads((plugin / '.mcp.json').read_text())['mcpServers']['simple-painter'], config)

    def test_cli_receives_paths_with_spaces_as_single_arguments(self):
        marketplace = Path('/tmp/三省 plugins/marketplace')
        for target, install_command in [('codex', 'add'), ('workbuddy', 'install')]:
            with patch.object(INSTALLER, 'find_cli', return_value='/tmp/AI tool/bin/client'), patch.object(INSTALLER.subprocess, 'run') as run:
                self.assertTrue(INSTALLER.install(target, marketplace))
                self.assertEqual(run.call_args_list[0].args[0][-1], str(marketplace))
                self.assertEqual(run.call_args_list[1].args[0][2], install_command)
                for call in run.call_args_list:
                    self.assertNotIn('shell', call.kwargs)

    def test_cli_failure_is_not_reported_as_installed(self):
        with patch.object(INSTALLER, 'find_cli', return_value='/tmp/codex'), patch.object(INSTALLER.subprocess, 'run', side_effect=subprocess.CalledProcessError(1, 'codex')):
            with self.assertRaises(subprocess.CalledProcessError):
                INSTALLER.install('codex', Path('/tmp/plugin-marketplace'))
        with patch.object(INSTALLER, 'find_cli', return_value=None):
            self.assertFalse(INSTALLER.install('workbuddy', Path('/tmp/plugin-marketplace')))


if __name__ == '__main__':
    unittest.main()
