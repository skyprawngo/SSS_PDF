import os
import base64
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import time
import socket
import atexit
from urllib.parse import urlparse, parse_qs
from subprocess import Popen
import signal

# 스크린샷 저장 폴더 설정
SCREENSHOT_FOLDER = "SS_temp"


# 전역 변수
# ChromeDriver와 연결된 포트 정보 설정
CHROME_DEBUGGER_PORT = 9222
USER_DATA_DIR = "/tmp/chrome_debug"  # 세션 유지 디렉토리
CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
set_url = "https://play.google.com/books/reader?id=FB-rEAAAQBAJ&pg=GBS.PP1"


def close_chrome_and_port(port=9222):
  """
  Chrome WebDriver를 종료하고 디버깅 포트(9222)를 닫습니다.
  """
  global driver

  # WebDriver 종료
  try:
    if driver:
      driver.quit()
      print("Chrome WebDriver가 종료되었습니다.")
  except Exception as e:
    print(f"WebDriver 종료 중 오류 발생: {e}")

  # 디버깅 포트를 사용하는 프로세스 종료
  try:
    # 포트를 사용하는 프로세스 찾기
    command = f"lsof -i :{port} | grep LISTEN"
    process_output = os.popen(command).read().strip()

    if process_output:
      # 프로세스 ID 추출
      pid = int(process_output.split()[1])
      os.kill(pid, signal.SIGKILL)
      print(f"포트 {port}를 사용하는 프로세스(PID: {pid})가 종료되었습니다.")
    else:
      print(f"포트 {port}를 사용하는 프로세스가 없습니다.")
  except Exception as e:
    print(f"포트 종료 중 오류 발생: {e}")


# 폴더 생성 함수
def ensure_screenshot_folder_exists():
  if not os.path.exists(SCREENSHOT_FOLDER):
    os.makedirs(SCREENSHOT_FOLDER)
    print(f"스크린샷 폴더 생성 완료: {SCREENSHOT_FOLDER}")
  else:
    print(f"스크린샷 폴더가 이미 존재합니다: {SCREENSHOT_FOLDER}")


def is_chrome_open(port):
  with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    result = sock.connect_ex(("127.0.0.1", port))
  return result == 0


def get_reader_page_id():
  """
  iframe 내부의 reader-page 태그의 단일 id 값을 반환합니다.

  Returns:
      str: reader-page 태그의 id 값 (존재하지 않으면 None 반환)
  """
  try:
    # iframe 대기 및 전환
    iframe = WebDriverWait(driver, 10).until(
      EC.presence_of_element_located((By.TAG_NAME, "iframe"))
    )
    driver.switch_to.frame(iframe)

    # reader-page 요소 찾기
    reader_page = WebDriverWait(driver, 10).until(
      EC.presence_of_element_located((By.CSS_SELECTOR, "reader-page[id]"))
    )

    # id 값 추출
    reader_page_id = reader_page.get_attribute("id")
    print(f"추출된 reader-page ID 값: {reader_page_id}")
    return reader_page_id

  except Exception as e:
    print(f"reader-page ID 추출 중 오류 발생: {e}")
    return None

  finally:
    # iframe 해제
    driver.switch_to.default_content()


def start_chrome_with_debugger(port, user_data_dir, chrome_path, headless=False):
  """
  Chrome 디버깅 모드로 실행.
  디버깅 포트가 열려 있지 않으면 Chrome을 새로 시작.
  """
  if not is_chrome_open(port):
    print(
      f"Chrome 디버깅 포트 {port}이 열려있지 않습니다. Chrome을 새로 시작합니다."
    )
    chrome_args = [
      chrome_path,
      f"--remote-debugging-port={port}",
      f"--user-data-dir={user_data_dir}",
    ]
    if headless:
      chrome_args.append("--headless")

    # 크롬 실행
    Popen(chrome_args)
    # 대기 시간을 충분히 늘림 (5 -> 10초)
    time.sleep(3)

    # 대기 후에도 포트가 안 열려 있으면 경고
    if not is_chrome_open(port):
      raise RuntimeError(
        f"Chrome이 {port} 포트로 열리지 않았습니다. "
        "ChromeDriver와 Chrome 버전 호환성, 또는 실행 경로를 확인하세요."
      )
  else:
    print(f"Chrome 디버깅 포트 {port}이 이미 열려 있습니다.")


def initialize_driver(headless=False, debugging=False):
  """
  ChromeDriver 초기화 및 설정
  """
  global driver  # 전역 driver 사용
  if debugging:
    # 디버깅 모드로 Chrome 실행 시도
    start_chrome_with_debugger(
      CHROME_DEBUGGER_PORT, USER_DATA_DIR, CHROME_PATH, headless
    )

  chrome_options = Options()
  chrome_options.add_experimental_option(
    "debuggerAddress", f"127.0.0.1:{CHROME_DEBUGGER_PORT}"
  )
  chrome_options.add_argument(f"user-data-dir={USER_DATA_DIR}")
  chrome_options.add_argument("--disable-dev-shm-usage")
  chrome_options.add_argument("--disable-devtools")
  chrome_options.add_argument("--lang=ko")
  chrome_options.add_argument(f"user-agent={user_agent}")
  if headless:
    chrome_options.add_argument("--headless")

  # 디버깅 모드로 연결을 시도
  # 만약 위에서 제대로 포트가 열리지 않았다면 여기서 에러가 발생
  driver = webdriver.Chrome(options=chrome_options)
  driver.set_window_size(1341, 2100)
  time.sleep(2)
  

