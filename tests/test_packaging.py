import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from office_assistant.__main__ import main
from office_assistant.paths import resource_dir, user_data_dir
from office_assistant.self_check import run_checks, write_report
from scripts.bundle_manifest import create, verify

ROOT = Path(__file__).resolve().parents[1]


class PackagingTests(unittest.TestCase):
    def test_source_and_frozen_resource_roots(self):
        self.assertEqual(resource_dir(), ROOT)
        with patch('sys._MEIPASS', '/test/frozen/_internal', create=True):
            self.assertEqual(resource_dir(), Path('/test/frozen/_internal'))

    def test_windows_data_root_is_not_install_directory(self):
        with patch.dict(os.environ, {'LOCALAPPDATA': 'D:/Users/test/AppData/Local'}):
            self.assertEqual(user_data_dir(), Path('D:/Users/test/AppData/Local/Office Assistant'))

    def test_self_check_uses_samples_and_preserves_user_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp)
            (data / 'config').mkdir()
            state = data / 'config/state.json'
            state.write_text('not even valid json: do not touch', encoding='utf-8')
            report = run_checks(data_root=data, resources=ROOT, check_gui=False)
            self.assertEqual([x['status'] for x in report['checks']], ['passed', 'passed', 'passed', 'skipped'])
            self.assertFalse(report['ok'], 'Skipping GUI must not report full success')
            self.assertEqual(state.read_text(), 'not even valid json: do not touch')
            self.assertEqual(list((data / 'cache').iterdir()), [])
            write_report(report, data / 'logs/result.json')
            self.assertEqual(json.loads((data / 'logs/result.json').read_text())['ok'], False)

    def test_missing_resources_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = run_checks(Path(tmp) / 'data', Path(tmp), check_gui=False)
            self.assertFalse(report['ok'])
            self.assertEqual(report['checks'][2]['status'], 'failed')

    def test_cli_report_and_exit_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'report.json'
            for success in (True, False):
                with patch('office_assistant.self_check.run_checks', return_value={'ok': success}):
                    self.assertEqual(main(['--self-check', '--report', str(path)]), 0 if success else 1)
                self.assertEqual(json.loads(path.read_text()), {'ok': success})

    def test_bundle_integrity_rejects_mutation_extra_and_missing_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            req = root / 'requirements-build.txt'
            req.write_text('example==1\n')
            wheel = root / 'example.whl'
            wheel.write_bytes(b'fixture')
            create(root)
            verify(root, req)
            wheel.write_bytes(b'tampered')
            with self.assertRaises(ValueError):
                verify(root)
            wheel.write_bytes(b'fixture')
            extra = root / 'extra.whl'
            extra.write_bytes(b'unexpected')
            with self.assertRaises(ValueError):
                verify(root)
            extra.unlink()
            wheel.unlink()
            with self.assertRaises(ValueError):
                verify(root)

    def test_bundle_cannot_override_current_requirements(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'bundle'
            root.mkdir()
            (root / 'requirements-build.txt').write_text('package==1')
            (root / 'example.whl').write_bytes(b'fixture')
            create(root)
            actual = Path(tmp) / 'current.txt'
            actual.write_text('package==2')
            with self.assertRaises(ValueError):
                verify(root, actual)

    def test_packaging_static_safeguards(self):
        installer = (ROOT / 'packaging/windows/installer.iss').read_text()
        self.assertIn('PrivilegesRequired=admin', installer)
        self.assertIn('DefaultDirName=D:\\Program Files\\Office Assistant', installer)
        sections = [line.strip() for line in installer.splitlines() if line.startswith('[')]
        self.assertNotIn('[Run]', sections)
        self.assertNotIn('[UninstallDelete]', sections)
        spec = (ROOT / 'packaging/windows/OfficeAssistant.spec').read_text()
        self.assertIn('uac_admin=False', spec)
        self.assertIn("'samples'", spec)
        build = (ROOT / 'scripts/build-windows.ps1').read_text()
        self.assertIn("'--no-index'", build)
        self.assertNotIn('Invoke-WebRequest', build)
        self.assertIn('$Process.WaitForExit(120000)', build)
        self.assertNotIn('Remove-Item', build)


class CloudBuildConfigurationTests(unittest.TestCase):
    """Static contracts only; these do not execute PowerShell or GitHub Actions."""

    def test_workflow_is_manual_and_read_only(self):
        import re
        text = (ROOT / '.github/workflows/windows-build.yml').read_text()
        self.assertIn('workflow_dispatch:', text)
        self.assertNotIn('pull_request_target:', text)
        self.assertNotIn('\n  push:', text)
        self.assertIn('contents: read', text)
        self.assertIn('persist-credentials: false', text)
        uses = re.findall(r'uses: ([^\s]+)', text)
        self.assertEqual(len(uses), 4)
        for action in uses:
            self.assertRegex(action, r'^actions/[a-z-]+@[a-f0-9]{40}$')
        self.assertIn('runs-on: windows-2022', text)
        self.assertIn('if-no-files-found: error', text)
        self.assertIn('retention-days: 7', text)
        self.assertNotIn('secrets.', text)

    def test_inno_is_verified_before_execution_and_offline_script_stays_offline(self):
        import re
        script = (ROOT / 'scripts/install-inno-ci.ps1').read_text()
        self.assertRegex(script, r"\$ExpectedHash = '[a-f0-9]{64}'")
        self.assertLess(script.index('$ActualHash -ne $ExpectedHash'), script.index('Start-Process'))
        self.assertIn('$Process.WaitForExit(180000)', script)
        build = (ROOT / 'scripts/build-windows.ps1').read_text()
        self.assertIn('$ResultFile', build)
        self.assertIn('build-provenance.json', build)
        self.assertNotIn('Invoke-WebRequest', build)
        self.assertNotIn('install-inno-ci.ps1', build)

    def test_frozen_self_check_error_does_not_open_a_blocking_dialog(self):
        with patch('office_assistant.self_check.run_checks', side_effect=RuntimeError('test failure')), \
             patch('sys.frozen', True, create=True), \
             patch('office_assistant.__main__._dialog') as dialog:
            self.assertEqual(main(['--self-check']), 1)
            dialog.assert_not_called()
            self.assertEqual(main(['--self-check', '--show-result']), 1)
            dialog.assert_called_once()

    def test_all_nine_fictional_samples_are_present_and_not_ignored(self):
        from zipfile import ZipFile
        from xml.etree import ElementTree as ET
        ignore = (ROOT / '.gitignore').read_text().splitlines()
        self.assertNotIn('samples/', ignore)
        paths = [p for p in (ROOT / 'samples').rglob('*') if p.is_file()]
        self.assertEqual(len(paths), 9)
        for path in paths:
            if path.suffix in ('.xlsx', '.docx'):
                with ZipFile(path) as archive:
                    text = '\n'.join(' '.join(ET.fromstring(archive.read(name)).itertext())
                                     for name in archive.namelist() if name.endswith('.xml'))
            else:
                text = path.read_text(encoding='utf-8')
            self.assertIn('虚构', text, str(path))
