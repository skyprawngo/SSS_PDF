"""Explicit cookie import validation and secret redaction regression tests."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from sss_pdf.browser import _restore_cookies
from sss_pdf.cli import main
from sss_pdf.config import AppConfig


class CookieTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'cookies.json'
        self.config = AppConfig(url='https://books.example.com/reader', cookies_file=self.path)
        self.driver = Mock()

    def export(self, value):
        self.path.write_text(json.dumps(value), encoding='utf-8')

    def test_default_never_reads_files_or_alters_session(self):
        with patch.object(Path, 'open', side_effect=AssertionError('unexpected access')):
            _restore_cookies(self.driver, AppConfig())
        self.driver.assert_not_called()
        self.driver.add_cookie.assert_not_called()
        self.driver.get.assert_not_called()

    def test_valid_cookies_strip_export_metadata_and_reload(self):
        self.export([{'name': 'session', 'value': 'private-token', 'domain': '.example.com', 'path': '/', 'secure': True, 'httpOnly': True, 'expiry': 2000000000, 'sameSite': 'Lax', 'storeId': '0', 'session': False}, {'name': 'host', 'value': ''}])
        _restore_cookies(self.driver, self.config)
        cookie = self.driver.add_cookie.call_args_list[0].args[0]
        self.assertEqual(set(cookie), {'name', 'value', 'domain', 'path', 'secure', 'httpOnly', 'expiry', 'sameSite'})
        self.assertEqual(self.driver.add_cookie.call_count, 2)
        self.driver.get.assert_called_once_with(self.config.url)

    def test_invalid_schema_rejected_before_any_cookie_is_set(self):
        invalid = [None, {}, 'secret-token', [None], [{'name': '', 'value': 'x'}], [{'name': 'x', 'value': 3}], [{'name': 'x', 'value': 'x', 'secure': 'true'}], [{'name': 'x', 'value': 'x', 'httpOnly': 1}], [{'name': 'x', 'value': 'x', 'expiry': True}], [{'name': 'x', 'value': 'x', 'expiry': 1.5}], [{'name': 'x', 'value': 'x', 'sameSite': {}}], [{'name': 'x', 'value': 'x', 'path': 'relative'}], [{'name': 'x', 'value': 'x', 'domain': 'evil-example.com'}], [{'name': 'x', 'value': 'x', 'domain': 'com.example.com'}]]
        for item in invalid:
            with self.subTest(item=item):
                self.export(item)
                with self.assertRaises(ValueError):
                    _restore_cookies(self.driver, self.config)
        self.driver.add_cookie.assert_not_called()
        self.driver.get.assert_not_called()

    def test_domain_suffix_boundary(self):
        for domain in ('books.example.com.evil', 'notexample.com', '.', '', ' example.com', 4):
            with self.subTest(domain=domain):
                self.export([{'name': 'x', 'value': 'x', 'domain': domain}])
                with self.assertRaises(ValueError):
                    _restore_cookies(self.driver, self.config)

    def test_size_and_count_limits(self):
        self.path.write_bytes(b' ' * (1024 * 1024 + 1))
        with self.assertRaises(ValueError):
            _restore_cookies(self.driver, self.config)
        self.export([{'name': 'x', 'value': 'x'}] * 501)
        with self.assertRaises(ValueError):
            _restore_cookies(self.driver, self.config)

    def test_missing_and_invalid_json_and_driver_error_hide_secrets(self):
        with self.assertRaises(ValueError):
            _restore_cookies(self.driver, self.config)
        self.path.write_text('private-token-is-not-json')
        with self.assertRaises(ValueError) as error:
            _restore_cookies(self.driver, self.config)
        self.assertNotIn('private-token', str(error.exception))
        self.export([{'name': 'session', 'value': 'private-token'}])
        self.driver.add_cookie.side_effect = RuntimeError('private-token')
        with self.assertRaises(ValueError) as error:
            _restore_cookies(self.driver, self.config)
        self.assertNotIn('private-token', str(error.exception))

    def test_cli_passes_optional_cookie_path(self):
        with patch('sss_pdf.browser.capture', return_value=[Path('run/page.png')]) as capture, contextlib.redirect_stdout(io.StringIO()):
            result = main(['capture', '--url', self.config.url, '--cookies-file', str(self.path)])
        self.assertEqual(result, 0)
        self.assertEqual(capture.call_args.args[0].cookies_file, self.path.resolve())


if __name__ == '__main__':
    unittest.main()
