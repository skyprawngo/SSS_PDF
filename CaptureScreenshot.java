package app.src.main.java;

import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.chrome.ChromeDriver;
import com.assertthat.selenium_shutterbug.core.Shutterbug;

public class CaptureScreenshot {
  public static void main(String[] args) {
    // ChromeDriver 경로 설정
    System.setProperty("webdriver.chrome.driver", "path/to/chromedriver");

    // WebDriver 초기화
    WebDriver driver = new ChromeDriver();

    try {
      // 페이지 로드
      driver.get("https://play.google.com/books/reader?id=FB-rEAAAQBAJ&pg=GBS.PP1");

      // 특정 요소 찾기
      WebElement element = driver.findElement(By.className("text-layer"));

      // 요소 스크린샷 캡처 및 저장
      Shutterbug.shootElement(driver, element).withName("element_screenshot").save("path/to/save");

      // 전체 페이지 스크린샷
      Shutterbug.shootPage(driver).withName("full_page_screenshot").save("path/to/save");

      System.out.println("스크린샷이 저장되었습니다.");
    } catch (Exception e) {
      e.printStackTrace();
    } finally {
      // WebDriver 종료
      driver.quit();
    }
  }
}