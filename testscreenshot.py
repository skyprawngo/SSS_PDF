import base64
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service

# 셀레니움 드라이버 실행
options = webdriver.ChromeOptions()
driver = webdriver.Chrome(options=options)

# 윈도우 크기 설정 (1920x1080)
driver.set_window_size(1920, 1080)

# URL 설정
url = 'https://www.naver.com/'

# 실행
driver.get(url)

# 페이지 로드 완료 대기
WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))

# 현재 윈도우 크기 가져오기
window_size = driver.get_window_size()
print(f"Browser width: {window_size['width']}, height: {window_size['height']}")

# 페이지 레이아웃 메트릭 가져오기
page_rect = driver.execute_cdp_cmd('Page.getLayoutMetrics', {})
print(f"Content width: {page_rect['contentSize']['width']}, Content height: {page_rect['contentSize']['height']}")

# 스크린샷 구성 설정
screenshot_config = {
  'captureBeyondViewport': True,
  'fromSurface': True,
  'clip': {
    'width': page_rect['contentSize']['width'],  # 'cssContentSize' 확인 필요
    'height': page_rect['contentSize']['height'],
    'x': 0,
    'y': 0,
    'scale': 1
  }
}

# 스크린샷 캡처
base_64_png = driver.execute_cdp_cmd('Page.captureScreenshot', screenshot_config)

# 이미지 파일 저장
with open("chrome-devtools-protocol.png", "wb") as fh:
  fh.write(base64.urlsafe_b64decode(base_64_png['data']))

# 드라이버 종료
driver.quit()