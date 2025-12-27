# bot/parsers/ozon.py

from __future__ import annotations

import asyncio
import logging
import re
import time
from datetime import datetime, timedelta
from typing import Any, Iterable

import aiohttp

log = logging.getLogger(__name__)

# ============================================================================
# Константы
# ============================================================================

COOKIES_REFRESH_HOURS = 2
CONNECT_TIMEOUT = 10
READ_TIMEOUT = 30

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Глобальный кеш cookies
_cookies_cache: dict[str, str] = {}
_cookies_updated: datetime | None = None


# ============================================================================
# Получение cookies
# ============================================================================

def _get_fresh_cookies() -> dict[str, str]:
    """Получает cookies через Selenium."""
    global _cookies_cache, _cookies_updated
    
    # Проверяем кеш
    if _cookies_updated and _cookies_cache:
        age = datetime.now() - _cookies_updated
        if age < timedelta(hours=COOKIES_REFRESH_HOURS):
            log.debug("Using cached Ozon cookies (age: %s)", age)
            return _cookies_cache
    
    log.info("Refreshing Ozon cookies via Selenium...")
    
    try:
        import undetected_chromedriver as uc
        
        options = uc.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        
        driver = uc.Chrome(options=options)
        
        try:
            driver.get("https://www.ozon.ru/")
            time.sleep(5)
            
            cookies = {}
            for cookie in driver.get_cookies():
                cookies[cookie['name']] = cookie['value']
            
            _cookies_cache = cookies
            _cookies_updated = datetime.now()
            
            log.info("Ozon cookies refreshed, count: %d", len(cookies))
            return cookies
            
        finally:
            try:
                driver.quit()
            except:
                pass
                
    except Exception as e:
        log.error("Failed to get Ozon cookies: %s", e)
        return _cookies_cache or {}


# ============================================================================
# Парсинг через Selenium
# ============================================================================

def _parse_product_selenium(product_id: int) -> dict[str, Any] | None:
    """Парсит один товар через Selenium."""
    try:
        import undetected_chromedriver as uc
        from selenium.webdriver.common.by import By
        
        options = uc.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--headless=new")  # Без окна
        
        driver = uc.Chrome(options=options)
        
        try:
            # Сначала главная для cookies
            driver.get("https://www.ozon.ru/")
            time.sleep(2)
            
            # Теперь товар
            url = f"https://www.ozon.ru/product/{product_id}/"
            driver.get(url)
            time.sleep(5)
            
            page_source = driver.page_source
            current_url = driver.current_url
            
            result = {
                "external_id": str(product_id),
                "platform": "ozon",
                "product_url": current_url,
            }
            
            # Название из h1
            try:
                h1_elements = driver.find_elements(By.TAG_NAME, "h1")
                for h1 in h1_elements:
                    text = h1.text.strip()
                    if text and len(text) > 5:
                        result["name"] = text
                        result["title"] = text
                        break
            except:
                pass
            
            # Цена из JSON в странице
            price_match = re.search(r'"price"\s*:\s*"?(\d+)"?', page_source)
            if price_match:
                result["price"] = int(price_match.group(1))
            
            # Старая цена
            original_match = re.search(r'"originalPrice"\s*:\s*"?(\d+)"?', page_source)
            if original_match:
                result["old_price"] = int(original_match.group(1))
            
            # Скидка
            if result.get("price") and result.get("old_price"):
                if result["old_price"] > result["price"]:
                    discount = (1 - result["price"] / result["old_price"]) * 100
                    result["discount_percent"] = round(discount)
            
            # Рейтинг
            rating_match = re.search(r'"reviewRating"\s*:\s*"?([\d.]+)"?', page_source)
            if rating_match:
                result["rating"] = float(rating_match.group(1))
            
            # Отзывы
            reviews_match = re.search(r'"reviewCount"\s*:\s*"?(\d+)"?', page_source)
            if reviews_match:
                result["feedbacks"] = int(reviews_match.group(1))
            
            # Картинка
            img_match = re.search(r'"images"\s*:\s*\["([^"]+)"', page_source)
            if img_match:
                result["image_url"] = img_match.group(1)
            
            return result
            
        finally:
            try:
                driver.quit()
            except:
                pass
                
    except Exception as e:
        log.error("Selenium parse error for %s: %s", product_id, e)
        return None


