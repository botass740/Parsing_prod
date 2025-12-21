from typing import Annotated

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from dotenv import load_dotenv  # ← ДОБАВИТЬ

load_dotenv()  # ← ДОБАВИТЬ


class ParsingIntervals(BaseModel):
    wb_seconds: int = Field(default=300, validation_alias="PARSING_WB_SECONDS")
    ozon_seconds: int = Field(default=300, validation_alias="PARSING_OZON_SECONDS")
    detmir_seconds: int = Field(default=300, validation_alias="PARSING_DETMIR_SECONDS")


class PublishingLimits(BaseModel):
    max_posts_per_run: int = Field(default=20, validation_alias="PUBLISHING_MAX_POSTS_PER_RUN")
    max_posts_per_day: int = Field(default=200, validation_alias="PUBLISHING_MAX_POSTS_PER_DAY")


class PostingSettings(BaseModel):
    channel: str = Field(default="", validation_alias="POSTING_CHANNEL")
    max_posts_per_hour: int = Field(default=50, validation_alias="POSTING_MAX_POSTS_PER_HOUR")


class FilteringThresholds(BaseModel):
    min_price: float = Field(default=0.0, validation_alias="FILTER_MIN_PRICE")
    max_price: float = Field(default=0.0, validation_alias="FILTER_MAX_PRICE")
    min_stock: int = Field(default=0, validation_alias="FILTER_MIN_STOCK")
    min_discount_percent: float = Field(default=0.0, validation_alias="FILTER_MIN_DISCOUNT_PERCENT")
    categories: list[str] = Field(default_factory=list, validation_alias="FILTER_CATEGORIES")
    
    # Пороги для публикации
    min_price_drop_percent: float = Field(default=1.0, validation_alias="MIN_PRICE_DROP_PERCENT")
    min_discount_increase: float = Field(default=5.0, validation_alias="MIN_DISCOUNT_INCREASE")

    @field_validator("categories", mode="before")
    @classmethod
    def _parse_categories(cls, v):
        if v is None:
            return []
        if isinstance(v, list):
            return [str(x).strip() for x in v if str(x).strip()]
        s = str(v).strip()
        if not s:
            return []
        return [part.strip() for part in s.split(",") if part.strip()]


class Settings(BaseSettings):
    bot_token: str = Field(validation_alias="BOT_TOKEN")
    #postgres_dsn: str = Field(validation_alias=("POSTGRES_DSN", "DATABASE_DSN"))
    postgres_dsn: str = Field(validation_alias="DATABASE_DSN")

    wb_nm_ids: Annotated[list[int], NoDecode] = Field(default_factory=list, validation_alias="WB_NM_IDS")

    @field_validator("wb_nm_ids", mode="before")
    @classmethod
    def _parse_wb_nm_ids(cls, v):
        if v is None:
            return []
        if isinstance(v, list):
            result: list[int] = []
            for x in v:
                try:
                    result.append(int(x))
                except (TypeError, ValueError):
                    continue
            return result
        s = str(v).strip()
        if not s:
            return []
        result: list[int] = []
        for part in s.split(","):
            part = part.strip()
            if not part:
                continue
            try:
                result.append(int(part))
            except ValueError:
                continue
        return result

    parsing: ParsingIntervals = ParsingIntervals()
    publishing: PublishingLimits = PublishingLimits()
    posting: PostingSettings = PostingSettings()
    filtering: FilteringThresholds = FilteringThresholds()
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="",
        extra="ignore",
    )


def load_settings() -> Settings:
    return Settings()
