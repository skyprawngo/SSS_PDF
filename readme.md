# SSS PDF

브라우저에서 표시되는 페이지를 순서대로 캡처하고 PNG를 PDF로 묶는 로컬 도구입니다. CLI와 한국어 웹 화면을 제공합니다. Google Books의 `reader-page` 구조를 대상으로 하며, 로그인과 페이지 레이아웃 설정은 사용자가 Chrome에서 직접 진행합니다.

## 다운로드 후 바로 실행

Python 3.11 이상과 Google Chrome을 설치하고 저장소 ZIP 또는 Actions의 `sss-pdf-application` 아티팩트를 내려받아 압축을 풉니다. 아티팩트에는 실행용 소스 ZIP과 Python 배포 패키지가 함께 들어 있습니다. 소스 ZIP을 한 번 더 풀어 `SSS_PDF` 폴더에서 실행하세요.

- macOS: `start.command`를 실행하거나 터미널에서 `python3 run.py`를 실행합니다. 실행 권한 때문에 열리지 않으면 터미널에서 실행하세요.
- Windows: `start.bat`를 더블클릭하거나 `py run.py`를 실행합니다.
- Linux: 터미널에서 `python3 run.py`를 실행합니다.

실행기는 프로젝트의 `.venv`를 준비하고 필요한 패키지를 설치한 뒤 로컬 서버와 웹 화면을 엽니다. 최초 실행에는 인터넷 연결이 필요합니다. 자동으로 창이 열리지 않으면 터미널에 표시된 로컬 주소를 직접 여세요. 프로그램을 종료하려면 실행 터미널에서 Ctrl+C를 누릅니다.

이미 설치한 환경에서는 인자 없이 `python -m sss_pdf`를 실행해도 웹 화면이 열립니다. 브라우저를 자동으로 열지 않으려면 `python -m sss_pdf serve --no-browser`를 사용하세요.

## 작업 순서

1. 기존 동작과 오류 확인: macOS 경로 고정, URL 변경에 의존한 조기 종료, PDF 변환 누락을 확인했습니다.
2. 브라우저·설정·PDF·CLI를 모듈로 분리하고 운영체제별 환경을 정리합니다.
3. 현재 Selenium 및 img2pdf에 맞춰 갱신하고 로컬 웹 화면을 추가합니다.
4. 자동 회귀 테스트, 패키지 빌드와 웹 서버 검증을 수행합니다. 실제 계정으로 로그인하고 책을 넘기는 검증은 로컬 Chrome에서 별도로 진행합니다.

## 지원 환경과 의존성

- Python 3.11 이상, Google Chrome 최신 안정 버전
- macOS, Windows, Linux의 Chrome 실행 파일과 사용자 데이터 경로 자동 탐색
- Selenium 4.51.0 이상 5 미만, img2pdf 0.6.3 이상 0.7 미만
- Selenium Manager가 Chrome에 맞는 드라이버를 관리합니다. 최초 실행 시 드라이버 다운로드를 위한 네트워크가 필요할 수 있습니다.
- 프론트엔드는 HTML/CSS/JavaScript로 제공되며 Node.js 설치가 필요하지 않습니다.

위 의존성 기준은 2026-10-28 PyPI 안정 버전 조회를 기준으로 합니다. GitHub Actions는 같은 날짜 최신 릴리스 checkout v7.0.1, setup-python v7.1.0, upload-artifact v7.0.2를 확인해 v7 메이저를 사용합니다. Python 3.11/3.14와 세 운영체제의 자동 테스트 매트릭스는 `.github/workflows/tests.yml`에 정의되어 있습니다. CI 정의와 실제 해당 OS에서의 검증 완료 여부는 구분해야 합니다.

### macOS 설치

Chrome과 Python을 설치한 뒤 저장소 디렉터리에서 실행합니다.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
python -m sss_pdf --help
```

### Windows 설치 (PowerShell)

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m sss_pdf --help
```

