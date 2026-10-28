"""Validated settings and platform-specific Chrome/profile discovery."""
from dataclasses import dataclass
from pathlib import Path
import os
import math
import platform
import shutil
from urllib.parse import urlparse


def default_profile_dir() -> Path:
    system = platform.system()
    if system == 'Windows':
        base = Path(os.environ.get('LOCALAPPDATA', str(Path.home() / 'AppData' / 'Local')))
    elif system == 'Darwin':
        base = Path.home() / 'Library' / 'Application Support'
    else:
        base = Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local' / 'share')))
    return base / 'SSS_PDF' / 'chrome-profile'


def find_chrome(explicit: str | None = None) -> str | None:
    if explicit:
        path = Path(explicit).expanduser()
        if not path.is_file():
            raise ValueError(f'Chrome 실행 파일을 찾을 수 없습니다: {path}')
        return str(path.resolve())
    candidates = []
    system = platform.system()
    if system == 'Darwin':
        candidates = [Path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'), Path.home() / 'Applications/Google Chrome.app/Contents/MacOS/Google Chrome']
    elif system == 'Windows':
        for key in ('PROGRAMFILES', 'PROGRAMFILES(X86)', 'LOCALAPPDATA'):
            if os.environ.get(key):
                candidates.append(Path(os.environ[key]) / 'Google/Chrome/Application/chrome.exe')
    for path in candidates:
        if path.is_file():
            return str(path)
    for name in ('google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser', 'chrome'):
        found = shutil.which(name)
        if found:
            return found
    return None  # Selenium Manager can discover/install the appropriate browser.


@dataclass
class AppConfig:
    url: str = ''
    pages: int = 5
    output_dir: Path = Path('SS_temp')
    profile_dir: Path | None = None
    chrome_path: str | None = None
    headless: bool = False
    timeout: float = 20
    cookies_file: Path | None = None

    def __post_init__(self):
        if self.cookies_file is not None:
            self.cookies_file = Path(self.cookies_file).expanduser().resolve()
        self.output_dir = Path(self.output_dir).expanduser().resolve()
        self.profile_dir = Path(self.profile_dir).expanduser().resolve() if self.profile_dir else default_profile_dir()
        if isinstance(self.pages, bool) or not isinstance(self.pages, int) or not 1 <= self.pages <= 10000:
            raise ValueError('pages는 1~10000 사이의 정수여야 합니다.')
        if isinstance(self.timeout, bool) or not isinstance(self.timeout, (int, float)) or not math.isfinite(self.timeout) or not 0 < self.timeout <= 300:
            raise ValueError('timeout은 0초 초과 300초 이하여야 합니다.')
        if not isinstance(self.url, str):
            raise ValueError('url은 문자열이어야 합니다.')
        if not isinstance(self.headless, bool):
            raise ValueError('headless는 boolean이어야 합니다.')
        if self.url:
            parsed = urlparse(self.url)
            if parsed.scheme not in ('http', 'https') or not parsed.hostname:
                raise ValueError('올바른 http 또는 https URL을 입력하세요.')
