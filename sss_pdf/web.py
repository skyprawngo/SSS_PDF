"""Loopback-only web dashboard; no runtime web framework required."""
from __future__ import annotations

import json
import secrets
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from .config import AppConfig

STATIC = Path(__file__).with_name('static')
MAX_BODY = 16_384


class DashboardServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address=('127.0.0.1', 8765)):
        if address[0] != '127.0.0.1':
            raise ValueError('Dashboard must bind to 127.0.0.1')
        super().__init__(address, DashboardHandler)
        self.token = secrets.token_urlsafe(32)
        self.lock = threading.Lock()
        self.job = {'state': 'idle', 'action': '', 'messages': [], 'download': False}
        self.artifact = None
        self.last_capture = None

    def snapshot(self):
        with self.lock:
            return {**self.job, 'messages': list(self.job['messages'])}

    def start_job(self, action, values):
        # Construct and validate before reserving the worker.
        allowed = {'url', 'pages', 'output_dir', 'profile_dir', 'chrome_path', 'headless', 'timeout'}
        if set(values) - allowed:
            raise ValueError('알 수 없는 설정입니다.')
        if not isinstance(values.get('headless', False), bool):
            raise ValueError('headless 값은 boolean이어야 합니다.')
        for field in ('url', 'output_dir', 'profile_dir', 'chrome_path'):
            if field in values and not isinstance(values[field], (str, type(None))):
                raise ValueError(f'{field} 값은 문자열이어야 합니다.')
        pages = values.get('pages', 5)
        if not isinstance(pages, int) or isinstance(pages, bool) or not 1 <= pages <= 10000:
            raise ValueError('페이지 수는 1~10000 사이 정수여야 합니다.')
        output = values.get('output_dir') or 'SS_temp'
        if not isinstance(output, str):
            raise ValueError('저장 폴더가 올바르지 않습니다.')
        config = AppConfig(
            url=values.get('url') or '', pages=pages, output_dir=Path(output).expanduser(),
            profile_dir=Path(values['profile_dir']).expanduser() if values.get('profile_dir') else None,
            chrome_path=values.get('chrome_path') or None, headless=values.get('headless', False),
            timeout=float(values.get('timeout', 20)),
        )
        with self.lock:
            if self.job['state'] == 'running':
                return False
            self.job = {'state': 'running', 'action': action, 'messages': ['작업을 시작합니다.'], 'download': False}
            self.artifact = None
            if action == 'capture':
                self.last_capture = None
        threading.Thread(target=self._run, args=(action, config), daemon=True).start()
        return True

    def _message(self, value):
        with self.lock:
            self.job['messages'] = (self.job['messages'] + [str(value)])[-200:]

    def _run(self, action, config):
        try:
            from . import browser, pdf
            if action == 'login':
                browser.login(config)
                self._message('로그인 브라우저가 종료되었습니다. 캡처를 시작할 수 있습니다.')
            elif action == 'capture':
                paths = browser.capture(config, progress=self._message)
                if paths:
                    self.last_capture = (config.output_dir.resolve(), Path(paths[0]).parent.resolve())
                self._message(f'{len(paths)}개 페이지를 저장했습니다.')
            elif action == 'pdf':
                # A new filename keeps existing PDFs intact.
                target = config.output_dir / f'pages-{secrets.token_hex(4)}.pdf'
                source = config.output_dir
                if self.last_capture and self.last_capture[0] == config.output_dir.resolve():
                    source = self.last_capture[1]
                result = pdf.create_pdf(source, target)
                with self.lock:
                    self.artifact = Path(result).resolve()
                    self.job['download'] = True
                self._message('PDF 생성이 완료되었습니다.')
            with self.lock:
                self.job['state'] = 'done'
        except Exception as exc:
            self._message(str(exc))
            with self.lock:
                self.job['state'] = 'error'


class DashboardHandler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def _trusted(self):
        port = self.server.server_address[1]
        hosts = {f'127.0.0.1:{port}', f'localhost:{port}'}
        if self.headers.get('Host') not in hosts:
            return False
        origin = self.headers.get('Origin')
        if origin is not None and origin not in {f'http://{host}' for host in hosts}:
            return False
        return self.headers.get('Sec-Fetch-Site') != 'cross-site'

    def _send(self, status, content, kind='application/json; charset=utf-8', extra=None):
        if not isinstance(content, bytes):
            content = json.dumps(content, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(content)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        if not self._trusted():
            return self._send(403, {'error': '허용되지 않은 요청입니다.'})
        path = urlsplit(self.path).path
        if path == '/api/status':
            return self._send(200, {**self.server.snapshot(), 'token': self.server.token})
        if path == '/api/download':
            with self.server.lock:
                artifact = self.server.artifact
            if artifact is None or not artifact.is_file():
                return self._send(404, {'error': '생성된 PDF가 없습니다.'})
            return self._send(200, artifact.read_bytes(), 'application/pdf', {'Content-Disposition': 'attachment; filename="pages.pdf"'})
        files = {'/': ('index.html', 'text/html; charset=utf-8'), '/app.js': ('app.js', 'text/javascript; charset=utf-8'), '/style.css': ('style.css', 'text/css; charset=utf-8')}
        if path not in files:
            return self._send(404, {'error': '찾을 수 없습니다.'})
        filename, kind = files[path]
        return self._send(200, (STATIC / filename).read_bytes(), kind)

    def do_POST(self):
        if not self._trusted() or not secrets.compare_digest(self.headers.get('X-Session-Token', ''), self.server.token):
            return self._send(403, {'error': '허용되지 않은 요청입니다.'})
        action = {'/api/login': 'login', '/api/capture': 'capture', '/api/pdf': 'pdf'}.get(urlsplit(self.path).path)
        if action is None:
            return self._send(404, {'error': '찾을 수 없습니다.'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= MAX_BODY:
                return self._send(413, {'error': '요청 크기가 올바르지 않습니다.'})
            if self.headers.get_content_type() != 'application/json':
                return self._send(415, {'error': 'JSON 요청이 필요합니다.'})
            values = json.loads(self.rfile.read(length))
            if not isinstance(values, dict):
                raise ValueError('설정 객체가 필요합니다.')
            if not self.server.start_job(action, values):
                return self._send(409, {'error': '진행 중인 작업이 끝난 후 다시 시도하세요.'})
        except (ValueError, TypeError, KeyError) as exc:
            return self._send(400, {'error': str(exc)})
        return self._send(202, {'ok': True})


def main(host='127.0.0.1', port=8765, open_browser=True):
    with DashboardServer((host, port)) as server:
        url = f'http://127.0.0.1:{server.server_address[1]}'
        print(f'SSS PDF dashboard: {url}\n종료: Ctrl+C')
        if open_browser:
            webbrowser.open(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
