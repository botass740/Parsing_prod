from __future__ import annotations

import asyncio
import logging
import os
import random
import re
import time
from typing import Any, Iterable

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from bot.parsers.base import BaseParser

log = logging.getLogger(__name__)

# ============================================================================
# Константы
# ============================================================================

WB_PROXY_URL = os.getenv("WB_PROXY_URL", "").strip()
PROXIES: dict[str, str] | None = None
if WB_PROXY_URL:
    PROXIES = {"http": WB_PROXY_URL, "https": WB_PROXY_URL}

CONNECT_TIMEOUT = 10
READ_TIMEOUT = 30

MIN_REQUEST_DELAY = 0.3
MAX_REQUEST_DELAY = 0.8

# СПП для расчёта цены без скидки постоянного покупателя
# price-history содержит цену с максимальным СПП (~27%)
# Для диапазона: price_min = из history, price_max = price_min / (1 - SPP)
DEFAULT_SPP = 0.22  # 22% — среднее значение

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]

_last_request_time: float = 0


def _get_headers() -> dict[str, str]:
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "ru-RU,ru;q=0.9",
        "Referer": "https://www.wildberries.ru/",
        "Origin": "https://www.wildberries.ru",
    }


def _rate_limit() -> None:
    global _last_request_time
    elapsed = time.time() - _last_request_time
    delay = random.uniform(MIN_REQUEST_DELAY, MAX_REQUEST_DELAY)
    if elapsed < delay:
        time.sleep(delay - elapsed)
    _last_request_time = time.time()


def _create_session() -> requests.Session:
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1.0,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    if PROXIES:
        session.proxies = PROXIES
    return session


_session: requests.Session | None = None


def _get_session() -> requests.Session:
    global _session
    if _session is None:
        _session = _create_session()
    return _session


# ============================================================================
# Basket-хост
# ============================================================================

def _get_basket_number(vol: int) -> int:
    if vol <= 143: return 1
    elif vol <= 287: return 2
    elif vol <= 431: return 3
    elif vol <= 719: return 4
    elif vol <= 1007: return 5
    elif vol <= 1061: return 6
    elif vol <= 1115: return 7
    elif vol <= 1169: return 8
    elif vol <= 1313: return 9
    elif vol <= 1601: return 10
    elif vol <= 1655: return 11
    elif vol <= 1919: return 12
    elif vol <= 2045: return 13
    elif vol <= 2189: return 14
    elif vol <= 2405: return 15
    elif vol <= 2621: return 16
    elif vol <= 2837: return 17
    elif vol <= 3053: return 18
    elif vol <= 3269: return 19
    elif vol <= 3485: return 20
    elif vol <= 3701: return 21
    elif vol <= 3917: return 22
    elif vol <= 4133: return 23
    elif vol <= 4349: return 24
    elif vol <= 4565: return 25
    elif vol <= 4781: return 26
    elif vol <= 4997: return 27
    elif vol <= 5213: return 28
    elif vol <= 5429: return 29
    elif vol <= 5645: return 30
    elif vol <= 5861: return 31
    else: return 32


def _get_basket_host(nm_id: int) -> str:
    vol = nm_id // 100000
    basket = _get_basket_number(vol)
    return f"https://basket-{basket:02d}.wbbasket.ru"


def _get_vol_part(nm_id: int) -> tuple[int, int]:
    return nm_id // 100000, nm_id // 1000


# ============================================================================
# API-функции
# ============================================================================

def _fetch_card_json(nm_id: int) -> dict[str, Any] | None:
    """Получает описание товара из card.json."""
    vol, part = _get_vol_part(nm_id)
    basket_host = _get_basket_host(nm_id)
    url = f"{basket_host}/vol{vol}/part{part}/{nm_id}/info/ru/card.json"
    
    session = _get_session()
    _rate_limit()
    
    try:
        resp = session.get(url, headers=_get_headers(), timeout=(CONNECT_TIMEOUT, READ_TIMEOUT))
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        log.warning(f"WB card.json error for {nm_id}: {e}")
    
    return None


