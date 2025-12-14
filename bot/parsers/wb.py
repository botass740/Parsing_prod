from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass
from typing import Any, Iterable

import requests
from bs4 import BeautifulSoup
from requests import Response

from bot.parsers.base import BaseParser


class WildberriesParser(BaseParser):
    async def fetch_products(self) -> Iterable[Any]:
        # TODO: implement fetching product list from Wildberries
        return []

    async def parse_product(self, raw: Any) -> dict[str, Any]:
        url = _normalize_product_url(raw)
        external_id = _extract_external_id(url)

        try:
            html = await asyncio.to_thread(_fetch_html, url)
        except requests.Timeout as e:
            raise TimeoutError(f"Wildberries request timed out: {url}") from e
        except requests.RequestException as e:
            raise ConnectionError(f"Wildberries request failed: {url}") from e

        soup = BeautifulSoup(html, "lxml")

        data = _parse_from_json_ld(soup)
        if data.name is None:
            data.name = _first_text(soup, ["h1", "h1.product-page__title"])

        if data.image_url is None:
            meta_image = soup.select_one('meta[property="og:image"]')
            if meta_image and meta_image.get("content"):
                data.image_url = str(meta_image.get("content"))

        if data.rating is None:
            rating_text = _first_text(soup, [".product-page__rating", ".user-opinion__rating"])
            data.rating = _parse_float(rating_text)

        if data.price is None:
            price_text = _first_text(soup, [".price-block__final-price", ".price-block__price"])
            data.price = _parse_price(price_text)

        if data.old_price is None:
            old_price_text = _first_text(soup, [".price-block__old-price", ".price-block__old"])
            data.old_price = _parse_price(old_price_text)

        if data.discount_percent is None:
            disc_text = _first_text(soup, [".price-block__discount", ".discount__percent"])
            data.discount_percent = _parse_discount_percent(disc_text)

        if data.discount_percent is None and data.price is not None and data.old_price:
            if data.old_price > 0:
                data.discount_percent = round((1 - (data.price / data.old_price)) * 100, 2)

        if data.stock is None:
            data.stock = _parse_stock_from_html(html)

        return {
            "external_id": external_id,
            "name": data.name,
            "title": data.name,
            "price": data.price,
            "old_price": data.old_price,
            "discount_percent": data.discount_percent,
            "stock": data.stock,
            "rating": data.rating,
            "product_url": url,
            "image_url": data.image_url,
        }


def _normalize_product_url(raw: Any) -> str:
    if isinstance(raw, str):
        return raw.strip()
    if isinstance(raw, dict) and "url" in raw:
        return str(raw["url"]).strip()
    raise TypeError("raw must be a product URL string or dict with 'url'")


def _extract_external_id(url: str) -> str:
    m = re.search(r"/(\d+)(?:/|$)", url)
    if m:
        return m.group(1)
    m = re.search(r"nm=(\d+)", url)
    if m:
        return m.group(1)
    return url


def _fetch_html(url: str) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    resp: Response = requests.get(url, headers=headers, timeout=(5, 20))
    resp.raise_for_status()
    return resp.text


@dataclass
class _ParsedProduct:
    name: str | None = None
    price: float | None = None
    old_price: float | None = None
    discount_percent: float | None = None
    stock: int | None = None
    rating: float | None = None
    image_url: str | None = None


def _parse_from_json_ld(soup: BeautifulSoup) -> _ParsedProduct:
    result = _ParsedProduct()

    for tag in soup.select('script[type="application/ld+json"]'):
        if not tag.string:
            continue
        try:
            payload = json.loads(tag.string)
        except json.JSONDecodeError:
            continue

        items = payload if isinstance(payload, list) else [payload]
        for item in items:
            if not isinstance(item, dict):
                continue

            item_type = item.get("@type")
            if isinstance(item_type, list):
                is_product = "Product" in item_type
            else:
                is_product = item_type == "Product"

            if not is_product:
                continue

            name = item.get("name")
            if isinstance(name, str) and name.strip():
                result.name = name.strip()

            image = item.get("image")
            if isinstance(image, str) and image.strip():
                result.image_url = image.strip()
            elif isinstance(image, list) and image:
                first = image[0]
                if isinstance(first, str) and first.strip():
                    result.image_url = first.strip()

            offers = item.get("offers")
            if isinstance(offers, dict):
                result.price = _parse_price(offers.get("price"))
                result.stock = _parse_stock_from_availability(offers.get("availability"))

            rating = item.get("aggregateRating")
            if isinstance(rating, dict):
                result.rating = _parse_float(rating.get("ratingValue"))

    return result


def _parse_stock_from_availability(value: Any) -> int | None:
    if not isinstance(value, str):
        return None
    if "InStock" in value:
        return None
    if "OutOfStock" in value:
        return 0
    return None


def _first_text(soup: BeautifulSoup, selectors: list[str]) -> str | None:
    for sel in selectors:
        node = soup.select_one(sel)
        if not node:
            continue
        text = node.get_text(" ", strip=True)
        if text:
            return text
    return None


def _parse_price(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value)
    digits = re.sub(r"[^0-9,\.]", "", s)
    if not digits:
        return None
    if digits.count(",") == 1 and digits.count(".") == 0:
        digits = digits.replace(",", ".")
    digits = re.sub(r"(?<=\d)[,](?=\d{3}(\D|$))", "", digits)
    try:
        return float(digits)
    except ValueError:
        return None


def _parse_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value)
    m = re.search(r"\d+(?:[\.,]\d+)?", s)
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", "."))
    except ValueError:
        return None


def _parse_discount_percent(value: Any) -> float | None:
    if value is None:
        return None
    s = str(value)
    m = re.search(r"-?\s*(\d+(?:[\.,]\d+)?)\s*%", s)
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", "."))
    except ValueError:
        return None


def _parse_stock_from_html(html: str) -> int | None:
    patterns = [
        r'"quantity"\s*:\s*(\d+)',
        r'"stock"\s*:\s*(\d+)',
        r'"stocks"\s*:\s*(\d+)',
    ]
    for p in patterns:
        m = re.search(p, html)
        if m:
            try:
                return int(m.group(1))
            except ValueError:
                return None
    return None
