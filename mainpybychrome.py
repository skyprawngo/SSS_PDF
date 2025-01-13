import os
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from PIL import Image
import time
import socket
from subprocess import Popen

# URL 저장 파일 경로
URL_SAVE_FILE = "./last_url.json"

def save_last_url(url):
    """현재 URL을 JSON 파일에 저장"""
    with open(URL_SAVE_FILE, "w") as file:
        json.dump({"last_url": url}, file)
    print(f"URL 저장 완료: {url}")

def load_last_url(default_url):
    """저장된 URL을 불러옴. 없으면 기본값 반환"""
    if os.path.exists(URL_SAVE_FILE):
        with open(URL_SAVE_FILE, "r") as file:
            data = json.load(file)
            return data.get("last_url", default_url)
    return default_url

def is_chrome_open(port):
    """포트가 열려 있는지 확인 (Chrome이 실행 중인지 체크)"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        result = sock.connect_ex(('127.0.0.1', port))
        return result == 0

def start_chrome_with_debugger(port, user_data_dir, chrome_path):
    """Chrome 디버깅 모드로 실행. 디버깅 포트가 열려 있지 않으면 Chrome을 시작."""
    if not is_chrome_open(port):
        print(f"Chrome 디버깅 포트 {port}이 열려있지 않습니다. Chrome을 새로 시작합니다.")
        Popen([
            chrome_path,
            f"--remote-debugging-port={port}",
            f"--user-data-dir={user_data_dir}"
        ])
        time.sleep(5)  # Chrome이 완전히 열리도록 대기
    else:
        print(f"Chrome 디버깅 포트 {port}이 이미 열려 있습니다.")

# ChromeDriver와 연결된 포트 정보 설정
CHROME_DEBUGGER_PORT = 9222
USER_DATA_DIR = "/tmp/chrome_debug"  # 세션 유지 디렉토리
CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# Chrome 디버깅 모드 실행 함수 호출
start_chrome_with_debugger(CHROME_DEBUGGER_PORT, USER_DATA_DIR, CHROME_PATH)

chrome_options = Options()
chrome_options.add_experimental_option("debuggerAddress", f"127.0.0.1:{CHROME_DEBUGGER_PORT}")
chrome_options.add_argument(f"user-data-dir={USER_DATA_DIR}")

# ChromeDriver 실행 (새로 실행하지 않고 기존 디버깅 세션에 연결)
driver = webdriver.Chrome(options=chrome_options)
driver.set_window_size(2000, 1080)

# 기존 URL 복원
default_url = "https://play.google.com/books/reader?id=ZP1LEAAAQBAJ&pg=GBS.PA1"
current_url = load_last_url(default_url)
print(f"복원된 URL: {current_url}")

# 새로고침 방지
if driver.current_url != current_url:
    driver.get(current_url)

# 스크롤 위치 저장 및 복원
scroll_position = 0
try:
    scroll_position = driver.execute_script("return window.scrollY;")
    print(f"저장된 스크롤 위치: {scroll_position}")
except Exception as e:
    print(f"스크롤 위치 저장 실패: {e}")

# 작업 수행
time.sleep(5)
full_screenshot_path = "./full_screenshot.png"
driver.save_screenshot(full_screenshot_path)

# 크롭 작업
crop_rectangle = (1362, 134, 2636, 1914)  # (왼쪽 x, 위쪽 y, 오른쪽 x, 아래쪽 y)
screenshot = Image.open(full_screenshot_path)
cropped_screenshot = screenshot.crop(crop_rectangle)
cropped_screenshot_path = "./cropped_screenshot.png"
cropped_screenshot.save(cropped_screenshot_path)

print("특정 영역 스크린샷 완료!")

# 현재 URL 저장
save_last_url(driver.current_url)

# 브라우저 종료하지 않음
print("브라우저는 종료되지 않고 유지됩니다. 저장된 URL로 다음 실행에 재사용 가능합니다.")