def _search_products_selenium(query: str, max_products: int = 100) -> list[str]:
    """Ищет товары через Selenium."""
    try:
        import undetected_chromedriver as uc
        from selenium.webdriver.common.by import By
        
        options = uc.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--headless=new")
        
        driver = uc.Chrome(options=options)
        
        try:
            url = f"https://www.ozon.ru/search/?text={query}&from_global=true"
            driver.get(url)
            time.sleep(5)
            
            # Ищем ссылки на товары
            product_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/product/']")
            
            product_ids = set()
            for link in product_links:
                href = link.get_attribute("href")
                if href:
                    # Формат: /product/name-123456789/
                    match = re.search(r'/product/[^/]*-(\d+)/', href)
                    if match:
                        product_ids.add(match.group(1))
                    else:
                        match = re.search(r'/product/(\d+)', href)
                        if match:
                            product_ids.add(match.group(1))
            
            result = list(product_ids)[:max_products]
            log.info("Ozon search '%s': found %d products", query, len(result))
            return result
            
        finally:
            try:
                driver.quit()
            except:
                pass
                
    except Exception as e:
        log.error("Ozon search error: %s", e)
        return []


# ============================================================================
# Основной класс
# ============================================================================

class OzonParser:
    """
    Парсер Ozon через Selenium.
    
    Ozon имеет серьёзную защиту от ботов, поэтому используем
    undetected-chromedriver для каждого запроса.
    """
    
    def __init__(self, product_ids: Iterable[int] | None = None) -> None:
        if product_ids:
            self._product_ids = [str(i) for i in product_ids]
        else:
            self._product_ids = []
    
    async def fetch_products(self) -> Iterable[Any]:
        """Возвращает список product_id для парсинга."""
        if not self._product_ids:
            log.warning("OzonParser: product_ids list is empty")
        return list(self._product_ids)
    
    async def parse_product(self, raw: Any) -> dict[str, Any]:
        """Парсит один товар."""
        product_id = int(raw) if not isinstance(raw, int) else raw
        
        # Запускаем синхронный Selenium в отдельном потоке
        result = await asyncio.to_thread(_parse_product_selenium, product_id)
        
        if result:
            return result
        
        # Fallback если не спарсилось
        return {
            "external_id": str(product_id),
            "platform": "ozon",
            "name": f"Товар {product_id}",
            "price": None,
            "product_url": f"https://www.ozon.ru/product/{product_id}/",
        }
    
    async def parse_products_batch(self, product_ids: list[int]) -> list[dict[str, Any]]:
        """
        Парсит несколько товаров.
        
        Внимание: Ozon не поддерживает batch API как WB,
        поэтому парсим последовательно с паузами.
        """
        results = []
        
        for i, pid in enumerate(product_ids):
            log.debug("Parsing Ozon product %d/%d: %s", i + 1, len(product_ids), pid)
            
            try:
                result = await self.parse_product(pid)
                if result.get("price"):
                    results.append(result)
            except Exception as e:
                log.warning("Failed to parse Ozon product %s: %s", pid, e)
            
            # Пауза между запросами
            if i < len(product_ids) - 1:
                await asyncio.sleep(2)
        
        return results
    
    async def search_products(self, query: str, max_products: int = 100) -> list[str]:
        """Поиск товаров по запросу."""
        return await asyncio.to_thread(_search_products_selenium, query, max_products)


# ============================================================================
# Вспомогательные функции для построения URL картинок
# ============================================================================

def build_ozon_image_url(product_id: int) -> str:
    """Строит URL картинки (заглушка, т.к. URL берём из парсинга)."""
    return f"https://ir.ozon.ru/s3/multimedia-0/c1000/wc1000/{product_id}.jpg"