PowerShell 실행 정책을 변경할 필요 없이 가상환경 Python을 직접 사용할 수 있습니다. 아래 예제의 `python`은 Windows에서 `.\.venv\Scripts\python.exe`로 바꾸어 실행하면 됩니다.

### Linux 설치

Python 3.11 이상과 Chrome을 설치하고 macOS 예제와 같이 가상환경을 만드세요. 로그인은 화면이 있는 데스크톱 환경에서 진행해야 합니다.

## 웹 화면 사용

```sh
python -m sss_pdf serve --port 8765
```

브라우저에서 http://127.0.0.1:8765 를 엽니다. 책 URL과 캡처 설정을 입력하고 로그인 → 캡처 → PDF 생성 순으로 진행합니다. 로그인 Chrome에서 인증을 마친 후 창을 닫아야 작업이 완료됩니다. 같은 프로필을 사용하는 Chrome을 닫은 다음 캡처를 실행하세요. 작업 상태와 오류를 화면에서 확인할 수 있고 생성된 PDF를 내려받을 수 있습니다.

서버는 로컬 컴퓨터에서만 접속하는 용도로 설계되어 있습니다. 종료하려면 서버를 실행한 터미널에서 Ctrl+C를 누르세요.

## CLI 사용

### 1. 로그인 세션 준비

```sh
python -m sss_pdf login --url "https://play.google.com/books/reader?id=BOOK_ID"
```

Chrome에서 로그인하고 책을 엽니다. 뷰어 설정에서 세로 스크롤을 끄고 한 페이지 레이아웃으로 맞춘 뒤 **로그인 Chrome 창을 닫습니다**. 프로필은 운영체제의 사용자 데이터 디렉터리에 별도로 보관되며 평소 Chrome 프로필과 분리됩니다.

### 2. 연속 캡처

```sh
python -m sss_pdf capture --url "https://play.google.com/books/reader?id=BOOK_ID" --pages 10 --output-dir SS_temp
```

현재 표시된 페이지부터 캡처합니다. 각 실행은 `SS_temp/<실행별 디렉터리>/page-00001.png` 형태로 저장되며 이전 캡처와 섞이지 않습니다. CLI에 출력된 실행별 디렉터리를 PDF 변환에 사용하세요. 화면이 없는 실행이 필요하면 로그인 완료 후 `--headless`를 추가합니다.

`login`과 `capture` 설정:

| 옵션 | 의미 |
| --- | --- |
| `--url` | 열 책 URL, capture에서 필수 |
| `--pages` | 캡처 수, 기본 5 |
| `--output-dir` | 캡처 저장 상위 디렉터리, 기본 SS_temp |
| `--profile-dir` | 로그인 세션을 보관할 프로필 경로 |
| `--chrome-path` | Chrome 자동 탐색 실패 시 실행 파일의 전체 경로 |
| `--timeout` | 요소와 페이지 전환 대기 초, 기본 20 |
| `--headless` | 캡처 시 창 없이 실행; 로그인은 항상 창 표시 |

공백이 포함된 경로는 따옴표로 감싸세요. `--profile-dir`을 사용했다면 로그인과 캡처에 동일한 경로를 지정해야 합니다.

### 3. PNG를 PDF로 변환

```sh
python -m sss_pdf pdf "SS_temp/실제-실행-디렉터리" "book.pdf"
```

PNG 파일을 숫자 기준 자연 정렬해 PDF로 묶습니다. 기존 PDF를 덮어쓰지 않고 원본 이미지를 삭제하지 않습니다. 예전 `pngtopdf.py`를 실행했을 때 캡처 폴더를 삭제하던 동작은 제거했습니다.

기존 진입점 `mainpybychrome.py`와 `pngtopdf.py`는 새 CLI 호환 래퍼입니다. 소스 상단의 전역 변수를 직접 고치던 방식 대신 CLI 옵션 또는 웹 화면을 사용하세요.

## 구조

