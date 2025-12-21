from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time

def get_wb_price(nm_id: int) -> dict:
    """Получает цены товара через Selenium"""
    
    options = Options()
    options.add_argument("--headless")  # Без окна браузера
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # Прокси (опционально)
    # options.add_argument("--proxy-server=http://23fmwsTtvu:Wx8hCmKzI5@45.132.252.132:38267")
    
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    
    result = {
        "nm_id": nm_id,
        "price": None,
        "old_price": None,
        "wallet_price": None,
    }
    
    try:
        url = f"https://www.wildberries.ru/catalog/{nm_id}/detail.aspx"
        print(f"Загружаем: {url}")
        
        driver.get(url)
        
        # Ждём загрузки цены (до 15 сек)
        wait = WebDriverWait(driver, 15)
        
        # Ищем элемент с ценой
        # WB использует разные классы, пробуем несколько вариантов
        price_selectors = [
            ".price-block__final-price",
            ".price-block__wallet-price", 
            "[class*='price']",
            ".product-page__price-block ins",
        ]
        
        for selector in price_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for el in elements:
                    text = el.text.strip()
                    if text and "₽" in text:
                        # Извлекаем число
                        import re
                        nums = re.findall(r'[\d\s]+', text)
                        if nums:
                            price = int(nums[0].replace(" ", ""))
                            print(f"  Найдена цена ({selector}): {price} ₽")
                            
                            if result["price"] is None:
                                result["price"] = price
            except:
                pass
        
        # Ищем старую цену
        old_price_selectors = [
            ".price-block__old-price",
            "del[class*='price']",
            ".product-page__price-block del",
        ]
        
        for selector in old_price_selectors:
            try:
                el = driver.find_element(By.CSS_SELECTOR, selector)
                text = el.text.strip()
                if text:
                    import re
                    nums = re.findall(r'[\d\s]+', text)
                    if nums:
                        result["old_price"] = int(nums[0].replace(" ", ""))
                        print(f"  Старая цена: {result['old_price']} ₽")
                        break
            except:
                pass
        
        # Скриншот для отладки
        driver.save_screenshot(f"wb_{nm_id}.png")
        print(f"  Скриншот сохранён: wb_{nm_id}.png")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        
    finally:
        driver.quit()
    
    return result


if __name__ == "__main__":
    print("="*60)
    print("ТЕСТ SELENIUM ДЛЯ WB")
    print("="*60)
    
    test_ids = [227648352, 443549513]
    
    for nm_id in test_ids:
        print(f"\n{'='*60}")
        print(f"Товар: {nm_id}")
        print("="*60)
        
        result = get_wb_price(nm_id)
        
        print(f"\nРезультат:")
        print(f"  Цена: {result['price']} ₽")
        print(f"  Старая: {result['old_price']} ₽")