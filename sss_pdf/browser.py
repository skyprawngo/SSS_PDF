"""Browser lifecycle and reader capture; no remote debugging or process killing."""
from pathlib import Path
import time

from .config import AppConfig, find_chrome


def _driver(config: AppConfig, *, login_mode=False):
    from selenium import webdriver
    options = webdriver.ChromeOptions()
    binary = find_chrome(config.chrome_path)
    if binary:
        options.binary_location = binary
    config.profile_dir.mkdir(parents=True, exist_ok=True)
    options.add_argument(f'--user-data-dir={config.profile_dir}')
    if config.headless and not login_mode:
        options.add_argument('--headless=new')
    options.add_argument('--window-size=1341,2100')
    driver = webdriver.Chrome(options=options)
    try:
        driver.set_page_load_timeout(config.timeout)
    except BaseException:
        _quit(driver)
        raise
    return driver


def _quit(driver):
    """Cleanup must not replace the job result or its original exception."""
    import logging
    try:
        driver.quit()
    except Exception:
        logging.getLogger(__name__).warning('WebDriver 종료에 실패했습니다.', exc_info=True)


def login(config: AppConfig) -> None:
    """Open a visible persistent browser; return when the user closes its window.

    This blocks and never reads stdin, so it can run as a web background job.
    Only this WebDriver-owned session is quit on completion.
    """
    from selenium.common.exceptions import WebDriverException
    driver = _driver(config, login_mode=True)
    try:
        driver.get(config.url or 'https://play.google.com/books')
        while True:
            try:
                if not driver.window_handles:
                    return
            except WebDriverException:
                return
            time.sleep(0.5)
    finally:
        _quit(driver)


def _visible_page(driver):
    """Search top document and nested frames, leaving focus at the page's frame."""
    from selenium.webdriver.common.by import By
    from selenium.common.exceptions import NoSuchFrameException, StaleElementReferenceException

    def search(depth):
        for element in driver.find_elements(By.CSS_SELECTOR, 'reader-page[id]'):
            if element.is_displayed() and element.rect['width'] > 0 and element.rect['height'] > 0:
                return element
        if depth >= 5:
            return False
        for frame in driver.find_elements(By.TAG_NAME, 'iframe'):
            try:
                driver.switch_to.frame(frame)
                found = search(depth + 1)
                if found:
                    return found
                driver.switch_to.parent_frame()
            except (NoSuchFrameException, StaleElementReferenceException):
                driver.switch_to.default_content()
                return False
        return False
    driver.switch_to.default_content()
    return search(0)


