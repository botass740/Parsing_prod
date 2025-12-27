# test_ozon_v2.py
import time
import json
import re


def parse_ozon_product(product_id: int) -> dict:
    """Парсит товар Ozon через Selenium."""
    try:
        import undetected_chromedriver as uc
        from selenium.webdriver.common.by import By
        
        options = uc.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        
        print("Запускаю Chrome...")
        driver = uc.Chrome(options=options)
        
        try:
            # Сначала заходим на главную
            print("Открываю главную Ozon...")
            driver.get("https://www.ozon.ru/")
            time.sleep(3)
            
            # Теперь на товар
            url = f"https://www.ozon.ru/product/{product_id}/"
            print(f"Открываю товар: {url}")
            driver.get(url)
            
            # Ждём дольше
            print("Жду загрузку (10 сек)...")
            time.sleep(10)
            
            # Проверяем title
            title = driver.title
            print(f"Title страницы: {title}")
            
            # Проверяем URL (может быть редирект)
            current_url = driver.current_url
            print(f"Текущий URL: {current_url}")
            
            result = {
                "product_id": product_id,
                "url": current_url,
                "page_title": title,
            }
            
            # Ищем JSON данные в странице
            page_source = driver.page_source
            
            # Ozon хранит данные в window.__NUXT__  или в script с type="application/json"
            if '"webPrice"' in page_source:
                print("Найдены данные webPrice в странице!")
                
                # Ищем цену через регулярку
                price_match = re.search(r'"price"\s*:\s*"?(\d+)"?', page_source)
                if price_match:
                    result["price"] = int(price_match.group(1))
                    print(f"Цена: {result['price']}")
            
            # Пробуем найти элементы на странице
            print("\nИщу элементы...")
            
            # Все тексты с ценой (₽)
            body_text = driver.find_element(By.TAG_NAME, "body").text
            prices = re.findall(r'(\d[\d\s]*)\s*₽', body_text.replace('\xa0', ' '))
            if prices:
                print(f"Найденные цены: {prices[:5]}")
                # Первая цена обычно актуальная
                result["price"] = int(prices[0].replace(' ', ''))
            
            # Название из h1
            try:
                h1_elements = driver.find_elements(By.TAG_NAME, "h1")
                for h1 in h1_elements:
                    text = h1.text.strip()
                    if text and len(text) > 5:
                        result["name"] = text
                        print(f"Название: {text[:50]}...")
                        break
            except:
                pass
            
            # Сохраняем HTML
            with open("ozon_page2.html", "w", encoding="utf-8") as f:
                f.write(page_source)
            
            return result
            
        finally:
            try:
                driver.quit()
            except:
                pass
            
    except Exception as e:
        print(f"Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return {}


if __name__ == "__main__":
    # Используем ID из поиска (который работал)
    test_ids = [1998926903, 1998926880, 2657126120]
    
    for pid in test_ids:
        print("\n" + "=" * 50)
        print(f"Тестирую товар: {pid}")
        print("=" * 50)
        
        result = parse_ozon_product(pid)
        print(f"\nРезультат: {json.dumps(result, ensure_ascii=False, indent=2)}")
        
        if result.get("price"):
            print("\n✅ Успех! Цена найдена.")
            break
        else:
            print("\n❌ Цена не найдена, пробую следующий...")
        
        time.sleep(2)