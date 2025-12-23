# test_selenium.py

import time
import undetected_chromedriver as uc

print("Запускаем Chrome...")

options = uc.ChromeOptions()
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

driver = uc.Chrome(options=options)

print("Chrome запущен, открываем WB...")

driver.get("https://www.wildberries.ru/")

print("Ждём 5 секунд...")
time.sleep(5)

cookies = {}
for cookie in driver.get_cookies():
    cookies[cookie['name']] = cookie['value']

print(f"Получено cookies: {len(cookies)}")
for name, value in list(cookies.items())[:5]:
    print(f"  {name}: {value[:30]}...")

driver.quit()
print("Готово!")