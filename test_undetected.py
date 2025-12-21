# test_undetected.py
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import re

def get_wb_price(nm_id: int, driver=None) -> dict:
    """Получает цены через undetected-chromedriver"""
    
    close_driver = False
    if driver is None:
        options = uc.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        driver = uc.Chrome(options=options)
        close_driver = True
    
    result = {
        "nm_id": nm_id,
        "name": None,
        "price": None,
        "price_wallet": None,
        "old_price": None,
    }
    
    try:
        url = f"https://www.wildberries.ru/catalog/{nm_id}/detail.aspx"
        print(f"Загружаем: {url}")
        
        driver.get(url)
        
        # Ждём прохождения проверки
        print("Ждём загрузки страницы...")
        time.sleep(8)
        
        # Дополнительная проверка
        if "Проверяем" in driver.page_source:
            print("⏳ Ещё проверяет, ждём...")
            time.sleep(7)
        
        # Скриншот
        driver.save_screenshot(f"wb_uc_{nm_id}.png")
        
        # === НАЗВАНИЕ ===
        try:
            # Пробуем разные селекторы для названия
            for selector in ["h1.product-page__title", "h1", "[data-name]"]:
                try:
                    el = driver.find_element(By.CSS_SELECTOR, selector)
                    text = el.text.strip()
                    if text and len(text) > 5:
                        result["name"] = text
                        print(f"✅ Название: {text[:50]}...")
                        break
                except:
                    pass
        except:
            pass
        
        # === ЦЕНЫ ===
        # Все элементы с ценами
        price_elements = driver.find_elements(By.CSS_SELECTOR, "[class*='price']")
        
        prices_found = []
        for el in price_elements:
            try:
                text = el.text.strip()
                if "₽" in text and len(text) < 30:
                    # Извлекаем число
                    nums = re.findall(r'[\d\s\xa0]+', text)
                    if nums:
                        price = int(nums[0].replace(" ", "").replace("\xa0", "").replace("\n", ""))
                        if price > 10:
                            class_name = el.get_attribute("class") or ""
                            tag = el.tag_name
                            prices_found.append({
                                "price": price,
                                "class": class_name,
                                "tag": tag,
                                "text": text[:30]
                            })
            except:
                pass
        
        print(f"\nНайдено цен: {len(prices_found)}")
        for p in prices_found:
            print(f"  {p['price']:>6} ₽ | {p['tag']:<4} | {p['class'][:40]}")
        
        # Определяем какая цена какая
        for p in prices_found:
            cls = p["class"].lower()
            tag = p["tag"].lower()
            
            # Старая цена (зачёркнутая)
            if "old" in cls or tag == "del":
                if result["old_price"] is None:
                    result["old_price"] = p["price"]
                    
            # Цена с кошельком (обычно меньше)
            elif "wallet" in cls:
                result["price_wallet"] = p["price"]
                
            # Основная цена
            elif "final" in cls or tag == "ins":
                result["price"] = p["price"]
        
        # Если не нашли по классам — берём минимальную как цену
        if result["price"] is None and prices_found:
            # Фильтруем старые цены
            current_prices = [p["price"] for p in prices_found if "old" not in p["class"].lower() and p["tag"] != "del"]
            if current_prices:
                result["price_wallet"] = min(current_prices)
                result["price"] = max(current_prices) if len(current_prices) > 1 else min(current_prices)
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if close_driver:
            try:
                driver.quit()
            except:
                pass
    
    return result


def test_multiple(nm_ids: list):
    """Тестируем несколько товаров в одной сессии браузера"""
    
    print("="*70)
    print("ТЕСТ UNDETECTED-CHROMEDRIVER — НЕСКОЛЬКО ТОВАРОВ")
    print("="*70)
    
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    driver = uc.Chrome(options=options)
    
    results = []
    
    try:
        for nm_id in nm_ids:
            print(f"\n{'='*70}")
            print(f"📦 Товар: {nm_id}")
            print("="*70)
            
            result = get_wb_price(nm_id, driver)
            results.append(result)
            
            # Пауза между запросами
            time.sleep(2)
    
    finally:
        try:
            driver.quit()
        except:
            pass
    
    # Итоговая таблица
    print(f"\n{'='*70}")
    print("ИТОГОВАЯ ТАБЛИЦА")
    print("="*70)
    print(f"{'Артикул':<12} {'Кошелёк':>10} {'Картой':>10} {'Старая':>10}")
    print("-"*70)
    
    for r in results:
        nm = r.get('nm_id', '?')
        wallet = r.get('price_wallet') or r.get('price') or 0
        card = r.get('price') or 0
        old = r.get('old_price') or 0
        print(f"{nm:<12} {wallet:>10} {card:>10} {old:>10}")
    
    print("="*70)
    
    return results


if __name__ == "__main__":
    test_ids = [
        227648352,
        443549513,
        158173097,
        535935438,
    ]
    
    test_multiple(test_ids)