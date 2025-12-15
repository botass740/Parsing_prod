from __future__ import annotations

import asyncio
import logging
import os
import re
from typing import Any, Iterable

import requests
from requests.auth import HTTPProxyAuth

from bot.parsers.base import BaseParser

log = logging.getLogger(__name__)

BASKET_HOST = "https://basket-12.wbbasket.ru"
BASKET_HOST_TEMPLATE = "https://basket-{n}.wbbasket.ru"
SEARCH_URL = "https://search.wb.ru/exactmatch/ru/common/v4/search"

WB_PROXY_URL = os.getenv("WB_PROXY_URL", "").strip()
PROXIES: dict[str, str] | None = None

if WB_PROXY_URL:
    PROXIES = {
        "http": WB_PROXY_URL,
        "https": WB_PROXY_URL,
    }


class WildberriesParser(BaseParser):
    """
    Парсер карточек WB через два JSON-источника:
    1) card.json через basket-*.wbbasket.ru – метаинформация о товаре
    2) search.wb.ru – цены, скидки, остатки, рейтинг

    Пока работает по одному тестовому товару:
    - 169684889
    """

    def __init__(self, product_ids: Iterable[int] | None = None) -> None:
        base_ids = [169684889]  # базовый тестовый id, если список не передан
        if product_ids:
            self._product_ids = [str(i) for i in product_ids]
        else:
            self._product_ids = [str(i) for i in base_ids]

    async def fetch_products(self) -> Iterable[Any]:
        if not self._product_ids:
            log.warning("WildberriesParser: product_ids list is empty")
        return list(self._product_ids)

    async def parse_product(self, raw: Any) -> dict[str, Any]:
        nm = _normalize_nm(raw)

        # 1) card.json – описание
        try:
            card = await asyncio.to_thread(_fetch_card_json, nm)
        except requests.Timeout as e:
            raise TimeoutError(f"Wildberries card request timed out: nm={nm}") from e
        except requests.RequestException as e:
            raise ConnectionError(f"Wildberries card request failed: nm={nm}") from e
        except Exception:
            log.exception("Unexpected error while fetching WB card: nm=%s", nm)
            raise

        product_meta = _extract_product_from_card(card, nm)

        # name = imt_name; бренд – из selling.brand_name
        name = product_meta.get("imt_name") or product_meta.get("name") or ""
        selling = product_meta.get("selling") or {}
        brand = selling.get("brand_name") or product_meta.get("brand")

        if brand:
            full_name = f"{brand} {name}".strip()
        else:
            full_name = name

        # external_id = артикул WB
        external_id = str(product_meta.get("nm_id") or nm)

        # Значения по умолчанию (если не удастся получить цены)
        price: float | None = None
        old_price: float | None = None
        discount: float | None = None
        rating: float | None = None
        stock: int = 0

        # 2) search.wb.ru – цены/остатки/рейтинг
        try:
            price_info = await asyncio.to_thread(_fetch_price_info, external_id)
        except requests.HTTPError as e:
            log.error("WB price request HTTP error for nm=%s: %s", external_id, e)
            price_info = None
        except requests.RequestException as e:
            log.error("WB price request failed for nm=%s: %s", external_id, e)
            price_info = None
        except Exception:
            log.exception("Unexpected error while fetching WB price info: nm=%s", external_id)
            price_info = None

        if price_info:
            price_u = price_info.get("salePriceU") or price_info.get("priceU")
            old_price_u = price_info.get("priceU")
            price = _from_wb_price(price_u)
            old_price = _from_wb_price(old_price_u)

            if price is not None and old_price is not None and old_price > 0:
                discount = round((1 - price / old_price) * 100, 2)

            r = price_info.get("rating") or price_info.get("reviewRating")
            try:
                rating = float(r) if r is not None else None
            except (TypeError, ValueError):
                rating = None

            stock = _calc_stock_from_sizes(price_info.get("sizes") or [])

        product_url = f"https://www.wildberries.ru/catalog/{external_id}/detail.aspx"
        image_url = _build_image_url(external_id, product_meta)

        return {
            "external_id": external_id,
            "name": full_name or name or external_id,
            "title": full_name or name or external_id,
            "price": price,
            "old_price": old_price,
            "discount_percent": discount,
            "stock": stock,
            "rating": rating,
            "product_url": product_url,
            "image_url": image_url,
        }


def _normalize_nm(raw: Any) -> str:
    if isinstance(raw, int):
        return str(raw)
    if isinstance(raw, str):
        s = raw.strip()
        m = re.search(r"/(\d+)(?:/|$)", s)
        if m:
            return m.group(1)
        m = re.search(r"nm=(\d+)", s)
        if m:
            return m.group(1)
        return s
    if isinstance(raw, dict):
        v = raw.get("external_id") or raw.get("id") or raw.get("nm") or raw.get("nm_id")
        if v is not None:
            return str(v)
    raise TypeError("Wildberries nm id must be int, str or dict with id/external_id/nm")


