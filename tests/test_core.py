"""Core regression tests; browser/account independent unless explicitly opted in."""
import contextlib
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from sss_pdf.config import AppConfig, default_profile_dir, find_chrome
from sss_pdf.pdf import create_pdf
from sss_pdf.cli import main


class ConfigTests(unittest.TestCase):
    def test_invalid_page_counts(self):
        for value in (0, -1, 10001, True, 2.5, '5'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                AppConfig(pages=value)

    def test_invalid_urls_and_timeouts(self):
        for url in ('file:///tmp/test', 'javascript:alert(1)', 'https:///missing'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                AppConfig(url=url)
        for timeout in (0, -1, 301, float('nan'), float('inf'), True, '20'):
            with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                AppConfig(timeout=timeout)

    def test_invalid_setting_types(self):
        for values in ({'url': 123}, {'url': None}, {'headless': 'false'}, {'headless': 0}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                AppConfig(**values)

    def test_os_profile_locations(self):
        with patch('sss_pdf.config.platform.system', return_value='Windows'), patch.dict(os.environ, {'LOCALAPPDATA': '/windows-local'}):
            self.assertEqual(default_profile_dir(), Path('/windows-local/SSS_PDF/chrome-profile'))
        with patch('sss_pdf.config.platform.system', return_value='Darwin'), patch('sss_pdf.config.Path.home', return_value=Path('/home/person')):
            self.assertEqual(default_profile_dir(), Path('/home/person/Library/Application Support/SSS_PDF/chrome-profile'))
        with patch('sss_pdf.config.platform.system', return_value='Linux'), patch.dict(os.environ, {'XDG_DATA_HOME': '/linux-data'}):
            self.assertEqual(default_profile_dir(), Path('/linux-data/SSS_PDF/chrome-profile'))

    def test_explicit_chrome_and_missing_binary(self):
        with tempfile.TemporaryDirectory() as folder:
            binary = Path(folder) / 'chrome'
            binary.touch()
            self.assertEqual(find_chrome(str(binary)), str(binary.resolve()))
            with self.assertRaises(ValueError):
                find_chrome(str(binary.parent / 'missing'))


class PdfTests(unittest.TestCase):
    def test_actual_pdf_preserves_natural_page_order_and_inputs(self):
        from PIL import Image
        import pikepdf
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name, width in [('page10.png', 30), ('page2.png', 20), ('page1.png', 10)]:
                Image.new('RGB', (width, 10), 'white').save(root / name)
            destination = create_pdf(root, root / 'book.pdf')
            self.assertTrue(destination.read_bytes().startswith(b'%PDF-'))
            with pikepdf.open(destination) as document:
                widths = [float(page.MediaBox[2]) for page in document.pages]
                self.assertEqual(widths, sorted(widths))
                self.assertEqual(len(widths), 3)
            self.assertEqual(len(list(root.glob('*.png'))), 3)
            original = destination.read_bytes()
            with self.assertRaises(FileExistsError):
                create_pdf(root, destination)
            self.assertEqual(destination.read_bytes(), original)

    def test_missing_empty_and_corrupt_input_leave_no_pdf(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            output = root / 'out.pdf'
            with self.assertRaises(ValueError):
                create_pdf(root / 'missing', output)
            with self.assertRaises(ValueError):
                create_pdf(root, output)
            (root / 'broken.png').write_bytes(b'not a PNG')
            with self.assertRaises(Exception):
                create_pdf(root, output)
            self.assertFalse(output.exists())


class CaptureTests(unittest.TestCase):
    def test_constant_url_still_captures_changed_pages_and_quits(self):
        from sss_pdf.browser import capture
        driver = Mock()
        driver.current_url = 'https://example.com/unchanged'
        page1, page2 = Mock(), Mock()
        page1.get_attribute.return_value = 'page-0-0'
        page2.get_attribute.return_value = 'page-1-0'
        page1.screenshot.return_value = page2.screenshot.return_value = True
        with tempfile.TemporaryDirectory() as folder, patch('sss_pdf.browser._driver', return_value=driver), patch('sss_pdf.browser._visible_page', side_effect=[page1, page2]), patch('selenium.webdriver.common.action_chains.ActionChains') as actions:
            updates = []
            files = capture(AppConfig(url='https://example.com', pages=2, output_dir=Path(folder)), updates.append)
            self.assertEqual([p.name for p in files], ['page-00001.png', 'page-00002.png'])
            self.assertEqual(len(updates), 2)
            actions.return_value.send_keys.return_value.perform.assert_called_once()
            driver.quit.assert_called_once()

    def test_screenshot_failure_is_reported_and_driver_closed(self):
        from sss_pdf.browser import capture
        driver, page = Mock(), Mock()
        page.get_attribute.return_value = 'page-0-0'
        page.screenshot.return_value = False
        with tempfile.TemporaryDirectory() as folder, patch('sss_pdf.browser._driver', return_value=driver), patch('sss_pdf.browser._visible_page', return_value=page):
            with self.assertRaisesRegex(RuntimeError, '스크린샷'):
                capture(AppConfig(url='https://example.com', pages=1, output_dir=Path(folder)))
            driver.quit.assert_called_once()

    def test_cleanup_does_not_mask_capture_failure(self):
        from sss_pdf.browser import capture
        driver, page = Mock(), Mock()
        driver.quit.side_effect = RuntimeError('cleanup failed')
        page.get_attribute.return_value = 'page-0-0'
        page.screenshot.side_effect = OSError('original screenshot failure')
        with tempfile.TemporaryDirectory() as folder, patch('sss_pdf.browser._driver', return_value=driver), patch('sss_pdf.browser._visible_page', return_value=page), self.assertLogs('sss_pdf.browser', level='WARNING'):
            with self.assertRaisesRegex(OSError, 'original screenshot failure'):
                capture(AppConfig(url='https://example.com', pages=1, output_dir=Path(folder)))

    def test_driver_initialization_failure_closes_browser(self):
        from sss_pdf.browser import _driver
        driver = Mock()
        driver.set_page_load_timeout.side_effect = RuntimeError('timeout setup failed')
        with tempfile.TemporaryDirectory() as folder, patch('selenium.webdriver.Chrome', return_value=driver), patch('sss_pdf.browser.find_chrome', return_value=None):
            with self.assertRaisesRegex(RuntimeError, 'timeout setup failed'):
                _driver(AppConfig(profile_dir=Path(folder)))
            driver.quit.assert_called_once()

    def test_page_timeout_preserves_error_and_quits(self):
        from sss_pdf.browser import capture
        from selenium.common.exceptions import TimeoutException
        driver = Mock()
        with patch('sss_pdf.browser._driver', return_value=driver), patch('selenium.webdriver.support.ui.WebDriverWait') as wait:
            wait.return_value.until.side_effect = TimeoutException()
            with self.assertRaisesRegex(RuntimeError, '저장된 페이지: 0'):
                capture(AppConfig(url='https://example.com', pages=1))
            driver.quit.assert_called_once()


class CliTests(unittest.TestCase):
    def test_invalid_configuration_returns_failure_without_launching_browser(self):
        with patch('sss_pdf.browser.capture') as capture, contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(['capture', '--url', 'file:///bad', '--pages', '0']), 1)
            capture.assert_not_called()

    def test_pdf_dispatch(self):
        with patch('sss_pdf.pdf.create_pdf', return_value=Path('out.pdf')) as create, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(['pdf', 'images', 'out.pdf']), 0)
            create.assert_called_once_with(Path('images'), Path('out.pdf'))


@unittest.skipUnless(os.environ.get('SSS_PDF_BROWSER_TEST') == '1', 'set SSS_PDF_BROWSER_TEST=1 with Chrome/driver installed')
class BrowserIntegrationTests(unittest.TestCase):
    def test_real_nested_iframe_capture_to_pdf(self):
        from functools import partial
        from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
        from threading import Thread
        from sss_pdf.browser import capture
        import pikepdf
        fixture_dir = Path(__file__).parent / 'fixtures'
        server = ThreadingHTTPServer(('127.0.0.1', 0), partial(SimpleHTTPRequestHandler, directory=str(fixture_dir)))
        worker = Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            with tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                files = capture(AppConfig(url=f'http://127.0.0.1:{server.server_port}/reader.html', pages=3, headless=True, chrome_path=os.environ.get('SSS_PDF_CHROME_PATH'), profile_dir=root/'profile', output_dir=root/'output', timeout=10))
                self.assertEqual(len(files), 3)
                self.assertEqual(len({p.read_bytes() for p in files}), 3)
                destination = create_pdf(files[0].parent, root/'book.pdf')
                with pikepdf.open(destination) as document:
                    self.assertEqual(len(document.pages), 3)
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=5)


if __name__ == '__main__':
    unittest.main()
