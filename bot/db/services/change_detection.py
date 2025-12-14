from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import Platform, PlatformCode, PriceHistory, Product


@dataclass(frozen=True)
class FieldChange:
    field: str
    old: Any
    new: Any


@dataclass(frozen=True)
class ChangeResult:
    product: Product
    changes: list[FieldChange]
    is_new: bool


async def detect_and_save_changes(
    session: AsyncSession,
    *,
    platform_code: PlatformCode,
    items: list[dict[str, Any]],
) -> list[ChangeResult]:
    platform = await _get_or_create_platform(session, platform_code)

    external_ids: list[str] = []
    by_external_id: dict[str, dict[str, Any]] = {}
    for item in items:
        ext = _as_str(item.get("external_id"))
        if not ext:
            continue
        external_ids.append(ext)
        by_external_id[ext] = item

    existing: dict[str, Product] = {}
    if external_ids:
        stmt = select(Product).where(
            Product.platform_id == platform.id,
            Product.external_id.in_(external_ids),
        )
        res = await session.execute(stmt)
        for p in res.scalars().all():
            existing[p.external_id] = p

    now = datetime.now(timezone.utc)
    results: list[ChangeResult] = []

    for external_id, item in by_external_id.items():
        product = existing.get(external_id)

        incoming_price = _to_decimal(item.get("price"))
        incoming_old_price = _to_decimal(item.get("old_price"))
        incoming_discount = _as_float(item.get("discount_percent"))
        incoming_stock = _as_int(item.get("stock"))
        incoming_rating = _as_float(item.get("rating"))

        title = _as_str(item.get("title")) or _as_str(item.get("name"))
        url = _as_str(item.get("product_url")) or _as_str(item.get("url"))

        if product is None:
            product = Product(
                platform_id=platform.id,
                external_id=external_id,
                title=title or external_id,
                url=url,
                current_price=incoming_price,
                old_price=incoming_old_price,
                discount=incoming_discount,
                stock=incoming_stock,
                rating=incoming_rating,
                last_checked_at=now,
            )
            session.add(product)
            await session.flush()

            history = PriceHistory(
                product_id=product.id,
                price=incoming_price,
                old_price=incoming_old_price,
                discount=incoming_discount,
                stock=incoming_stock,
                rating=incoming_rating,
                checked_at=now,
            )
            session.add(history)

            results.append(ChangeResult(product=product, changes=[], is_new=True))
            continue

        changes: list[FieldChange] = []

        if _decimal_changed(product.current_price, incoming_price):
            changes.append(FieldChange("price", product.current_price, incoming_price))
            product.current_price = incoming_price

        if _decimal_changed(product.old_price, incoming_old_price):
            changes.append(FieldChange("old_price", product.old_price, incoming_old_price))
            product.old_price = incoming_old_price

        if _float_changed(product.discount, incoming_discount):
            changes.append(FieldChange("discount", product.discount, incoming_discount))
            product.discount = incoming_discount

        if _int_changed(product.stock, incoming_stock):
            changes.append(FieldChange("stock", product.stock, incoming_stock))
            product.stock = incoming_stock

        if _float_changed(product.rating, incoming_rating):
            changes.append(FieldChange("rating", product.rating, incoming_rating))
            product.rating = incoming_rating

        if title and product.title != title:
            product.title = title

        if url and product.url != url:
            product.url = url

        product.last_checked_at = now

        meaningful = any(c.field in {"price", "old_price", "discount", "stock"} for c in changes)
        if meaningful:
            history = PriceHistory(
                product_id=product.id,
                price=product.current_price,
                old_price=product.old_price,
                discount=product.discount,
                stock=product.stock,
                rating=product.rating,
                checked_at=now,
            )
            session.add(history)

            results.append(ChangeResult(product=product, changes=changes, is_new=False))

    return results


async def _get_or_create_platform(session: AsyncSession, code: PlatformCode) -> Platform:
    stmt = select(Platform).where(Platform.code == code)
    res = await session.execute(stmt)
    platform = res.scalar_one_or_none()
    if platform is not None:
        return platform

    name_map = {
        PlatformCode.WB: "Wildberries",
        PlatformCode.OZON: "Ozon",
        PlatformCode.DM: "Detmir",
    }
    platform = Platform(code=code, name=name_map.get(code, code.value))
    session.add(platform)
    await session.flush()
    return platform


def _to_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        return Decimal(str(value))
    s = str(value).strip()
    if not s:
        return None
    s = s.replace(",", ".")
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip().replace(",", ".")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _as_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    s = str(value).strip()
    if not s:
        return None
    try:
        return int(s)
    except ValueError:
        return None


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    return s or None


def _decimal_changed(old: Decimal | None, new: Decimal | None) -> bool:
    if old is None and new is None:
        return False
    if old is None or new is None:
        return True
    return old != new


def _int_changed(old: int | None, new: int | None) -> bool:
    if old is None and new is None:
        return False
    if old is None or new is None:
        return True
    return old != new


def _float_changed(old: float | None, new: float | None, *, eps: float = 1e-6) -> bool:
    if old is None and new is None:
        return False
    if old is None or new is None:
        return True
    return abs(old - new) > eps
