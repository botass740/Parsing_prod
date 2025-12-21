import requests
import time
import undetected_chromedriver as uc

def get_cookies():
    """Получаем cookies через браузер."""
    print("Получаем cookies...")
    
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    driver = uc.Chrome(options=options)
    
    try:
        driver.get("https://www.wildberries.ru/catalog/elektronika/smartfony-i-telefony/vse-smartfony")
        time.sleep(7)
        
        cookies = {}
        for cookie in driver.get_cookies():
            cookies[cookie['name']] = cookie['value']
        
        print(f"✅ Cookies: {len(cookies)}")
        return cookies
        
    finally:
        try:
            driver.quit()
        except:
            pass


def test_catalog_search(cookies: dict):
    """Тестируем внутренний API каталога."""
    
    headers = {
        "Accept": "*/*",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.wildberries.ru/catalog/elektronika/smartfony-i-telefony/vse-smartfony",
        "x-requested-with": "XMLHttpRequest",
    }
    
    params = {
        "ab_testing": "false",
        "appType": "1",
        "curr": "rub",
        "dest": "-3827418",
        "lang": "ru",
        "page": "1",
        "query": "смартфон",
        "resultset": "catalog",
        "sort": "popular",
        "spp": "30",
    }
    
    url = "https://www.wildberries.ru/__internal/search/exactmatch/ru/common/v18/search"
    
    print("\n" + "="*70)
    print("ТЕСТ ВНУТРЕННЕГО API КАТАЛОГА")
    print("="*70)
    
    try:
        r = requests.get(url, params=params, headers=headers, cookies=cookies, timeout=15)
        
        print(f"Статус: {r.status_code}")
        
        if r.status_code == 200:
            data = r.json()
            
            print(f"Ключи ответа: {list(data.keys())}")
            print(f"Total: {data.get('total')}")
            
            # Товары в корне!
            products = data.get("products", [])
            
            if products:
                print(f"✅ Товаров на странице: {len(products)}")
                
                print("\nПримеры товаров:")
                for p in products[:5]:
                    nm_id = p.get("id")
                    name = p.get("name", "")[:40]
                    brand = p.get("brand", "")
                    
                    sizes = p.get("sizes", [])
                    if sizes:
                        price_info = sizes[0].get("price", {})
                        price = price_info.get("product", 0) / 100
                    else:
                        price = 0
                    
                    print(f"  {nm_id}: {price}₽ — {brand} / {name}...")
                
                all_ids = [p.get("id") for p in products if p.get("id")]
                print(f"\nАртикулов: {len(all_ids)}")
                
                return all_ids
            else:
                print("⚠️ products пустой")
                # Покажем структуру
                import json
                print(f"Ответ: {json.dumps(data, ensure_ascii=False)[:500]}")
                
        else:
            print(f"❌ Ошибка {r.status_code}")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    
    return []


def test_pagination(cookies: dict, query: str = "смартфон", max_pages: int = 3):
    """Тест пагинации."""
    
    headers = {
        "Accept": "*/*",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.wildberries.ru/",
        "x-requested-with": "XMLHttpRequest",
    }
    
    url = "https://www.wildberries.ru/__internal/search/exactmatch/ru/common/v18/search"
    
    all_ids = []
    
    print("\n" + "="*70)
    print(f"ПАГИНАЦИЯ: '{query}' (до {max_pages} страниц)")
    print("="*70)
    
    for page in range(1, max_pages + 1):
        params = {
            "ab_testing": "false",
            "appType": "1",
            "curr": "rub",
            "dest": "-3827418",
            "lang": "ru",
            "page": str(page),
            "query": query,
            "resultset": "catalog",
            "sort": "popular",
            "spp": "30",
        }
        
        try:
            r = requests.get(url, params=params, headers=headers, cookies=cookies, timeout=15)
            
            if r.status_code == 200:
                data = r.json()
                products = data.get("products", [])
                
                if products:
                    page_ids = [p.get("id") for p in products if p.get("id")]
                    all_ids.extend(page_ids)
                    print(f"  Страница {page}: {len(page_ids)} товаров (всего: {len(all_ids)})")
                else:
                    print(f"  Страница {page}: пусто")
                    break
            else:
                print(f"  Страница {page}: ошибка {r.status_code}")
                break
                
        except Exception as e:
            print(f"  Страница {page}: ошибка {e}")
            break
        
        time.sleep(0.5)
    
    print(f"\n✅ Итого собрано: {len(all_ids)} артикулов")
    return all_ids


if __name__ == "__main__":
    cookies = get_cookies()
    
    if cookies:
        ids = test_catalog_search(cookies)
        
        if ids:
            all_ids = test_pagination(cookies, "смартфон", max_pages=5)
            print(f"\nПервые 20 артикулов: {all_ids[:20]}")
    
    print("\n" + "="*70)
    print("ГОТОВО")
    print("="*70)