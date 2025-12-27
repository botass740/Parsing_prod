# test_ozon_api.py
import asyncio
import time
import json

import requests


def get_ozon_cookies() -> dict:
    """Получает cookies через Selenium."""
    try:
        import undetected_chromedriver as uc
        
        options = uc.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        print("Запускаю Chrome...")
        driver = uc.Chrome(options=options)
        
        try:
            print("Открываю Ozon...")
            driver.get("https://www.ozon.ru/")
            time.sleep(5)  # Ждём загрузку
            
            cookies = {}
            for cookie in driver.get_cookies():
                cookies[cookie['name']] = cookie['value']
            
            print(f"Получено cookies: {len(cookies)}")
            return cookies
            
        finally:
            driver.quit()
            
    except Exception as e:
        print(f"Ошибка: {e}")
        return {}


def test_product_api(product_id: int, cookies: dict) -> dict:
    """Тестирует API карточки товара."""
    
    # Вариант 1: через page/json
    url = f"https://www.ozon.ru/api/entrypoint-api.bx/page/json/v2?url=/product/{product_id}/"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Referer": "https://www.ozon.ru/",
    }
    
    print(f"\nЗапрос: {url}")
    
    resp = requests.get(url, headers=headers, cookies=cookies, timeout=30)
    print(f"Статус: {resp.status_code}")
    
    if resp.status_code == 200:
        data = resp.json()
        # Сохраняем для анализа
        with open("ozon_response.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("Ответ сохранён в ozon_response.json")
        return data
    else:
        print(f"Ошибка: {resp.text[:500]}")
        return {}


def test_search_api(query: str, cookies: dict) -> dict:
    """Тестирует API поиска."""
    
    url = f"https://www.ozon.ru/api/composer-api.bx/page/json/v2?url=/search/?text={query}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Referer": "https://www.ozon.ru/",
    }
    
    print(f"\nПоиск: {query}")
    
    resp = requests.get(url, headers=headers, cookies=cookies, timeout=30)
    print(f"Статус: {resp.status_code}")
    
    if resp.status_code == 200:
        data = resp.json()
        with open("ozon_search.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("Ответ сохранён в ozon_search.json")
        return data
    else:
        print(f"Ошибка: {resp.text[:500]}")
        return {}


if __name__ == "__main__":
    # 1. Получаем cookies
    cookies = get_ozon_cookies()
    
    if not cookies:
        print("Не удалось получить cookies!")
        exit(1)
    
    # 2. Тестируем API товара
    # Возьмите любой product_id с Ozon (число из URL)
    # Например: https://www.ozon.ru/product/1234567890/ -> product_id = 1234567890
    test_product_id = 1386462292  # Замените на реальный
    test_product_api(test_product_id, cookies)
    
    # 3. Тестируем поиск
    test_search_api("смартфон", cookies)
    
    print("\nГотово! Проверьте файлы ozon_response.json и ozon_search.json")