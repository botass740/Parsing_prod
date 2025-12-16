from __future__ import annotations

from collections import deque
from collections.abc import Iterable
from datetime import datetime, timedelta, timezone
from html import escape
from typing import Any
import os
import logging

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, FSInputFile

from bot.config import PostingSettings

log = logging.getLogger(__name__)


class PostingService:
    def __init__(self, bot: Bot, settings: PostingSettings) -> None:
        self._bot = bot

        env_channel = os.getenv("POSTING_CHANNEL", "").strip()
        self._channel = (settings.channel or env_channel).strip()

        self._max_per_hour = settings.max_posts_per_hour
        self._sent: deque[datetime] = deque()

        log.info("PostingService channel resolved to %r", self._channel)

    async def post_product(self, product: dict[str, Any]) -> bool:
        if not self._channel:
            raise ValueError("POSTING_CHANNEL is not configured")

        if not self._allow_now():
            return False

        # Пробуем загрузить картинку товара, иначе используем заглушку
        image_url = product.get("image_url")
        photo: FSInputFile | str
        
        if image_url:
            photo = image_url
        else:
            photo = FSInputFile("test.jpg")

        url = _as_str(product.get("product_url"))
        caption = _build_caption(product)
        markup = _build_keyboard(url, product.get("external_id"))

        try:
            await self._bot.send_photo(
                chat_id=self._channel,
                photo=photo,
                caption=caption,
                reply_markup=markup,
                parse_mode="HTML",
            )
        except Exception as e:
            # Если не удалось загрузить картинку по URL — используем заглушку
            log.warning(f"Failed to send photo from URL, using fallback: {e}")
            await self._bot.send_photo(
                chat_id=self._channel,
                photo=FSInputFile("test.jpg"),
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


def _build_keyboard(url: str | None, article: str | None = None) -> InlineKeyboardMarkup | None:
    buttons = []
    
    if url:
        buttons.append([InlineKeyboardButton(text="🛒 Перейти к товару", url=url)])
    
    if not buttons:
        return None
        
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _build_caption(product: dict[str, Any]) -> str:
    """
    Формирует caption для поста.
    
    Формат:
    🟣 Бренд Название товара
    
    💰 Цена: от 928 ₽ до 1 189 ₽
    🔥 Скидка: 34% (было 1 546 ₽)
    ⭐ Рейтинг: 4.8 (230 отзывов)
    
    📎 Артикул: 169684889
    """
    lines = []
    
    # 1. Название
    name = _as_str(product.get("name")) or _as_str(product.get("title")) or "Товар"
    platform = product.get("platform", "").upper()
    platform_emoji = {"WB": "🟣", "OZON": "🔵", "DETMIR": "🟢"}.get(platform, "🛍")
    
    lines.append(f"{platform_emoji} <b>{escape(name)}</b>")
    lines.append("")  # Пустая строка
    
    # 2. Цена (диапазон)
    price_min = product.get("price_min")
    price_max = product.get("price_max")
    price = product.get("price")  # fallback
    
    if price_min is not None and price_max is not None:
        price_min_fmt = _format_price(price_min)
        price_max_fmt = _format_price(price_max)
        
        if price_min == price_max:
            lines.append(f"💰 Цена: <b>{price_min_fmt} ₽</b>")
        else:
            lines.append(f"💰 Цена: <b>от {price_min_fmt} ₽ до {price_max_fmt} ₽</b>")
    elif price is not None:
        lines.append(f"💰 Цена: <b>{_format_price(price)} ₽</b>")
    
    # 3. Скидка и старая цена
    discount = product.get("discount_percent")
    old_price = product.get("old_price")
    
    if discount is not None and old_price is not None:
        old_price_fmt = _format_price(old_price)
        lines.append(f"🔥 Скидка: <b>{int(discount)}%</b> (было {old_price_fmt} ₽)")
    elif discount is not None:
        lines.append(f"🔥 Скидка: <b>{int(discount)}%</b>")
    elif old_price is not None:
        old_price_fmt = _format_price(old_price)
        lines.append(f"💸 Было: <s>{old_price_fmt} ₽</s>")
    
    # 4. Рейтинг (только если есть)
    rating = product.get("rating")
    feedbacks = product.get("feedbacks", 0)
    
    if rating is not None and rating > 0:
        if feedbacks > 0:
            lines.append(f"⭐ Рейтинг: <b>{rating}</b> ({feedbacks} отзывов)")
        else:
            lines.append(f"⭐ Рейтинг: <b>{rating}</b>")
    elif feedbacks > 0:
        lines.append(f"💬 Отзывов: {feedbacks}")
    
    # 5. Артикул
    article = product.get("external_id")
    if article:
        lines.append("")
        lines.append(f"📎 Артикул: <code>{escape(str(article))}</code>")
    
    return "\n".join(lines)


def _format_price(price: float | int) -> str:
    """Форматирует цену с разделителями тысяч."""
    if price is None:
        return "—"
    
    # Округляем до целых
    price_int = int(round(price))
    
    # Форматируем с пробелами между тысячами
    return f"{price_int:,}".replace(",", " ")


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    return s or None