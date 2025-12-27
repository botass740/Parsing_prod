# test_ozon_selenium.py
import time
import json
import re

def parse_ozon_product(product_id: int) -> dict:
    """Парсит товар Ozon через Selenium."""
    try:
        import undetected_chromedriver as uc
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        
        options = uc.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        print("Запускаю Chrome...")
        driver = uc.Chrome(options=options)
        
        try:
            url = f"https://www.ozon.ru/product/{product_id}/"
            print(f"Открываю: {url}")
            driver.get(url)
            
            # Ждём загрузку страницы
            time.sleep(5)
            
            # Пробуем найти данные в JSON внутри страницы
            # Ozon хранит данные в <script> тегах
            scripts = driver.find_elements(By.TAG_NAME, "script")
            
            page_data = None
            for script in scripts:
                content = script.get_attribute("innerHTML")
                if content and "webPrice" in content:
                    print("Найден скрипт с ценой!")
                    # Сохраняем для анализа
                    with open("ozon_script.txt", "w", encoding="utf-8") as f:
                        f.write(content)
                    break
            
            # Парсим видимые элементы
            result = {
                "product_id": product_id,
                "url": url,
            }
            
            # Название
            try:
                title_el = driver.find_element(By.CSS_SELECTOR, "h1")
                result["name"] = title_el.text.strip()
                print(f"Название: {result['name']}")
            except:
                print("Название не найдено")
            
            # Цена - ищем разными способами
            try:
                # Способ 1: через data-widget
                price_container = driver.find_element(By.CSS_SELECTOR, "[data-widget='webPrice']")
                price_text = price_container.text
                print(f"Блок цены: {price_text[:100]}")
                
                # Извлекаем числа
                prices = re.findall(r'(\d[\d\s]*)\s*₽', price_text.replace('\xa0', ' '))
                if prices:
                    result["price"] = int(prices[0].replace(' ', '').replace('\xa0', ''))
                    print(f"Цена: {result['price']}")
                    
                    if len(prices) > 1:
                        result["old_price"] = int(prices[1].replace(' ', '').replace('\xa0', ''))
                        print(f"Старая цена: {result['old_price']}")
            except Exception as e:
                print(f"Ошибка парсинга цены: {e}")
            
            # Рейтинг
            try:
                rating_el = driver.find_element(By.CSS_SELECTOR, "[data-widget='webReviewProductScore']")
                rating_text = rating_el.text
                rating_match = re.search(r'([\d,\.]+)', rating_text)
                if rating_match:
                    result["rating"] = float(rating_match.group(1).replace(',', '.'))
                    print(f"Рейтинг: {result['rating']}")
                    
                reviews_match = re.search(r'(\d+)\s*отзыв', rating_text)
                if reviews_match:
                    result["feedbacks"] = int(reviews_match.group(1))
                    print(f"Отзывов: {result['feedbacks']}")
            except Exception as e:
                print(f"Рейтинг не найден: {e}")
            
            # Картинка
            try:
                img_el = driver.find_element(By.CSS_SELECTOR, "[data-widget='webGallery'] img")
                result["image_url"] = img_el.get_attribute("src")
                print(f"Картинка: {result['image_url'][:50]}...")
            except:
                print("Картинка не найдена")
            
            # Сохраняем HTML для анализа
            with open("ozon_page.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            print("\nHTML сохранён в ozon_page.html")
            
            return result
            
        finally:
            driver.quit()
            
    except Exception as e:
        print(f"Ошибка: {e}")
        return {}


def parse_ozon_search(query: str, max_products: int = 10) -> list:
    """Парсит поиск Ozon."""
    try:
        import undetected_chromedriver as uc
        from selenium.webdriver.common.by import By
        
        options = uc.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        print("Запускаю Chrome...")
        driver = uc.Chrome(options=options)
        
        try:
            url = f"https://www.ozon.ru/search/?text={query}&from_global=true"
            print(f"Открываю поиск: {url}")
            driver.get(url)
            
            time.sleep(5)
            
            # Ищем ссылки на товары
            product_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/product/']")
            
            product_ids = set()
            for link in product_links:
                href = link.get_attribute("href")
                if href:
                    match = re.search(r'/product/[^/]*-(\d+)/', href)
                    if match:
                        product_ids.add(match.group(1))
                    else:
                        # Попробуем другой формат
                        match = re.search(r'/product/(\d+)', href)
                        if match:
                            product_ids.add(match.group(1))
            
            product_ids = list(product_ids)[:max_products]
            print(f"Найдено товаров: {len(product_ids)}")
            print(f"ID: {product_ids[:5]}...")
            
            return product_ids
            
        finally:
            driver.quit()
            
    except Exception as e:
        print(f"Ошибка: {e}")
        return []


if __name__ == "__main__":
    # Тест 1: парсинг товара
    print("=" * 50)
    print("ТЕСТ 1: Парсинг товара")
    print("=" * 50)
    
    # Возьмите product_id из URL любого товара Ozon
    # Например: https://www.ozon.ru/product/smartfon-apple-iphone-15-128gb-chernyy-1386462292/
    # product_id = 1386462292
    product = parse_ozon_product(1386462292)
    print(f"\nРезультат: {json.dumps(product, ensure_ascii=False, indent=2)}")
    
    # Тест 2: поиск
    print("\n" + "=" * 50)
    print("ТЕСТ 2: Поиск")
    print("=" * 50)
    
    ids = parse_ozon_search("смартфон", max_products=5)
    print(f"\nНайденные ID: {ids}")