SSS_PDF (Sequence ScreenShot to PDF)
===

* 사용 용도 : Google Books에서 구매한 책 PDF 따기
* 사용 목적 : 내보내기 불가능한 책을 다운로드 하려는 목적

사용환경(Environment Requirements)
---

* python
* selenium
* google chrome 및 동일한 버전의 chromedriver (same version)
* img2pdf

사용방법
---

0. 위의 사용환경을 전부 설치한다.
1. didyou_set_your_session 값을 False 상태에서 한 번 실행시킨다.
    * 당신의 로그인 세션 정보를 ChromeWebdriver에 저장시킨다.
2. 당신이 구매한 책의 Url을 복사해 set_url에 붙여넣는다.
3. 전체 페이지쪽수를 적어넣는다. (50개로 두고 여러번 실행시켜도 됨.)
4. pngtopdf.py 파일을 실행해 SS_temp 디렉토리 내부의 모든 png 파일을 pdf로 묶는다.

*** 

* Purpose: Extracting PDF files from books purchased on Google Books.
* Objective: To download books that cannot be exported.

Usage Instructions
---

0.	Install all the required environment components listed above.
1.	Run the program with the value of didyou_set_your_session set to False once.
    •	This step saves your login session information to Chrome WebDriver.
2.	Copy the URL of the book you purchased and paste it into set_url.
3.	Enter the total number of pages in the book. (You can set it to 50 and run the program multiple times.)
4.	Run the pngtopdf.py script to combine all the PNG files inside the SS_temp directory into a single PDF.