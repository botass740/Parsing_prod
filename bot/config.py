from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ParsingIntervals(BaseModel):
    wb_seconds: int = Field(default=300, validation_alias="PARSING_WB_SECONDS")
    ozon_seconds: int = Field(default=300, validation_alias="PARSING_OZON_SECONDS")
    detmir_seconds: int = Field(default=300, validation_alias="PARSING_DETMIR_SECONDS")


class PublishingLimits(BaseModel):
    max_posts_per_run: int = Field(default=20, validation_alias="PUBLISHING_MAX_POSTS_PER_RUN")
    max_posts_per_day: int = Field(default=200, validation_alias="PUBLISHING_MAX_POSTS_PER_DAY")


class PostingSettings(BaseModel):
    channel: str = Field(default="", validation_alias="POSTING_CHANNEL")
    max_posts_per_hour: int = Field(default=20, validation_alias="POSTING_MAX_POSTS_PER_HOUR")


class FilteringThresholds(BaseModel):
    min_price: float = Field(default=0.0, validation_alias="FILTER_MIN_PRICE")
    max_price: float = Field(default=0.0, validation_alias="FILTER_MAX_PRICE")
    min_stock: int = Field(default=0, validation_alias="FILTER_MIN_STOCK")
    min_discount_percent: float = Field(default=0.0, validation_alias="FILTER_MIN_DISCOUNT_PERCENT")
    categories: list[str] = Field(default_factory=list, validation_alias="FILTER_CATEGORIES")

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
    postgres_dsn: str = Field(validation_alias=("POSTGRES_DSN", "DATABASE_DSN"))

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
