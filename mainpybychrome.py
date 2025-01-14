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
from subprocess import Popen
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
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


def get_previous_screenshot_filename():
  """
  SCREENSHOT_FOLDER에 있는 파일 중 tmp_screenshot_~.png 형식의 마지막 숫자를 반환.
  """
  try:
    # 폴더에서 파일 목록 가져오기
    files = os.listdir(SCREENSHOT_FOLDER)

    # "tmp_screenshot_"로 시작하고 ".png"로 끝나는 파일 필터링 및 정렬
    screenshot_files = sorted(
      [f for f in files if f.startswith("tmp_screenshot_") and f.endswith(".png")]
    )

    if not screenshot_files:
      print("유효한 스크린샷 파일이 없습니다.")
      return 0

    # 가장 마지막 파일 이름
    last_file = screenshot_files[-1]

    # 파일 이름에서 숫자 부분 추출
    number_part = last_file[len("tmp_screenshot_") : -len(".png")]
    return int(number_part)

  except Exception as e:
    print(f"파일 검사 중 오류 발생: {e}")
    return 0


def is_chrome_open(port):
  with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    result = sock.connect_ex(("127.0.0.1", port))
  return result == 0


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
    time.sleep(10)

    # 대기 후에도 포트가 안 열려 있으면 경고
    if not is_chrome_open(port):
      raise RuntimeError(
        f"Chrome이 {port} 포트로 열리지 않았습니다. "
        "ChromeDriver와 Chrome 버전 호환성, 또는 실행 경로를 확인하세요."
      )
  else:
    print(f"Chrome 디버깅 포트 {port}이 이미 열려 있습니다.")


def compare_and_get_reset_url(set_url, loaded_url):
  # set_url과 loaded_url의 id와 pg 값을 비교하여 reset_url을 반환
  if not loaded_url:  # loaded_url이 None인 경우 기본 set_url 반환
    return set_url

  # URL 파싱
  set_url_parsed = urlparse(set_url)
  loaded_url_parsed = urlparse(loaded_url)

  # 쿼리 파라미터 추출
  set_params = parse_qs(set_url_parsed.query)
  loaded_params = parse_qs(loaded_url_parsed.query)

  # id 값 비교
  if set_params.get("id") == loaded_params.get("id"):
    # pg 값 비교
    set_pg = set_params.get("pg", [""])[0]
    loaded_pg = loaded_params.get("pg", [""])[0]

    # pg 값 순서 비교 함수
    def pg_to_order(pg):
      if not pg.startswith("GBS."):
        return float("inf")  # 예외적으로 잘못된 형식은 가장 큰 값으로 처리
      pg = pg[4:]  # "GBS." 제거
      prefix_order = {"PP": 1, "PA": 2, "RA": 3}  # 우선순위 정의 (RA 유지)
      prefix = pg[:2]  # "PP", "PA", "RA" 추출
      number = int(pg[2:]) if pg[2:].isdigit() else float("inf")  # 숫자 추출

      # "RA"를 "RA1-PA"로 변경
      if prefix == "RA":
        prefix = "RA1-PA"

      return (prefix_order.get(prefix, float("inf")), number)

    # pg 순서 비교
    set_order = pg_to_order(set_pg)
    loaded_order = pg_to_order(loaded_pg)

    # 더 큰 pg 값을 reset_url로 선택
    if loaded_order > set_order:
      reset_params = loaded_params
    else:
      reset_params = set_params
  else:
    # id 값이 다르면 기본 set_url 사용
    reset_params = set_params

  # 새로운 URL 생성
  reset_url = urlunparse(
    (
      set_url_parsed.scheme,
      set_url_parsed.netloc,
      set_url_parsed.path,
      set_url_parsed.params,
      urlencode(reset_params, doseq=True),
      set_url_parsed.fragment,
    )
  )
  return reset_url


def ensure_page_loaded(driver, set_url, loaded_url):
  """
  현재 URL과 set_url을 비교하여 페이지를 새로 로드할 필요가 있는지 확인하고,
  필요하면 reset_url로 페이지를 로드합니다.
  """
  reset_url = compare_and_get_reset_url(set_url, loaded_url)
  print(f"선택된 reset_url: {reset_url}")

  # 새로고침 방지
  if driver.current_url != reset_url:
    print(f"다른 URL이 감지되었습니다. 페이지를 로드합니다: {reset_url}")
    driver.get(reset_url)
    WebDriverWait(driver, 10).until(
      EC.presence_of_element_located((By.TAG_NAME, "body"))
    )  # 페이지 로딩 확인
    time.sleep(4)  # 로딩 후 대기
  else:
    print("URL이 동일하므로 재요청하지 않습니다.")
    time.sleep(1)


def capture_element_screenshot(selector, output_filename="element_screenshot.png"):
  """
  DevTools Protocol을 사용해 iframe 내부의 특정 요소를 캡처
  (요소가 실제로 보이도록 scrollIntoView 및 visibility_of_element_located 사용)
  """
  output_path = os.path.join(SCREENSHOT_FOLDER, output_filename)

  try:
    # iframe이 새로 로드됐을 가능성이 있으므로, 다시 찾아서 전환
    iframe = WebDriverWait(driver, 10).until(
      EC.presence_of_element_located((By.TAG_NAME, "iframe"))
    )
    driver.switch_to.frame(iframe)

    # 요소가 보이도록 기다리기 (visibility_of_element_located)
    element = WebDriverWait(driver, 10).until(
      EC.visibility_of_element_located((By.CSS_SELECTOR, selector))
    )

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
      selector,
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


def main():
  try: 
    headless_mode = True
    debugging = True  # 디버깅 모드 활성화
    screenshot_filename_counter = get_previous_screenshot_filename()
    initialize_driver(headless=headless_mode, debugging=debugging)

    # 초기 URL 설정
    past_url = driver.current_url  # 첫 번째 실행 시 기준 URL 설정
    ensure_page_loaded(driver=driver, set_url=set_url, loaded_url=past_url)
    max_repeats = 5  # 최대 반복 횟수
    repeat_count = 0  # 현재 반복 횟수

    while debugging and repeat_count < max_repeats:
      print(f"반복 실행 횟수: {repeat_count + 1}/{max_repeats}")

      screenshot_filename = f"tmp_screenshot_{screenshot_filename_counter}.png"

      # 동적으로 page-0-0, page-1-0, page-2-0 ... 형태의 selector를 생성
      page_selector = f'reader-page[id="page-{repeat_count}-0"]'
      print(f"캡처할 selector: {page_selector}")

      # 캡처하기 전에 해당 요소가 페이지에 등장했는지 기다림
      WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
      )

      # 실제 캡처 수행
      capture_element_screenshot(page_selector, screenshot_filename)
      screenshot_filename_counter += 1

      # 다음 동작 (우측 방향키 입력 등)
      WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
      )
      ActionChains(driver).send_keys(Keys.ARROW_RIGHT).perform()
      time.sleep(2)

      # 현재 URL과 past_url 비교
      current_url = driver.current_url
      print(f"현재 URL: {current_url}, 과거 URL: {past_url}")
      if current_url == past_url:
        print("현재 URL이 과거 URL과 동일합니다. 반복을 종료합니다.")
        break

      past_url = current_url
      repeat_count += 1

    print("디버깅 반복 종료 또는 최대 반복 횟수 도달.")

  except Exception as e:
    print(f"예외 발생: {e}")

# 프로그램 실행
if __name__ == "__main__":
  ensure_screenshot_folder_exists()  # 폴더 존재 확인
  main()
  # close_chrome_and_port()
