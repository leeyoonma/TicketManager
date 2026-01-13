import time
from datetime import datetime
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import easyocr
import os 
from dotenv import load_dotenv
import ssl
import tkinter as tk
from tkinter import messagebox

ssl._create_default_https_context = ssl._create_unverified_context

load_dotenv()

TARGET_URL = os.getenv("TARGET_URL")
SEAT_COLOR = os.getenv("SEAT_COLOR")

user_credentials = {}

def show_input_gui():
    """GUI를 통해 로그인 정보와 오픈 타임 입력받기"""
    def on_submit():
        open_time = entry_open_time.get().strip()
        
        # 시간 형식 검증 (HH:MM:SS)
        try:
            datetime.strptime(open_time, "%H:%M:%S")
        except ValueError:
            messagebox.showerror("형식 오류", "시간 형식이 올바르지 않습니다!\n예: 20:00:00")
            return
        
        user_credentials['open_time'] = open_time
        
        root.destroy()
    
    root = tk.Tk()
    root.title("인터파크 티켓팅 자동화")
    root.geometry("400x250")
    root.resizable(False, False)
    
    # 중앙 정렬
    root.eval('tk::PlaceWindow . center')
    
    # 타이틀
    tk.Label(root, text="티켓팅 정보 입력", font=("Helvetica", 16, "bold")).pack(pady=15)
    
    # 오픈 타임 입력
    frame_open_time = tk.Frame(root)
    frame_open_time.pack(pady=5)
    tk.Label(frame_open_time, text="오픈 타임:", width=10, anchor='e').pack(side=tk.LEFT, padx=5)
    entry_open_time = tk.Entry(frame_open_time, width=25)
    entry_open_time.insert(0, "20:00:00")  # 기본값
    entry_open_time.pack(side=tk.LEFT)
    
    # 안내 문구
    tk.Label(root, text="형식: HH:MM:SS (예: 20:00:00)", 
             font=("Helvetica", 9), fg="gray").pack(pady=5)
    
    # 시작 버튼
    tk.Button(root, text="시작", command=on_submit, 
              bg="#4CAF50", fg="white", font=("Helvetica", 12, "bold"),
              width=15, height=1).pack(pady=15)
    
    root.mainloop()
    
    # GUI가 닫힌 후 입력값 반환
    return user_credentials

def setup_driver():
    options = uc.ChromeOptions()

    user_data = r"/Users/dgsw03/Library/Application Support/Google/Chrome"
    options.add_argument(f"--user-data-dir={user_data}")
    options.add_argument("--profile-directory=Profile 1")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    
    print("Chrome 브라우저 시작 중... (기존 Chrome을 모두 종료해주세요)")
    driver = uc.Chrome(options=options, version_main=None, use_subprocess=False)
    print("Chrome 브라우저 시작 완료")
    return driver


def wait_for_open(driver, target_time):
    print("예매 페이지로 이동 중...")
    try:
        driver.get("https://ticket.yes24.com/Special/56674")
        # 페이지 로딩 대기
        WebDriverWait(driver, 10).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        print("예매 페이지 로딩 완료")
    except Exception as e:
        print(f"페이지 로딩 오류: {e}")
        print("수동으로 페이지를 확인하세요.")
    
    print(f"{target_time} 정각까지 대기합니다...")
    while True:
        now = datetime.now().strftime("%H:%M:%S")
        if now >= target_time:
            driver.find_element(By.CSS_SELECTOR, '.sideBtn.is-primary').click()
            
            driver.switch_to.window(driver.window_handles[-1])
            print("예매 창으로 전환 완료")
            
            try:
                time.sleep(1) 
                iframe = driver.find_element(By.XPATH, '//*[@id="ifrmSeat"]')
                driver.switch_to.frame(iframe)
                print("iframe으로 전환 완료")
            except:
                print("iframe 없음, 현재 창에서 진행")
            
            print(f"정각 진입 시도: {now}")
            break
        time.sleep(0.01)