def _fetch_price_history(nm_id: int) -> dict[str, Any] | None:
    """
    Получает историю цен.
    
    price-history.json содержит цену С УЧЁТОМ максимального СПП.
    
    Возвращает:
    - price_min: минимальная цена (с СПП) — "от"
    - price_max: максимальная цена (без СПП) — "до"  
    - old_price: старая/зачёркнутая цена
    - discount: скидка в %
    """
    vol, part = _get_vol_part(nm_id)
    basket_host = _get_basket_host(nm_id)
    url = f"{basket_host}/vol{vol}/part{part}/{nm_id}/info/price-history.json"
    
    session = _get_session()
    _rate_limit()
    
    try:
        resp = session.get(url, headers=_get_headers(), timeout=(CONNECT_TIMEOUT, READ_TIMEOUT))
        if resp.status_code == 200:
            data = resp.json()
            
            if isinstance(data, list) and data:
                # Последняя запись = текущая цена с максимальным СПП
                latest = data[-1]
                price_with_spp_raw = latest.get("price", {}).get("RUB", 0)
                price_min = price_with_spp_raw / 100.0 if price_with_spp_raw else None
                
                # Цена без СПП (максимальная для покупателя)
                price_max = None
                if price_min:
                    price_max = round(price_min / (1 - DEFAULT_SPP), 0)
                
                # Максимальная цена из истории ≈ старая цена
                all_prices = [
                    item.get("price", {}).get("RUB", 0) / 100.0
                    for item in data
                    if item.get("price", {}).get("RUB")
                ]
                
                # Старая цена — максимум из истории, но увеличиваем для реалистичности
                # (WB часто показывает "было" выше чем максимум в истории)
                max_history = max(all_prices) if all_prices else None
                old_price = None
                if max_history and price_max:
                    # Старая цена обычно на 30-50% выше текущей максимальной
                    old_price = round(max(max_history, price_max * 1.3), 0)
                
                # Скидка от старой цены
                discount = None
                if price_max and old_price and old_price > price_max:
                    discount = round((1 - price_max / old_price) * 100, 0)
                
                return {
                    "price_min": round(price_min, 0) if price_min else None,
                    "price_max": price_max,
                    "old_price": old_price,
                    "discount": discount,
                }
                
    except Exception as e:
        log.warning(f"WB price-history error for {nm_id}: {e}")
    
    return None


def _fetch_rating(nm_id: int) -> dict[str, Any]:
    """Получает рейтинг и количество отзывов."""
    url = f"https://feedbacks1.wb.ru/feedbacks/v1/{nm_id}"
    
    session = _get_session()
    _rate_limit()
    
    try:
        resp = session.get(url, headers=_get_headers(), timeout=(CONNECT_TIMEOUT, READ_TIMEOUT))
        if resp.status_code == 200:
            data = resp.json()
            
            valuation = data.get("valuation")
            feedback_count = data.get("feedbackCount", 0)
            
            if not valuation and feedback_count > 0:
                valuation_sum = data.get("valuationSum", 0)
                valuation = round(valuation_sum / feedback_count, 1) if valuation_sum else None
            
            return {
                "rating": float(valuation) if valuation else None,
                "feedbacks": feedback_count,
            }
    except Exception as e:
        log.warning(f"WB rating error for {nm_id}: {e}")
    
    return {"rating": None, "feedbacks": 0}


# ============================================================================
# Основной класс
# ============================================================================