def capture_element_screenshot(int_page, output_filename="element_screenshot.png"):
  """
  DevTools Protocol을 사용해 iframe 내부의 특정 요소를 캡처
  (요소가 실제로 보이도록 visibility_of_element_located 사용)
  """
  output_path = os.path.join(SCREENSHOT_FOLDER, output_filename)

  try:
    print("확인용1")
    # iframe이 새로 로드됐을 가능성이 있으므로, 다시 찾아서 전환
    iframe = WebDriverWait(driver, 10).until(
      EC.presence_of_element_located((By.TAG_NAME, "iframe"))
    )
    driver.switch_to.frame(iframe)
    print("확인용2")
    
    # 동적으로 page-0-0, page-1-0, page-2-0 ... 형태의 selector를 생성
    page_selector = f'reader-page[id="page-{int_page}-0"]'
    print(f"캡처할 selector: {page_selector}")
    
    # 요소가 보이도록 기다리기 (visibility_of_element_located)
    element = WebDriverWait(driver, 10).until(
      EC.visibility_of_element_located((By.CSS_SELECTOR, page_selector))
    )
    print("확인용3")

    # 요소의 위치와 크기 가져오기
    bounding_box = driver.execute_script(
      """
      const rect = document.querySelector(arguments[0]).getBoundingClientRect();
      return {
        x: rect.x,
        y: rect.y,
        width: rect.width,
        height: rect.height
      };
      """,
      page_selector,
    )

    print("Bounding Box:", json.dumps(bounding_box, indent=4))

    # 혹시라도 bounding_box가 여전히 0이면 추가 대기 or 재시도 로직을 둘 수도 있음
    if bounding_box["width"] == 0 or bounding_box["height"] == 0:
      print("⚠️ Bounding Box가 0입니다. 재시도 또는 대기 시간이 더 필요할 수 있습니다.")

    # DevTools Protocol 설정
    screenshot_config = {
      "fromSurface": True,
      "clip": {
        "x": bounding_box["x"],
        "y": bounding_box["y"],
        "width": bounding_box["width"],
        "height": bounding_box["height"],
        "scale": 1,
      },
    }
    
    time.sleep(2)
    base_64_png = driver.execute_cdp_cmd("Page.captureScreenshot", screenshot_config)

    # base64 이미지를 디코딩하여 파일로 저장
    with open(output_path, "wb") as file:
      file.write(base64.b64decode(base_64_png["data"]))
    print(f"요소 스크린샷 저장 완료: {output_path}")

  except Exception as e:
    print(f"요소 스크린샷 저장 중 오류 발생: {e}")

  finally:
    # iframe 해제
    driver.switch_to.default_content()


def main():
  try: 
    headless_mode = True
    debugging = True  # 디버깅 모드 활성화
    repeats_left = 30  # for문 최대 반복 횟수
    past_url = None
    current_page_id = "page-0-0"
    initialize_driver(headless=headless_mode, debugging=debugging)
    current_url = driver.current_url
    set_url_id = parse_qs(urlparse(set_url).query).get("id", [None])[0]
    current_url_id = parse_qs(urlparse(current_url).query).get("id", [None])[0]
    
    # 초기 URL 설정, page id 설정
    if current_url_id == set_url_id:
      print("현재 페이지의 ID와 set_url의 ID가 동일합니다.")
      print(f"현재 페이지 : {current_url}")
      driver.get(current_url)
      # reader-page의 id값 가져오기
      current_page_id = get_reader_page_id()
    else:
      print("현재 페이지의 ID와 set_url의 ID가 동일하지 않습니다.")
      print(f"설정한 페이지로 이동 : {set_url}")
      driver.get(set_url)

    
    # current_page_id에서 중앙의 숫자 값 추출
    int_page = int(current_page_id.split('-')[1])
    while debugging and int_page < int_page+repeats_left:
      print(f"앞으로 {repeats_left}번 반복함.")

      screenshot_filename = f"tmp_screenshot_{int_page}.png"

      # 실제 캡처 수행
      capture_element_screenshot(int_page, screenshot_filename)
      repeats_left -= 1
      int_page += 1

      # 현재 URL과 past_url 비교
      current_url = driver.current_url
      print(f"현재 URL: {current_url}, 과거 URL: {past_url}")
      if current_url == past_url:
        print("현재 URL이 과거 URL과 동일합니다. 반복을 종료합니다.")
        break

      past_url = current_url

      # 다음 동작 (우측 방향키 입력 등)
      WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
      )
      ActionChains(driver).send_keys(Keys.ARROW_RIGHT).perform()
      WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
      )
      
    print("디버깅 반복 종료 또는 최대 반복 횟수 도달.")

  except Exception as e:
    print(f"예외 발생: {e}")
    # close_chrome_and_port()

# 프로그램 실행
if __name__ == "__main__":
  ensure_screenshot_folder_exists()  # 폴더 존재 확인
  main()
