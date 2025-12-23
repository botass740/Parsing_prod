# test_spp.py

import requests
import time
import undetected_chromedriver as uc

def check_spp():
    nm_id = 494949159
    
    print("Получаем cookies...")
    
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    driver = uc.Chrome(options=options)
    driver.get("https://www.wildberries.ru/")
    time.sleep(5)
    
    cookies = {}
    for cookie in driver.get_cookies():
        cookies[cookie['name']] = cookie['value']
    driver.quit()
    
    headers = {
        "Accept": "*/*",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.wildberries.ru/",
    }
    
    # Тестируем разные spp
    for spp in [0, 10, 20, 30]:
        url = f"https://www.wildberries.ru/__internal/u-card/cards/v4/detail?appType=1&curr=rub&dest=12354108&spp={spp}&lang=ru&nm={nm_id}"
        
        resp = requests.get(url, headers=headers, cookies=cookies, timeout=30)
        
        if resp.status_code == 200:
            data = resp.json()
            products = data.get("data", {}).get("products", []) or data.get("products", [])
            
            if products:
                p = products[0]
                sizes = p.get("sizes", [])
                if sizes:
                    price = sizes[0].get("price", {}).get("product", 0) / 100
                    basic = sizes[0].get("price", {}).get("basic", 0) / 100
                    print(f"spp={spp}: price={price}₽, basic={basic}₽")


if __name__ == "__main__":
    check_spp()