| 경로 | 역할 |
| --- | --- |
| `sss_pdf/config.py` | 설정 검증, OS별 경로 탐색 |
| `sss_pdf/browser.py` | Chrome 로그인, 페이지 전환, 요소 캡처 |
| `sss_pdf/pdf.py` | PNG 자연 정렬 및 PDF 생성 |
| `sss_pdf/cli.py` | 명령행 인터페이스 |
| `sss_pdf/web.py` | 로컬 HTTP 서버와 백그라운드 작업 |
| `sss_pdf/static/` | 반응형 한국어 웹 화면 |
| `tests/` | 브라우저 모의 테스트, 실제 PDF 및 HTTP 회귀 검증 |

## 검증과 문제 해결

```sh
python -m pip install -e ".[dev]"
python -m unittest discover -s tests -v
python -m build
```

자동 테스트는 Google 계정 없이 실행할 수 있습니다. 실제 Google Books의 로그인 정책과 뷰어 DOM은 외부에서 바뀔 수 있으므로, 최초 사용 시 2~3페이지로 먼저 확인하세요. 자동 테스트 결과가 실제 서비스 연결 성공을 뜻하지는 않습니다.

### 이번 변경의 검증 결과 (2026-10-28)

- Linux / Python 3.12.14에서 실제 Chromium 156 통합 테스트를 포함한 32개 테스트 통과.
- URL이 유지되는 iframe 리더에서 서로 다른 PNG 3개를 캡처하고 실제 3페이지 PDF를 생성했습니다. 이 과정에서 발견한 iframe 키보드 초점 문제를 수정했습니다.
- 한국어 대시보드의 데스크톱(1440×1100)·모바일(390×844) 표시, 작업 완료와 다운로드 링크, JavaScript 오류 여부를 실제 브라우저로 확인했습니다. 실제 UI → 캡처 → PDF 다운로드를 연결한 통합 테스트도 통과했습니다.
- 패키지 빌드와 의존성 검사, 저장소 밖 wheel 설치 및 웹 자산 포함 여부를 확인했습니다.
- macOS·Windows 실기기 실행 및 Google Books 실제 계정 로그인은 미검증입니다. CI의 OS별 실행 결과도 아직 없습니다.

Chrome과 호환 드라이버가 준비된 환경에서 실제 로컬 리더 통합 테스트도 실행하려면 `SSS_PDF_BROWSER_TEST=1`을 설정하세요. 필요하면 `SSS_PDF_CHROME_PATH`에 Chrome 실행 파일을 지정합니다. 일반 테스트 명령은 브라우저 통합 테스트 한 개를 건너뜁니다.

- Chrome 탐색 실패: 설치 상태를 확인하거나 `--chrome-path`를 지정하세요.
- 프로필 사용 중 오류: 로그인용 Chrome과 같은 프로필의 다른 창을 닫으세요.
- `reader-page` 대기 실패: 책을 연 상태인지, 한 페이지 레이아웃인지 확인하세요. 느린 환경에서는 `--timeout`을 늘려보세요.
- PDF 생성 실패: 올바른 실행별 이미지 폴더를 선택했는지와 출력 파일이 이미 존재하는지 확인하세요.
- 드라이버 다운로드 실패: 네트워크·프록시 설정과 Chrome 설치 버전을 확인하세요.

라이선스: MIT. 내보내기 및 복제 권한이 있는 콘텐츠에 사용하세요.

## GitHub Actions에서 동일 기능 검증 및 다운로드

Actions는 macOS·Windows·Ubuntu 단위 테스트와 패키지 검증을 실행합니다. 별도 Ubuntu 작업에서는 실제 Chrome으로 로컬 테스트 페이지를 열고 **웹 화면 → 캡처 → PDF 생성** 흐름을 검증합니다. 테스트용 페이지를 사용하므로 Google 계정은 필요하지 않습니다. 이 검증은 Google Books 서비스 자체의 로그인·책 뷰어 호환성 검증과 구분됩니다.

