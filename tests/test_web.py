import http.client
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from sss_pdf.web import DashboardServer


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.server = DashboardServer(('127.0.0.1', 0))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.server.server_address[1]

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def request(self, method, path, value=None, headers=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.port, timeout=3)
        actual = {'Content-Type': 'application/json', 'X-Session-Token': self.server.token}
        actual.update(headers or {})
        connection.request(method, path, None if value is None else json.dumps(value), actual)
        response = connection.getresponse()
        result = (response.status, response.read(), dict(response.getheaders()))
        connection.close()
        return result

    def wait_job(self):
        for _ in range(100):
            if self.server.snapshot()['state'] != 'running':
                return self.server.snapshot()
            time.sleep(.01)
        self.fail('job did not finish')

    def test_assets_and_token(self):
        status, body, headers = self.request('GET', '/')
        self.assertEqual(status, 200)
        self.assertIn('작업 설정', body.decode())
        self.assertIn("frame-ancestors 'none'", headers['Content-Security-Policy'])
        status, body, _ = self.request('GET', '/api/status')
        self.assertEqual(json.loads(body)['token'], self.server.token)
        self.assertEqual(self.request('GET', '/../../etc/passwd')[0], 404)

    def test_reject_untrusted_requests(self):
        self.assertEqual(self.request('GET', '/', headers={'Host': 'evil.example'})[0], 403)
        self.assertEqual(self.request('GET', '/api/status', headers={'Origin': 'https://evil.example'})[0], 403)
        self.assertEqual(self.request('POST', '/api/pdf', {}, {'X-Session-Token': ''})[0], 403)
        self.assertEqual(self.request('POST', '/api/pdf', {}, {'Sec-Fetch-Site': 'cross-site'})[0], 403)

    def test_validation(self):
        self.assertEqual(self.request('POST', '/api/capture', {'pages': 0})[0], 400)
        self.assertEqual(self.request('POST', '/api/capture', {'url': []})[0], 400)
        self.assertEqual(self.request('POST', '/api/capture', {'pages': True})[0], 400)
        self.assertEqual(self.request('POST', '/api/capture', {'extra': 1})[0], 400)
        self.assertEqual(self.request('GET', '/api/download')[0], 404)

    def test_single_worker_and_error(self):
        gate = threading.Event()
        with patch('sss_pdf.browser.login', side_effect=lambda config: gate.wait(2)):
            self.assertEqual(self.request('POST', '/api/login', {})[0], 202)
            self.assertEqual(self.request('POST', '/api/capture', {})[0], 409)
            gate.set()
            self.assertEqual(self.wait_job()['state'], 'done')
        with patch('sss_pdf.browser.capture', side_effect=RuntimeError('test failure')):
            self.assertEqual(self.request('POST', '/api/capture', {})[0], 202)
            result = self.wait_job()
            self.assertEqual(result['state'], 'error')
            self.assertIn('test failure', result['messages'])

    def test_capture_then_pdf_download(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            session = root / 'capture-session'
            session.mkdir()
            image = session / 'page-1.png'
            image.write_bytes(b'fake image')
            def convert(source, target):
                self.assertEqual(source, session.resolve())
                target.write_bytes(b'%PDF-test')
                return target
            with patch('sss_pdf.browser.capture', return_value=[image]), patch('sss_pdf.pdf.create_pdf', side_effect=convert):
                self.assertEqual(self.request('POST', '/api/capture', {'output_dir': folder})[0], 202)
                self.assertEqual(self.wait_job()['state'], 'done')
                self.assertEqual(self.request('POST', '/api/pdf', {'output_dir': folder})[0], 202)
                result = self.wait_job()
                self.assertEqual(result['state'], 'done', result['messages'])
                self.assertTrue(result['download'])
                status, data, _ = self.request('GET', '/api/download')
                self.assertEqual(status, 200)
                self.assertEqual(data, b'%PDF-test')

    def test_failed_capture_forgets_previous_run(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            previous = root / 'previous'
            previous.mkdir()
            with patch('sss_pdf.browser.capture', return_value=[previous / '1.png']):
                self.request('POST', '/api/capture', {'output_dir': folder})
                self.assertEqual(self.wait_job()['state'], 'done')
            with patch('sss_pdf.browser.capture', side_effect=RuntimeError('failed')):
                self.request('POST', '/api/capture', {'output_dir': folder})
                self.assertEqual(self.wait_job()['state'], 'error')
            with patch('sss_pdf.pdf.create_pdf', side_effect=ValueError('no direct images')) as convert:
                self.request('POST', '/api/pdf', {'output_dir': folder})
                self.assertEqual(self.wait_job()['state'], 'error')
                self.assertEqual(convert.call_args.args[0], root.resolve())


if __name__ == '__main__':
    unittest.main()