def _restore_cookies(driver, config: AppConfig) -> None:
    """Restore an explicit cookie export for the configured target host only.

    Authentication depends on the website; imported cookies do not guarantee a
    valid login session. Cookie values and browser error details are never logged.
    """
    import json
    from urllib.parse import urlparse
    if config.cookies_file is None:
        return
    try:
        with config.cookies_file.open('rb') as stream:
            data = stream.read(1024 * 1024 + 1)
    except OSError:
        raise ValueError('쿠키 파일을 읽을 수 없습니다.') from None
    if len(data) > 1024 * 1024:
        raise ValueError('쿠키 파일은 1MB 이하여야 합니다.')
    try:
        exported = json.loads(data)
    except (ValueError, UnicodeError, RecursionError):
        raise ValueError('쿠키 파일은 올바른 JSON 배열이어야 합니다.') from None
    if not isinstance(exported, list) or len(exported) > 500:
        raise ValueError('쿠키 JSON은 최대 500개 항목의 배열이어야 합니다.')
    hostname = urlparse(config.url).hostname
    if not hostname:
        raise ValueError('쿠키 복원에는 유효한 대상 URL이 필요합니다.')
    hostname = hostname.lower()
    allowed = {'name', 'value', 'path', 'domain', 'secure', 'httpOnly', 'expiry', 'sameSite'}
    cookies = []
    for item in exported:
        if not isinstance(item, dict):
            raise ValueError('각 쿠키는 JSON 객체여야 합니다.')
        cookie = {key: value for key, value in item.items() if key in allowed}
        if not isinstance(cookie.get('name'), str) or not cookie['name'] or not isinstance(cookie.get('value'), str):
            raise ValueError('쿠키 name과 value는 문자열이어야 하며 name은 비어 있을 수 없습니다.')
        for key in ('secure', 'httpOnly'):
            if key in cookie and not isinstance(cookie[key], bool):
                raise ValueError('쿠키 secure와 httpOnly는 boolean이어야 합니다.')
        if 'path' in cookie and (not isinstance(cookie['path'], str) or not cookie['path'].startswith('/')):
            raise ValueError('쿠키 path는 /로 시작하는 문자열이어야 합니다.')
        if 'expiry' in cookie and (isinstance(cookie['expiry'], bool) or not isinstance(cookie['expiry'], int) or cookie['expiry'] < 0):
            raise ValueError('쿠키 expiry는 0 이상의 정수여야 합니다.')
        if 'sameSite' in cookie and cookie['sameSite'] not in ('Strict', 'Lax', 'None'):
            raise ValueError('쿠키 sameSite는 Strict, Lax, None 중 하나여야 합니다.')
        if 'domain' in cookie:
            domain = cookie['domain']
            if not isinstance(domain, str) or not domain or domain != domain.strip():
                raise ValueError('쿠키 domain이 올바르지 않습니다.')
            domain = domain.lower()
            bare = domain[1:] if domain.startswith('.') else domain
            if not bare or not (hostname == bare or hostname.endswith('.' + bare)):
                raise ValueError('쿠키 domain은 대상 URL 호스트에 적용 가능해야 합니다.')
            cookie['domain'] = domain
        cookies.append(cookie)
    # Validate the entire export before altering the browser session.
    for cookie in cookies:
        try:
            driver.add_cookie(cookie)
        except Exception:
            raise ValueError('브라우저가 쿠키를 적용하지 못했습니다. 대상 도메인과 쿠키 형식을 확인하세요.') from None
    driver.get(config.url)


def capture(config: AppConfig, progress=None) -> list[Path]:
    """Capture visible reader pages, waiting for page identity changes each turn.

    Output is placed in a fresh run directory. Failure is raised with completed
    files retained for recovery. The login window must be closed before capture.
    """
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.webdriver.common.keys import Keys
    from selenium.common.exceptions import TimeoutException
    from datetime import datetime, timezone
    from uuid import uuid4
    if not config.url:
        raise ValueError('캡처할 URL을 입력하세요.')
    report = progress or (lambda message: None)
    driver = _driver(config)
    saved = []
    try:
        driver.get(config.url)
        if config.cookies_file is not None:
            _restore_cookies(driver, config)
        wait = WebDriverWait(driver, config.timeout)
        run_dir = config.output_dir / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid4().hex[:8])
        previous = None
        for index in range(config.pages):
            def changed_page(browser):
                page = _visible_page(browser)
                return page if page and page.get_attribute('id') != previous else False
            try:
                element = wait.until(changed_page)
            except TimeoutException as exc:
                raise RuntimeError(f'다음 reader-page를 찾지 못했습니다. 로그인·뷰어 설정 또는 책의 마지막 페이지를 확인하세요. 저장된 페이지: {len(saved)}') from exc
            previous = element.get_attribute('id')
            run_dir.mkdir(parents=True, exist_ok=True)
            target = run_dir / f'page-{index + 1:05d}.png'
            if not element.screenshot(str(target)):
                raise RuntimeError(f'스크린샷 저장에 실패했습니다: {target}')
            saved.append(target)
            report(f'{index + 1}/{config.pages}: {target.name}')
            if index + 1 < config.pages:
                # Switching frame context alone does not move keyboard focus.
                # Focus the reader without clicking links or changing selection.
                driver.execute_script("""
                    window.focus();
                    const page = arguments[0];
                    const previous = page.getAttribute('tabindex');
                    page.setAttribute('tabindex', '-1');
                    page.focus({preventScroll: true});
                    if (previous === null) page.removeAttribute('tabindex');
                    else page.setAttribute('tabindex', previous);
                """, element)
                ActionChains(driver).send_keys(Keys.ARROW_RIGHT).perform()
        return saved
    finally:
        _quit(driver)