def booking_process(driver):
    reader = easyocr.Reader(['en'])
    
    print('보안문자 대기 중...')
    wait = WebDriverWait(driver, 30)
    captcha_img_element = wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "img[alt*='캡챠 이미지']"))
    )
    print("보안문자 캡쳐 완료")

    while captcha_img_element:
      captcha_img_element.screenshot("captcha.png")
      result = reader.readtext("captcha.png", detail=0)
      captcha_text = "".join(result).replace(" ", "").replace('5','S').replace('0','O')\
        .replace('1','I').replace('$','S').replace('8','B').replace(',','')\
        .replace('€','C').replace('e','Q').replace('.','').replace('(','').replace(')','')\
        .replace('-','').replace(':','').replace('3','S').replace('}','').upper() 
      
      print(f"인식된 보안문자: {captcha_text}")
      input_field = driver.find_element(By.XPATH, "//*[@id=\"__next\"]/div[2]/div/div/div/div/input")
      input_field.clear() 
      input_field.send_keys(captcha_text)
      driver.find_element(By.XPATH, "//*[@id=\"__next\"]/div[2]/div/footer/button").click()
      
      # 처리 결과 대기
      time.sleep(0.2)
      
      try:
          error_msg = driver.find_element(By.XPATH, '//*[@id="__next"]/div[2]/div/div/div/div/div[2]')
          if error_msg.is_displayed() or len(captcha_text) != 6:
              print("보안문자 오류, 재시도합니다.")
              driver.find_element(By.XPATH, '//*[@id="__next"]/div[2]/div/div/div/div/div[1]/button[2]').click()
              time.sleep(0.5)
              captcha_img_element = wait.until(
                  EC.presence_of_element_located((By.CSS_SELECTOR, "img[alt*='캡챠 이미지']"))
              )
              continue
      except:
          print(f"보안문자 입력 완료: {captcha_text}")
          break
    
    while True:
        try:
            print("좌석 선택 시도 중...")
            seats = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, f"circle[fill='{SEAT_COLOR}']")))
            
            if seats:
                seats[0].click()
                print("좌석 클릭 성공!")

                driver.find_element(By.XPATH, "//*[@id=\"__next\"]/div/div/main/div[2]/aside/section/div/div[3]/button").click()
                
                time.sleep(0.2)
                try:
                    modal = driver.find_element(By.CSS_SELECTOR, "div[role='dialog'], .modal, .popup, [class*='modal'], [class*='popup'], [class*='alert']")
                    
                    if modal.is_displayed():
                        modal_text = modal.text
                        print(f"모달 감지: {modal_text}")
                        
                        if any(keyword in modal_text for keyword in ["이미 선택", "선택된 좌석", "이선좌", "선점", "다른 좌석"]):
                            print("이선좌 발생. 재시도합니다.")
                            try:
                                confirm_btn = modal.find_element(By.XPATH, ".//button[contains(text(), '확인') or contains(text(), '닫기') or contains(text(), 'OK')]")
                                confirm_btn.click()
                            except:
                                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                            time.sleep(0.2)
                            continue
                        else:
                            print("좌석 선택 성공")
                            break
                except:
                    print("좌석 선택 성공")
                    break
            else: 
              time.sleep(0.1)
                
            
        except Exception as e:
            # 아직 로딩 중이면 계속 반복
            time.sleep(0.1)


# --- 실행 ---
if __name__ == '__main__':
    print("="*50)
    print("인터파크 티켓팅 자동화 프로그램")
    print("="*50)

    credentials = show_input_gui()

    if not credentials:
        print("프로그램이 취소되었습니다.")
        exit()

    open_time = credentials['open_time']

    print(f"\n설정된 오픈 타임: {open_time}")
    print("브라우저를 실행합니다...\n")

    driver = setup_driver()
    try:
        wait_for_open(driver, open_time)
        booking_process(driver)
    finally:
        # 프로그램 종료 시 창이 바로 닫히지 않게 대기
        input("티켓팅이 완료되었나요? 엔터를 누르면 종료됩니다.")
        driver.quit()