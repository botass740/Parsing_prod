from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from bot.config import FilteringThresholds

class FilterService:
    def __init__(self, thresholds: FilteringThresholds) -> None:
        self._t = thresholds

    def filter_products(self, products: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
        return [p for p in products if self.passes(p)]

    def passes(self, product: dict[str, Any]) -> bool:
        price = _as_float(product.get("price"))
        stock = _as_int(product.get("stock"))
        discount = _as_float(product.get("discount_percent"))
        category = _as_str(product.get("category"))

        if price is None:
            if self._t.min_price > 0:
                return False
            if self._t.max_price > 0:
                return False
        else:
            if price < self._t.min_price:
                return False
            if self._t.max_price > 0 and price > self._t.max_price:
                return False

        if self._t.min_stock > 0:
            if stock is None:
                return False
            if stock < self._t.min_stock:
                return False

        if self._t.min_discount_percent > 0:
            if discount is None:
                return False
            if discount < self._t.min_discount_percent:
                return False

        if self._t.categories:
            if category is None:
                return False
            allowed = {c.casefold() for c in self._t.categories}
            if category.casefold() not in allowed:
                return False

        return True


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).replace(",", ".").strip())
    except ValueError:
        return None


def _as_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    try:
        return int(str(value).strip())
    except ValueError:
        return None


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    return s or None
