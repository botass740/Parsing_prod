from __future__ import annotations

from typing import Any, Iterable

from bot.parsers.base import BaseParser


class DetmirParser(BaseParser):
    async def fetch_products(self) -> Iterable[Any]:
        # TODO: implement fetching product list from Детский Мир
        return []

    async def parse_product(self, raw: Any) -> dict[str, Any]:
        # TODO: implement parsing a single Детский Мир product payload
        raise NotImplementedError
