from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Iterable

from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.db.models import Platform, PlatformCode, Product

log = logging.getLogger(__name__)


class ProductManager:
    """Управление списком товаров для мониторинга."""
    
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def add_products(
        self,
        platform: PlatformCode,
        external_ids: Iterable[str],
    ) -> tuple[int, int]:
        """
        Добавляет товары в мониторинг.
        
        Returns:
            (added, skipped) — количество добавленных и пропущенных
        """
        external_ids = [str(eid).strip() for eid in external_ids if str(eid).strip()]
        
        if not external_ids:
            return 0, 0
        
        async with self._session_factory() as session:
            # Получаем или создаём платформу
            platform_obj = await self._get_or_create_platform(session, platform)
            
            # Проверяем какие уже есть
            stmt = select(Product.external_id).where(
                Product.platform_id == platform_obj.id,
                Product.external_id.in_(external_ids),
            )
            result = await session.execute(stmt)
            existing = {row[0] for row in result.fetchall()}
            
            # Добавляем новые
            added = 0
            for eid in external_ids:
                if eid in existing:
                    continue
                
                product = Product(
                    platform_id=platform_obj.id,
                    external_id=eid,
                    title=f"Товар {eid}",  # Временное название
                )
                session.add(product)
                added += 1
            
            await session.commit()
            
            skipped = len(external_ids) - added
            log.info(f"Added {added} products, skipped {skipped} (already exist)")
            
            return added, skipped

    async def remove_products(
        self,
        platform: PlatformCode,
        external_ids: Iterable[str],
    ) -> int:
        """Удаляет товары из мониторинга."""
        external_ids = [str(eid).strip() for eid in external_ids if str(eid).strip()]
        
        if not external_ids:
            return 0
        
        async with self._session_factory() as session:
            platform_obj = await self._get_platform(session, platform)
            if not platform_obj:
                return 0
            
            stmt = delete(Product).where(
                Product.platform_id == platform_obj.id,
                Product.external_id.in_(external_ids),
            )
            result = await session.execute(stmt)
            await session.commit()
            
            deleted = result.rowcount
            log.info(f"Removed {deleted} products")
            
            return deleted

    async def get_product_ids(self, platform: PlatformCode) -> list[str]:
        """Возвращает список артикулов для мониторинга."""
        async with self._session_factory() as session:
            platform_obj = await self._get_platform(session, platform)
            if not platform_obj:
                return []
            
            stmt = select(Product.external_id).where(
                Product.platform_id == platform_obj.id,
            )
            result = await session.execute(stmt)
            
            return [row[0] for row in result.fetchall()]

    async def get_product_count(self, platform: PlatformCode) -> int:
        """Возвращает количество товаров."""
        async with self._session_factory() as session:
            platform_obj = await self._get_platform(session, platform)
            if not platform_obj:
                return 0
            
            stmt = select(func.count(Product.id)).where(
                Product.platform_id == platform_obj.id,
            )
            result = await session.execute(stmt)
            
            return result.scalar() or 0

    async def import_from_csv(
        self,
        platform: PlatformCode,
        file_path: str | Path,
        column: str = "article",
    ) -> tuple[int, int]:
        """
        Импортирует артикулы из CSV файла.
        
        Args:
            platform: Платформа (WB, OZON, DM)
            file_path: Путь к CSV файлу
            column: Название колонки с артикулами
        
        Returns:
            (added, skipped)
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        external_ids = []
        
        with open(file_path, "r", encoding="utf-8-sig") as f:
            sample = f.read(1024)
            f.seek(0)
            
            if ";" in sample:
                delimiter = ";"
            elif "\t" in sample:
                delimiter = "\t"
            else:
                delimiter = ","
            
            reader = csv.DictReader(f, delimiter=delimiter)
            
            fieldnames_lower = {fn.lower(): fn for fn in (reader.fieldnames or [])}
            
            actual_column = None
            for col_name in [column, "article", "артикул", "nm_id", "nmid", "sku", "id"]:
                if col_name.lower() in fieldnames_lower:
                    actual_column = fieldnames_lower[col_name.lower()]
                    break
            
            if not actual_column:
                actual_column = reader.fieldnames[0] if reader.fieldnames else None
            
            if not actual_column:
                raise ValueError("Cannot find article column in CSV")
            
            log.info(f"Using column '{actual_column}' from CSV")
            
            for row in reader:
                value = row.get(actual_column, "").strip()
                if value and value.isdigit():
                    external_ids.append(value)
        
        log.info(f"Found {len(external_ids)} articles in CSV")
        
        return await self.add_products(platform, external_ids)

    async def import_from_text(
        self,
        platform: PlatformCode,
        text: str,
    ) -> tuple[int, int]:
        """
        Импортирует артикулы из текста.
        """
        import re
        
        external_ids = re.findall(r'\d+', text)
        external_ids = [eid for eid in external_ids if len(eid) >= 6]
        
        log.info(f"Found {len(external_ids)} articles in text")
        
        return await self.add_products(platform, external_ids)

    async def clear_all(self, platform: PlatformCode) -> int:
        """Удаляет все товары платформы."""
        async with self._session_factory() as session:
            platform_obj = await self._get_platform(session, platform)
            if not platform_obj:
                return 0
            
            stmt = delete(Product).where(Product.platform_id == platform_obj.id)
            result = await session.execute(stmt)
            await session.commit()
            
            return result.rowcount

    async def _get_or_create_platform(
        self,
        session: AsyncSession,
        code: PlatformCode,
    ) -> Platform:
        """Получает или создаёт платформу."""
        stmt = select(Platform).where(Platform.code == code)
        result = await session.execute(stmt)
        platform = result.scalar_one_or_none()
        
        if platform:
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

    async def _get_platform(
        self,
        session: AsyncSession,
        code: PlatformCode,
    ) -> Platform | None:
        """Получает платформу."""
        stmt = select(Platform).where(Platform.code == code)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()