from __future__ import annotations

from collections import deque
from collections.abc import Iterable
from datetime import datetime, timedelta, timezone
from html import escape
from typing import Any

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.config import PostingSettings

class PostingService:
    def __init__(self, bot: Bot, settings: PostingSettings) -> None:
        self._bot = bot
        self._channel = settings.channel
        self._max_per_hour = settings.max_posts_per_hour
        self._sent: deque[datetime] = deque()

    async def post_product(self, product: dict[str, Any]) -> bool:
        if not self._channel:
            raise ValueError("POSTING_CHANNEL is not configured")

        if not self._allow_now():
            return False

        photo = _as_str(product.get("image_url"))
        url = _as_str(product.get("product_url"))

        caption = _build_caption(product)
        markup = _build_keyboard(url)

        if not photo:
            raise ValueError("Product has no image_url")

        await self._bot.send_photo(
            chat_id=self._channel,
            photo=photo,
            caption=caption,
            reply_markup=markup,
            parse_mode="HTML",
        )

        self._mark_sent()
        return True

    async def post_products(self, products: Iterable[dict[str, Any]]) -> int:
        posted = 0
        for p in products:
            ok = await self.post_product(p)
            if not ok:
                break
            posted += 1
        return posted

    def _allow_now(self) -> bool:
        if self._max_per_hour <= 0:
            return True

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=1)
        while self._sent and self._sent[0] < cutoff:
            self._sent.popleft()
        return len(self._sent) < self._max_per_hour

    def _mark_sent(self) -> None:
        self._sent.append(datetime.now(timezone.utc))


def _build_keyboard(url: str | None) -> InlineKeyboardMarkup | None:
    if not url:
        return None
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Открыть", url=url)],
        ]
    )


def _build_caption(product: dict[str, Any]) -> str:
    name = _as_str(product.get("name")) or _as_str(product.get("title")) or ""
    price = product.get("price")
    old_price = product.get("old_price")
    discount = product.get("discount_percent")

    name_line = f"<b>{escape(name)}</b>" if name else "<b>Товар</b>"

    price_line = ""
    if old_price is not None and price is not None:
        price_line = f"<s>{escape(str(old_price))}</s> → <b>{escape(str(price))}</b>"
    elif price is not None:
        price_line = f"<b>{escape(str(price))}</b>"

    discount_line = ""
    if discount is not None:
        discount_line = f"Скидка: <b>{escape(str(discount))}%</b>"

    parts = [name_line]
    if price_line:
        parts.append(price_line)
    if discount_line:
        parts.append(discount_line)

    return "\n".join(parts)


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    return s or None