테스트가 통과하면 `Downloadable application` 작업이 실행 가능한 소스 ZIP, wheel, 소스 배포 패키지를 `sss-pdf-application` 아티팩트로 제공합니다. GitHub 저장소의 **Actions → 성공한 실행 → Artifacts**에서 내려받으세요. 아티팩트는 14일 보관하며 GitHub 접근 권한이 필요할 수 있습니다. Actions 수동 실행은 **Run workflow**에서 가능합니다.

GitHub Actions는 원격 실행 환경이므로 사용자 컴퓨터의 브라우저를 열 수 없습니다. 내려받은 실행기로 같은 로컬 앱을 시작하는 방식입니다. Python 백엔드가 필요한 앱이므로 GitHub Pages 정적 호스팅만으로 로그인·캡처·PDF 변환 전체를 제공할 수 없습니다. 공개 서버 배포 설정은 포함하지 않습니다.

로컬에서 실제 Chrome 통합 테스트도 실행하려면 Chrome을 설치하고 `SSS_PDF_BROWSER_TEST=1`을 설정한 뒤 전체 테스트를 실행하세요. 자동 탐색이 어려우면 `SSS_PDF_CHROME_PATH`에 Chrome 실행 파일의 전체 경로를 지정합니다. 기본 단위 테스트에서는 실제 Chrome 테스트가 건너뛰어질 수 있습니다. Actions의 성공 여부와 각 OS 실행 결과는 해당 실행 로그에서 확인하세요.

## Actions에서 책 URL을 직접 PDF로 변환

프론트엔드 테스트·소스 배포와 별도로 **Capture reader pages to PDF** 워크플로가 핵심 캡처 기능을 실행합니다. 저장소의 **Actions → Capture reader pages to PDF → Run workflow**에서 다음을 입력합니다.

| 입력 | 의미 |
| --- | --- |
| `reader_url` | 캡처할 권한이 있는 책의 리더 URL |
| `pages` | 캡처할 페이지 수, 기본 5 |
| `timeout` | 페이지 준비 대기 시간(초), 기본 30 |

Ubuntu 실행기의 Chrome을 headless로 실행해 페이지를 캡처하고 PDF로 변환합니다. 성공하면 실행 화면의 Artifacts에서 `captured-book-pdf`를 내려받으세요. 이 아티팩트에는 `book.pdf`만 포함되며 3일 보관합니다. 실행별 임시 디렉터리에서 작업하고 쿠키·Chrome 프로필·캡처 이미지·비공개 로그는 업로드하지 않으며 마지막 정리 단계에서 삭제합니다. 실행 제한은 20분입니다.

공개 접근이 가능한 리더는 별도 인증 정보 없이 시도할 수 있습니다. 로그인 세션이 필요하면 GitHub 저장소의 **Settings → Secrets and variables → Actions → New repository secret**에 `SSS_PDF_COOKIES`를 추가할 수 있습니다. 값은 Selenium 쿠키 객체의 JSON 배열입니다. 예를 들어 각 항목에는 `name`, `value`와 필요에 따라 `domain`, `path`, `secure`, `httpOnly`, `expiry`, `sameSite`가 들어갑니다. 실제 세션 값은 README·워크플로 입력·소스에 넣지 말고 비밀값으로 저장하세요.

쿠키는 임시 JSON 파일을 통해 캡처 명령에 전달됩니다. 원격 실행기에서는 대화형 로그인·추가 인증을 할 수 없고, Google이 쿠키 세션이나 원격 브라우저 접속을 거부할 수도 있습니다. 따라서 쿠키를 제공해도 실제 책 캡처 성공이 보장되지는 않습니다. 이러한 경우 로컬 앱에서 로그인한 뒤 실행하세요. 워크플로의 성공 여부는 개별 실행에서 확인하며, 실제 계정 인증 성공을 자동 테스트 통과로 대체하지 않습니다.
