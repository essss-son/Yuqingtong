"""服务模块"""
from .briefing import BriefingService, briefing_service
from .embedding import EmbeddingServiceWrapper, embedding_service
from .crawler import CrawlerService, crawler_service

__all__ = [
    "BriefingService", "briefing_service",
    "EmbeddingServiceWrapper", "embedding_service",
    "CrawlerService", "crawler_service"
]
