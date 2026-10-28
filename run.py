"""Download the repository, then run `python run.py` to open the dashboard."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parent


def main(argv=None):
    parser = argparse.ArgumentParser(description='SSS PDF 환경 준비 및 웹 화면 실행')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--no-browser', action='store_true')
    parser.add_argument('--install-only', action='store_true', help='환경 준비만 수행')
    args = parser.parse_args(argv)
    if sys.version_info < (3, 11):
        parser.error('Python 3.11 이상을 설치하세요.')
    if not 1 <= args.port <= 65535:
        parser.error('port는 1~65535 사이여야 합니다.')
    environment = ROOT / '.venv'
    python = environment / ('Scripts/python.exe' if sys.platform == 'win32' else 'bin/python')
    try:
        if not python.is_file():
            print('프로젝트 전용 Python 환경을 준비합니다.', flush=True)
            venv.EnvBuilder(with_pip=True).create(environment)
        fingerprint = hashlib.sha256((ROOT / 'pyproject.toml').read_bytes()).hexdigest()
        marker = environment / '.sss-pdf-install'
        if not marker.is_file() or marker.read_text().strip() != fingerprint:
            print('필요한 패키지를 설치합니다. 최초 실행에는 인터넷 연결이 필요합니다.', flush=True)
            subprocess.run([str(python), '-m', 'pip', 'install', '-e', str(ROOT)], cwd=ROOT, check=True)
            marker.write_text(fingerprint)
        if args.install_only:
            return 0
        command = [str(python), '-m', 'sss_pdf', 'serve', '--port', str(args.port)]
        if args.no_browser:
            command.append('--no-browser')
        return subprocess.call(command, cwd=ROOT)
    except KeyboardInterrupt:
        return 0
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f'실행 준비 실패: {exc}\nPython 3.11 이상과 인터넷 연결을 확인하세요.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