def _fetch_card_json(nm: str) -> dict[str, Any]:
    """Запрос описания товара (card.json) с basket-*.wbbasket.ru"""
    nm_int = int(nm)
    vol = nm_int // 100000
    part = nm_int // 1000

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.wildberries.ru/",
    }

    base_candidates = [12, 25, 29]
    candidates: list[int] = []
    for n in base_candidates + list(range(1, 33)):
        if n not in candidates:
            candidates.append(n)

    last_status: int | None = None
    for n in candidates:
        host = f"https://basket-{n}.wbbasket.ru"
        url = f"{host}/vol{vol}/part{part}/{nm_int}/info/ru/card.json"

        resp = requests.get(url, headers=headers, timeout=(5, 20))
        if resp.status_code == 200:
            return resp.json()

        if resp.status_code in (403, 404):
            last_status = resp.status_code
            continue

        log.error("WB card request failed: %s %s", resp.status_code, resp.text[:200])
        resp.raise_for_status()

    raise ValueError(f"WB card.json not found for nm={nm_int} (last_status={last_status})")


def _basket_host(vol: int) -> str:
    # WB uses multiple basket hosts (basket-1..basket-15). Exact mapping may vary;
    # using a stable modulo-based distribution is sufficient for correct URL formation.
    n = (vol % 15) + 1
    return BASKET_HOST_TEMPLATE.format(n=n)


def _fetch_price_info(nm: str) -> dict[str, Any] | None:
    """
    Получаем цену/остатки/рейтинг из поискового API WB.

    Пример запроса:
    https://search.wb.ru/exactmatch/ru/common/v4/search?appType=1&curr=rub&dest=-1257786&page=1&query=169684889&resultset=catalog&sort=popular&spp=0
    """
    nm_str = str(nm)

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.wildberries.ru/",
    }

    params = {
        "TestGroup": "no_test",
        "TestID": "no_test",
        "appType": 1,
        "curr": "rub",
        "dest": -1257786,
        "page": 1,
        "query": nm_str,
        "resultset": "catalog",
        "sort": "popular",
        "spp": 0,
    }

    resp = requests.get(
    SEARCH_URL,
    headers=headers,
    params=params,
    timeout=(5, 20),
    proxies=PROXIES,  # только proxies, без auth
)
    if resp.status_code != 200:
        log.error("WB price request failed: %s %s", resp.status_code, resp.text[:200])
        resp.raise_for_status()

    data = resp.json()
    products = (data.get("data") or {}).get("products") or []

    for p in products:
        pid = p.get("id") or p.get("nmId") or p.get("nm_id")
        if pid is not None and str(pid) == nm_str:
            return p

    return None


def _extract_product_from_card(card: Any, nm: str) -> dict[str, Any]:
    if not isinstance(card, dict):
        raise ValueError(f"Unexpected WB card type for nm={nm}: {type(card)}")

    # Конкретно твой JSON: imt_name, nm_id, описание и т.д.
    if "imt_name" in card and "nm_id" in card:
        return card

    data = card.get("data") or {}
    products = data.get("products")
    if isinstance(products, list) and products:
        prod = products[0]
        if isinstance(prod, dict):
            return prod

    products = card.get("products")
    if isinstance(products, list) and products:
        prod = products[0]
        if isinstance(prod, dict):
            return prod

    if isinstance(data, dict) and ("name" in data or "priceU" in data or "salePriceU" in data):
        return data

    if "name" in card or "priceU" in card or "salePriceU" in card:
        return card

    raise ValueError(f"Unexpected WB card format for nm={nm}: keys={list(card.keys())}")


def _from_wb_price(value: Any) -> float | None:
    try:
        if value is None:
            return None
        v = int(value)
        return v / 100.0
    except (TypeError, ValueError):
        return None


def _calc_stock_from_sizes(sizes: list[dict[str, Any]]) -> int:
    total = 0
    for size in sizes:
        for st in size.get("stocks") or []:
            qty = st.get("qty")
            if isinstance(qty, int):
                total += qty
    return total


def _calc_stock(product: dict[str, Any]) -> int:
    total = 0
    sizes = product.get("sizes") or []
    for size in sizes:
        for stock in size.get("stocks") or []:
            qty = stock.get("qty")
            if isinstance(qty, int):
                total += qty
    return total


def _build_image_url(external_id: str, product: dict[str, Any]) -> str | None:
    try:
        nm = int(product.get("nm_id") or external_id)
    except (TypeError, ValueError):
        nm = None

    if nm is None:
        return None

    return f"https://images.wbstatic.net/big/new/{nm}.jpg"