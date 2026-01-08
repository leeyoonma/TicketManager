import time
from datetime import datetime
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import easyocr
import os 
from dotenv import load_dotenv
import ssl
import certifi

ssl._create_default_https_context = ssl._create_unverified_context

load_dotenv()

TARGET_URL = os.getenv("TARGET_URL")
OPEN_TIME = os.getenv("OPEN_TIME")
SEAT_COLOR = os.getenv("SEAT_COLOR")

def setup_driver():
    options = uc.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    
    driver = uc.Chrome(options=options, version_main=None, use_subprocess=True)
    return driver

def login_and_wait(driver):
    # 로그인 페이지로 이동
    driver.get("https://ticket.interpark.com/Gate/TPLogin.asp")
    print("60초 이내에 수동으로 로그인을 완료해주세요.")
    time.sleep(60) 

def wait_for_open(driver, target_time, url):
    print(f"{target_time} 정각까지 대기합니다...")
    while True:
        now = datetime.now().strftime("%H:%M:%S")
        if now >= target_time:
            driver.get(url)
            print(f"정각 진입 시도: {now}")
            break
        time.sleep(0.01)

def booking_process(driver):
    
    driver.find_element(By.XPATH, '//*[@id="productSide"]/div/div[2]/a[1]').click()
    WebDriverWait(driver, 10).until(lambda d: len(d.window_handles) > 1)
    driver.switch_to.window(driver.window_handles[-1])
    
    # print("대기열 통과 및 좌석표 로딩 감시 중...")
    # wait = WebDriverWait(driver, 60) # 최대 60초 대기
    
    reader = easyocr.Reader(['en'])

    captcha_img_element = driver.find_element(By.XPATH, "//*[@id=\"__next\"]/div[2]/div/div/div/div/div[1]/div[2]")


    while captcha_img_element:
  
        captcha_img_element.screenshot("captcha.png")
        result = reader.readtext("captcha.png", detail=0)
        captcha_text = "".join(result).replace(" ", "").upper() # 공백 제거 및 대문자화
        
        # 3. 입력창에 입력 및 확인 버튼 클릭
        input_field = driver.find_element(By.ID, "txtCaptcha")
        input_field.clear() 
        input_field.send_keys(captcha_text)
        driver.find_element(By.ID, "btnCaptcha_Ok").click()
        print(f"보안문자 입력 완료: {captcha_text}")
        display = driver.find_element(By.XPATH, '//*[@id="__next"]/div[2]/div/div/div/div/div[2]').is_displayed()

        if display:
          print(f"보안문자 처리 실패: {e}")
          driver.find_element(By.XPATH, "//*[@id=\"__next\"]/div[2]/div/div/div/div/div[1]/button[2]").click()
        else:
          print("보안문자 처리 성공")
          break

    
    while True:
        try:
            seats = driver.find_elements(By.CSS_SELECTOR, f"circle[fill='{SEAT_COLOR}']")
            
            if seats:
                seats[0].click()
                print("좌석 클릭 성공!")

                driver.find_element(By.XPATH, "//*[@id=\"__next\"]/div/div/main/div[2]/aside/section/div/div[3]/button").click()
                
                time.sleep(0.2)
                try:
                    alert = driver.switch_to.alert
                    print(f"이선좌 발생: {alert.text}. 재시도합니다.")
                    alert.accept()
                    continue 
                except:
                    print("좌석 선택 성공")
                    break
            else: 
              time.sleep(0.1)
                
            
        except Exception as e:
            # 아직 로딩 중이면 계속 반복
            time.sleep(0.1)


# --- 실행 ---
driver = setup_driver()
try:
    login_and_wait(driver)
    wait_for_open(driver, OPEN_TIME, TARGET_URL)
    booking_process(driver)
finally:
    # 프로그램 종료 시 창이 바로 닫히지 않게 대기
    input("티켓팅이 완료되었나요? 엔터를 누르면 종료됩니다.")
    driver.quit()