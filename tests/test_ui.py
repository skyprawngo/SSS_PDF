"""Opt-in, real-browser coverage of the complete local dashboard workflow.

Run with SSS_PDF_BROWSER_TEST=1. SSS_PDF_CHROME_PATH optionally selects the
Chrome binary used for both the dashboard browser and its capture browser.
A matching ChromeDriver must be discoverable by Selenium Manager or on PATH.
"""
from contextlib import ExitStack
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import io
import os
from pathlib import Path
import tempfile
from threading import Thread
import unittest
from urllib.request import urlopen

from sss_pdf.web import DashboardServer


class QuietFixtureHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


@unittest.skipUnless(
    os.environ.get('SSS_PDF_BROWSER_TEST') == '1',
    'set SSS_PDF_BROWSER_TEST=1 with Chrome/driver installed',
)
class DashboardBrowserIntegrationTests(unittest.TestCase):
    def test_real_ui_capture_to_download_on_desktop_and_mobile(self):
        import pikepdf
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait

        fixture_dir = Path(__file__).parent / 'fixtures'
        fixture = ThreadingHTTPServer(
            ('127.0.0.1', 0),
            partial(QuietFixtureHandler, directory=str(fixture_dir)),
        )
        dashboard = DashboardServer(('127.0.0.1', 0))
        workers = [Thread(target=server.serve_forever, daemon=True) for server in (fixture, dashboard)]
        for worker in workers:
            worker.start()
        try:
            with ExitStack() as resources:
                root = Path(resources.enter_context(tempfile.TemporaryDirectory()))
                chrome_path = os.environ.get('SSS_PDF_CHROME_PATH')
                options = webdriver.ChromeOptions()
                if chrome_path:
                    options.binary_location = chrome_path
                options.add_argument('--headless=new')
                options.add_argument('--window-size=1440,1100')
                options.add_argument(f'--user-data-dir={root / "dashboard-profile"}')
                options.set_capability('goog:loggingPrefs', {'browser': 'ALL'})
                driver = webdriver.Chrome(options=options)
                # Release profile file handles before TemporaryDirectory cleanup on Windows.
                resources.callback(driver.quit)
                wait = WebDriverWait(driver, 60)
                base = f'http://127.0.0.1:{dashboard.server_port}'
                driver.get(base)
                wait.until(lambda browser: browser.find_element(By.ID, 'state').text == '준비됨')

                def fill(name, value):
                    field = driver.find_element(By.NAME, name)
                    field.clear()
                    field.send_keys(str(value))

                fill('url', f'http://127.0.0.1:{fixture.server_port}/reader.html')
                fill('pages', 3)
                fill('output_dir', root / 'output')
                driver.find_element(By.CSS_SELECTOR, 'details summary').click()
                if chrome_path:
                    fill('chrome_path', chrome_path)
                fill('profile_dir', root / 'capture-profile')
                driver.find_element(By.NAME, 'headless').click()
                driver.find_element(By.CSS_SELECTOR, '[data-action="capture"]').click()

                def capture_finished(browser):
                    state = browser.find_element(By.ID, 'state').text
                    logs = browser.find_element(By.ID, 'logs').text
                    self.assertNotEqual(state, '오류', logs)
                    self.assertFalse(browser.find_element(By.ID, 'error').text)
                    return state == '완료' and '3/3:' in logs

                wait.until(capture_finished)
                images = sorted((root / 'output').glob('*/page-*.png'))
                self.assertEqual(len(images), 3)
                self.assertEqual(len({image.read_bytes() for image in images}), 3)
                self.assertTrue(all(image.read_bytes().startswith(b'\x89PNG\r\n\x1a\n') for image in images))
                driver.find_element(By.CSS_SELECTOR, '[data-action="pdf"]').click()

                def pdf_finished(browser):
                    self.assertNotEqual(browser.find_element(By.ID, 'state').text, '오류', browser.find_element(By.ID, 'logs').text)
                    self.assertFalse(browser.find_element(By.ID, 'error').text)
                    link = browser.find_element(By.ID, 'download')
                    return link if link.is_displayed() else False

                download = wait.until(pdf_finished)
                with urlopen(download.get_attribute('href'), timeout=10) as response:
                    self.assertEqual(response.status, 200)
                    self.assertEqual(response.headers.get_content_type(), 'application/pdf')
                    data = response.read()
                self.assertTrue(data.startswith(b'%PDF-'))
                with pikepdf.open(io.BytesIO(data)) as document:
                    self.assertEqual(len(document.pages), 3)
                self.assertEqual(len(list((root / 'output').glob('*/page-*.png'))), 3)
                self.assertTrue(driver.execute_script('return document.documentElement.scrollWidth <= innerWidth'))
                driver.set_window_size(390, 844)
                wait.until(lambda browser: browser.execute_script('return innerWidth < 600'))
                self.assertTrue(driver.execute_script('return document.documentElement.scrollWidth <= innerWidth'))
                self.assertTrue(driver.find_element(By.ID, 'download').is_displayed())
                errors = [
                    entry for entry in driver.get_log('browser')
                    if entry['level'] == 'SEVERE' and 'favicon.ico' not in entry['message']
                ]
                self.assertEqual(errors, [], 'Browser console errors')
        finally:
            for server in (dashboard, fixture):
                server.shutdown()
                server.server_close()
            for worker in workers:
                worker.join(timeout=5)


if __name__ == '__main__':
    unittest.main()
