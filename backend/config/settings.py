"""应用配置管理"""
from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    """应用配置"""

    # 应用配置
    APP_NAME: str = "Yuqingtong"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # API配置
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # 数据库配置
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "yuqing"
    POSTGRES_PASSWORD: str = "yuqing123"
    POSTGRES_DB: str = "yuqing_db"

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Redis配置
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None

    @property
    def REDIS_URL(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # LLM配置
    OPENAI_API_KEY: str = "sk-your-api-key"
    OPENAI_API_BASE: Optional[str] = None
    LLM_MODEL: str = "gpt-3.5-turbo"
    EMBEDDING_MODEL: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    RERANKER_MODEL: str = "BAAI/bge-reranker-base"

    # 检索配置
    EMBEDDING_DIM: int = 384
    TOP_K_CANDIDATES: int = 20
    TOP_K_RESULTS: int = 5

    # 缓存配置
    CACHE_TTL_SHORT: int = 300  # 5分钟
    CACHE_TTL_LONG: int = 3600  # 1小时
    HOT_TOPIC_THRESHOLD: int = 10  # 热点话题访问阈值

    # 爬虫配置
    CRAWLER_TIMEOUT: int = 30
    CRAWLER_MAX_RETRIES: int = 3
    CRAWLER_CONCURRENT_LIMIT: int = 5

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


settings = get_settings()
