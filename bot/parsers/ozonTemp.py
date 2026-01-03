# bot/parsers/ozon.py
"""
Парсер OZON с двумя режимами:
- COLLECT: сбор товаров через infinite scroll (для наполнения БД)
- MONITOR: проверка цен через API (для мониторинга)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import Any, Iterable

log = logging.getLogger(__name__)

# CDP подключение к Chrome
CDP_URL = os.getenv("OZON_CDP_URL", "http://localhost:9222").strip()

# === Настройки COLLECT режима ===
COLLECT_TARGET_COUNT = int(os.getenv("OZON_COLLECT_TARGET", "3000"))
SCROLL_DELAY_SEC = float(os.getenv("OZON_SCROLL_DELAY_SEC", "1.2"))
MAX_SCROLL_STEPS = int(os.getenv("OZON_MAX_SCROLL_STEPS", "500"))
QUIET_STEPS_STOP = int(os.getenv("OZON_QUIET_STEPS_STOP", "30"))
LOG_EVERY_STEPS = int(os.getenv("OZON_LOG_EVERY_STEPS", "25"))

# === Настройки MONITOR режима ===
MONITOR_BATCH_SIZE = int(os.getenv("OZON_MONITOR_BATCH_SIZE", "100"))
MONITOR_REQUEST_DELAY = float(os.getenv("OZON_MONITOR_REQUEST_DELAY", "0.3"))
MONITOR_ERROR_DELAY = float(os.getenv("OZON_MONITOR_ERROR_DELAY", "2.0"))
MONITOR_MAX_ERRORS = int(os.getenv("OZON_MONITOR_MAX_ERRORS", "10"))

# Категории для сбора
DEFAULT_SEED_URLS = [
    "https://www.ozon.ru/category/smartfony-15502/",
    "https://www.ozon.ru/category/noutbuki-15692/",
    "https://www.ozon.ru/category/naushniki-i-bluetooth-garnitury-15548/",
    "https://www.ozon.ru/category/planshety-15525/",
    "https://www.ozon.ru/category/televizory-15528/",
]

# Пропускать товары с ценой только по карте
SKIP_CARD_ONLY_ITEMS = os.getenv("OZON_SKIP_CARD_ONLY", "false").lower() in ("1", "true", "yes")


def _extract_price(text: str) -> int | None:
    """Извлекает число из строки с ценой."""
    if not text:
        return None
    digits = re.sub(r"[^\d]", "", str(text))
    return int(digits) if digits else None


def _parse_discount(discount_str: str | None) -> int | None:
    """Парсит процент скидки."""
    if not discount_str:
        return None
    match = re.search(r"(\d+)", str(discount_str))
    return int(match.group(1)) if match else None


class OzonParser:
    """
    Парсер OZON.
    
    Режимы:
    - COLLECT: parse_products_batch([]) — сбор через scroll
    - MONITOR: parse_products_batch(["sku1", "sku2", ...]) — проверка через API
    """

    def __init__(self, product_ids: Iterable[int | str] | None = None) -> None:
        self._product_ids = [str(x) for x in product_ids] if product_ids else []
        
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None
        self._connected = False

    # =========================================================================
    # Подключение к Chrome
    # =========================================================================

    async def _connect(self) -> None:
        """Подключается к Chrome через CDP."""
        if self._connected and self._page:
            return

        from bot.utils.chrome_manager import ensure_chrome_running
        
        ok = await ensure_chrome_running()
        if not ok:
            raise RuntimeError("Не удалось запустить Chrome для OZON")

        from playwright.async_api import async_playwright
        
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.connect_over_cdp(CDP_URL)

        self._context = self._browser.contexts[0] if self._browser.contexts else await self._browser.new_context()
        self._page = self._context.pages[0] if self._context.pages else await self._context.new_page()

        # Инициализируем сессию
        await self._page.goto("https://www.ozon.ru/", wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(2)
        
        self._connected = True
        log.info("OZON: connected to Chrome")

    async def _ensure_connected(self) -> None:
        """Проверяет подключение."""
        if not self._connected:
            await self._connect()

    async def close(self) -> None:
        """Закрывает подключение."""
        try:
            if self._playwright:
                await self._playwright.stop()
        except Exception:
            pass
        
        self._connected = False
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None

    # =========================================================================
    # Основные методы
    # =========================================================================

    async def fetch_products(self) -> Iterable[Any]:
        """Возвращает список SKU для мониторинга."""
        return list(self._product_ids)

    async def parse_product(self, raw: Any) -> dict[str, Any]:
        """Парсит один товар."""
        await self._ensure_connected()
        sku = str(raw)
        products = await self._monitor_products([sku])
        return products[0] if products else self._empty_product(sku)

    async def parse_products_batch(self, product_ids: list[int | str]) -> list[dict[str, Any]]:
        """
        Основной метод парсинга.
        
        - Если product_ids пустой → COLLECT режим (scroll)
        - Если product_ids заполнен → MONITOR режим (API)
        """
        await self._ensure_connected()

        if not product_ids:
            log.info("OZON: COLLECT mode (scroll)")
            return await self._collect_from_scroll()
        else:
            log.info("OZON: MONITOR mode (%d products)", len(product_ids))
            return await self._monitor_products(product_ids)

    # =========================================================================
    # COLLECT режим: сбор через scroll
    # =========================================================================

    async def _collect_from_scroll(self) -> list[dict[str, Any]]:
        """Собирает товары через infinite scroll."""
        
        collected: dict[str, dict[str, Any]] = {}
        quiet_steps = 0

        async def on_response(response):
            nonlocal quiet_steps
            try:
                ct = (response.headers.get("content-type") or "").lower()

                # Берём только ответы, похожие на json
                if "json" not in ct:
                    return

                # Пытаемся распарсить JSON (даже если URL не тот, tileGrid может быть внутри)
                try:
                    data = await response.json()
                except Exception:
                    return

                if not isinstance(data, dict):
                    return

                items = self._parse_tile_grid(data)
                if not items:
                    return

                before = len(collected)
                for item in items:
                    eid = item.get("external_id")
                    if eid and eid not in collected:
                        collected[eid] = item

                if len(collected) > before:
                    quiet_steps = 0
                    log.info("OZON COLLECT: +%d (total=%d)", len(collected) - before, len(collected))
                else:
                    quiet_steps += 1

            except Exception:
                # чтобы не падать на любом странном ответе
                return
        log.info("OZON: attach network response listener")
        self._page.on("response", on_response)

        target = COLLECT_TARGET_COUNT

        for seed_url in DEFAULT_SEED_URLS:
            if len(collected) >= target:
                break

            quiet_steps = 0
            log.info("OZON: opening %s", seed_url)

            try:
                await self._page.goto(seed_url, wait_until="networkidle", timeout=30000)
            except Exception as e:
                log.warning("OZON: failed to open %s: %s", seed_url, e)
                continue

            await asyncio.sleep(3)

            for step in range(1, MAX_SCROLL_STEPS + 1):
                if len(collected) >= target:
                    break

                await self._page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(SCROLL_DELAY_SEC)

                if step % LOG_EVERY_STEPS == 0:
                    log.info("OZON scroll step=%d, collected=%d/%d", step, len(collected), target)

                if quiet_steps >= QUIET_STEPS_STOP:
                    log.info("OZON: no new items for %d steps, moving to next category", quiet_steps)
                    break
        log.info("OZON: detach network response listener")
        self._page.remove_listener("response", on_response)

        result = list(collected.values())
        log.info("OZON COLLECT done: %d items", len(result))
        return result

    def _parse_tile_grid(self, page_json: dict) -> list[dict[str, Any]]:
        """Парсит товары из tileGrid виджета."""
        
        widget_states = page_json.get("widgetStates") or {}
        items = []

        for key, value in widget_states.items():
            if "tileGrid" not in key.lower():
                continue
            
            if not isinstance(value, str):
                continue

            try:
                parsed = json.loads(value)
            except Exception:
                continue

            for item in parsed.get("items") or []:
                product = self._parse_tile_item(item)
                if product:
                    items.append(product)

        return items

    def _parse_tile_item(self, item: dict) -> dict[str, Any] | None:
        """Парсит один товар из tile."""
        
        sku = item.get("sku")
        if not sku:
            return None

        name = None
        price = None
        old_price = None
        discount_percent = None
        rating = None
        feedbacks = None
        image_url = None
        product_url = None

        # URL товара
        action = item.get("action") or {}
        link = action.get("link")
        if link:
            product_url = link if link.startswith("http") else "https://www.ozon.ru" + link.split("?")[0]

        # Картинка
        tile_image = (item.get("tileImage") or {}).get("items") or []
        if tile_image:
            image_url = (tile_image[0].get("image") or {}).get("link")

        is_card_price = False

        for state in item.get("mainState") or []:
            state_type = state.get("type")

            if state_type == "textAtom":
                ta = state.get("textAtom") or {}
                if not name:
                    name = ta.get("text")

            if state_type == "priceV2":
                pv = state.get("priceV2") or {}

                style_type = ((pv.get("priceStyle") or {}).get("styleType") or "").upper()
                if style_type == "CARD_PRICE":
                    is_card_price = True

                discount_percent = _parse_discount(pv.get("discount"))

                for p in pv.get("price") or []:
                    style = p.get("textStyle")
                    val = _extract_price(p.get("text"))
                    if not val:
                        continue
                    if style == "PRICE":
                        price = val
                    elif style == "ORIGINAL_PRICE":
                        old_price = val

            if state_type == "labelList":
                for label in (state.get("labelList") or {}).get("items") or []:
                    icon = (label.get("icon") or {}).get("image") or ""
                    title = label.get("title") or ""

                    if "star" in icon and rating is None:
                        m = re.search(r"(\d+[.,]\d+|\d+)", title.replace(",", "."))
                        if m:
                            try:
                                rating = float(m.group(1))
                            except Exception:
                                pass

                    if "dialog" in icon and feedbacks is None:
                        digits = re.sub(r"[^\d]", "", title)
                        if digits:
                            try:
                                feedbacks = int(digits)
                            except Exception:
                                pass

        # Пропускаем если только цена по карте
        if SKIP_CARD_ONLY_ITEMS and is_card_price and not old_price:
            return None

        if price is None:
            return None

        return {
            "external_id": str(sku),
            "platform": "ozon",
            "name": name,
            "title": name,
            "price": price,
            "old_price": old_price,
            "discount_percent": discount_percent,
            "rating": rating,
            "feedbacks": feedbacks,
            "product_url": product_url,
            "image_url": image_url,
        }

    # =========================================================================
    # MONITOR режим: проверка через API
    # =========================================================================

    async def _monitor_products(self, product_ids: list[int | str]) -> list[dict[str, Any]]:
        """Проверяет цены товаров через API."""
        
        results = []
        errors_count = 0
        total = len(product_ids)

        for idx, sku in enumerate(product_ids, 1):
            sku = str(sku)
            
            try:
                product = await self._fetch_product_api(sku)
                
                if product.get("price"):
                    results.append(product)
                    errors_count = 0  # Сбрасываем счётчик ошибок
                else:
                    log.debug("OZON: no price for %s", sku)
                    errors_count += 1

            except Exception as e:
                log.warning("OZON: error fetching %s: %s", sku, e)
                errors_count += 1
                await asyncio.sleep(MONITOR_ERROR_DELAY)

            # Слишком много ошибок подряд — возможно бан
            if errors_count >= MONITOR_MAX_ERRORS:
                log.error("OZON: too many errors, stopping monitor")
                break

            # Прогресс
            if idx % 100 == 0:
                log.info("OZON monitor: %d/%d, success=%d", idx, total, len(results))

            await asyncio.sleep(MONITOR_REQUEST_DELAY)

        log.info("OZON MONITOR done: %d/%d products", len(results), total)
        return results

    async def _fetch_product_api(self, sku: str) -> dict[str, Any]:
        """Получает данные товара через API."""
        
        # Пробуем с полным URL, если не работает — с коротким
        slug = f"/product/{sku}/"
        api_url = f"https://www.ozon.ru/api/entrypoint-api.bx/page/json/v2?url={slug}"

        response = await self._page.evaluate(f"""
            async () => {{
                try {{
                    const resp = await fetch("{api_url}");
                    if (!resp.ok) return {{error: resp.status}};
                    return await resp.json();
                }} catch (e) {{
                    return {{error: e.message}};
                }}
            }}
        """)

        if isinstance(response, dict) and "error" in response:
            return self._empty_product(sku, error=str(response["error"]))

        return self._parse_product_api(response, sku)

    def _parse_product_api(self, data: dict, sku: str) -> dict[str, Any]:
        """Парсит данные товара из API ответа."""
        
        result = self._empty_product(sku)
        widget_states = data.get("widgetStates") or {}

        for key, value in widget_states.items():
            if not isinstance(value, str):
                continue

            try:
                parsed = json.loads(value)
            except Exception:
                continue

            # === webPrice — цены ===
            if "webPrice" in key and "Decreased" not in key:
                result["price"] = _extract_price(parsed.get("price"))
                result["card_price"] = _extract_price(parsed.get("cardPrice"))
                result["old_price"] = _extract_price(parsed.get("originalPrice"))
                result["in_stock"] = parsed.get("isAvailable", True)

                # Рассчитываем скидку
                if result["price"] and result["old_price"] and result["old_price"] > result["price"]:
                    result["discount_percent"] = round((1 - result["price"] / result["old_price"]) * 100)

            # === webProductHeading — название ===
            if "webProductHeading" in key:
                result["name"] = parsed.get("title")
                result["title"] = parsed.get("title")

            # === webGallery — картинка ===
            if "webGallery" in key:
                covers = parsed.get("covers") or []
                if covers:
                    result["image_url"] = covers[0].get("link")

            # === webReviewProductScore — рейтинг ===
            if "webReviewProductScore" in key:
                result["rating"] = parsed.get("score")
                result["feedbacks"] = parsed.get("count")

        # URL товара
        result["product_url"] = f"https://www.ozon.ru/product/{sku}/"

        return result

    def _empty_product(self, sku: str, error: str | None = None) -> dict[str, Any]:
        """Возвращает пустую структуру товара."""
        result = {
            "external_id": str(sku),
            "platform": "ozon",
            "name": None,
            "title": None,
            "price": None,
            "card_price": None,
            "old_price": None,
            "discount_percent": None,
            "rating": None,
            "feedbacks": None,
            "in_stock": None,
            "product_url": f"https://www.ozon.ru/product/{sku}/",
            "image_url": None,
        }
        if error:
            result["error"] = error
        return result