class WildberriesParser(BaseParser):
    """
    Парсер Wildberries.
    
    Источники данных:
    1. basket-*.wbbasket.ru/info/ru/card.json — описание
    2. basket-*.wbbasket.ru/info/price-history.json — цены
    3. product-order-qnt.wildberries.ru — остатки
    4. feedbacks1.wb.ru — рейтинг
    """

    def __init__(self, product_ids: Iterable[int] | None = None) -> None:
        base_ids = [169684889]
        if product_ids:
            self._product_ids = [int(i) for i in product_ids]
        else:
            self._product_ids = base_ids

    async def fetch_products(self) -> Iterable[Any]:
        if not self._product_ids:
            log.warning("WildberriesParser: product_ids list is empty")
        return list(self._product_ids)

    async def parse_product(self, raw: Any) -> dict[str, Any]:
        nm_id = _normalize_nm(raw)
        external_id = str(nm_id)
        
        log.debug(f"WB: Parsing product {nm_id}")

        # 1. Описание
        name = ""
        brand = None
        
        try:
            card = await asyncio.to_thread(_fetch_card_json, nm_id)
            if card:
                name = card.get("imt_name") or card.get("name") or ""
                selling = card.get("selling") or {}
                brand = selling.get("brand_name") or card.get("brand")
        except Exception as e:
            log.warning(f"WB card error for {nm_id}: {e}")

        # 2. Цены (диапазон)
        price_min: float | None = None
        price_max: float | None = None
        old_price: float | None = None
        discount: float | None = None
        
        try:
            price_data = await asyncio.to_thread(_fetch_price_history, nm_id)
            if price_data:
                price_min = price_data.get("price_min")
                price_max = price_data.get("price_max")
                old_price = price_data.get("old_price")
                discount = price_data.get("discount")
        except Exception as e:
            log.warning(f"WB price error for {nm_id}: {e}")

        # 3. Остатки — не используем, данные ненадёжные
        stock = None

        # 4. Рейтинг
        rating: float | None = None
        feedbacks = 0
        try:
            rating_data = await asyncio.to_thread(_fetch_rating, nm_id)
            rating = rating_data.get("rating")
            feedbacks = rating_data.get("feedbacks", 0)
        except Exception as e:
            log.warning(f"WB rating error for {nm_id}: {e}")

        # Имя
        if brand and name:
            full_name = f"{brand} {name}".strip()
        elif brand:
            full_name = brand
        elif name:
            full_name = name
        else:
            full_name = f"Товар {external_id}"

        product_url = f"https://www.wildberries.ru/catalog/{external_id}/detail.aspx"
        image_url = _build_image_url(nm_id)

        result = {
            "external_id": external_id,
            "platform": "wb",
            "name": full_name,
            "title": full_name,
            "brand": brand,
            "price": price_min,
            "price_min": price_min,
            "price_max": price_max,
            "old_price": old_price,
            "discount_percent": discount,
            "stock": None,  # Не используем — данные ненадёжные
            "rating": rating,
            "feedbacks": feedbacks,
            "product_url": product_url,
            "image_url": image_url,
        }
        
        log.info(
            f"WB: Parsed {nm_id}: "
            f"price={price_min}-{price_max}, old={old_price}, "
            f"discount={discount}%, rating={rating}"
        )
        
        return result


# ============================================================================
# Вспомогательные
# ============================================================================

def _normalize_nm(raw: Any) -> int:
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str):
        s = raw.strip()
        m = re.search(r"/(\d+)(?:/|$)", s)
        if m:
            return int(m.group(1))
        m = re.search(r"nm=(\d+)", s)
        if m:
            return int(m.group(1))
        return int(s)
    if isinstance(raw, dict):
        v = raw.get("external_id") or raw.get("id") or raw.get("nm") or raw.get("nm_id")
        if v is not None:
            return int(v)
    raise TypeError(f"Cannot normalize nm_id from {type(raw)}: {raw}")


def _build_image_url(nm_id: int) -> str:
    vol, part = _get_vol_part(nm_id)
    basket_host = _get_basket_host(nm_id)
    return f"{basket_host}/vol{vol}/part{part}/{nm_id}/images/big/1.webp"