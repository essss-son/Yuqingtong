"""嵌入服务"""
from typing import List, Dict, Any, Optional
import numpy as np
import logging
import asyncio
import time

from ..config import settings
from ..retrieval import EmbeddingService, retriever
from ..memory import db

logger = logging.getLogger(__name__)


class EmbeddingServiceWrapper:
    """嵌入服务封装"""

    def __init__(self):
        self.service = retriever.embedding_service
        self.db = db

    async def init(self):
        """初始化"""
        await self.service.init()

    async def encode_texts(
        self,
        texts: List[str]
    ) -> List[List[float]]:
        """编码文本列表"""
        start_time = time.time()

        embeddings = await self.service.encode(texts)

        elapsed = time.time() - start_time
        logger.info(f"Encoded {len(texts)} texts in {elapsed:.3f}s")

        return embeddings.tolist()

    async def encode_single(self, text: str) -> List[float]:
        """编码单个文本"""
        embedding = await self.service.encode_single(text)
        return embedding.tolist()

    async def index_documents(
        self,
        doc_ids: List[int],
        texts: List[str]
    ) -> int:
        """索引文档"""
        if len(doc_ids) != len(texts):
            raise ValueError("文档ID和文本数量不匹配")

        embeddings = await self.service.encode(texts)

        for doc_id, embedding in zip(doc_ids, embeddings):
            await self.service.add_to_index(doc_id, embedding)

        logger.info(f"Indexed {len(doc_ids)} documents")
        return len(doc_ids)

    async def search_similar(
        self,
        query: str,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """搜索相似文档"""
        query_embedding = await self.service.encode_single(query)

        results = await self.service.search_similar(query_embedding, top_k)

        doc_ids = [r[0] for r in results]
        scores = [r[1] for r in results]

        if doc_ids:
            records = await self.db.get_by_ids(doc_ids)
            records_map = {r.id: r for r in records}

            return [
                {
                    "id": doc_id,
                    "score": score,
                    "title": records_map.get(doc_id, {}).get("title", ""),
                    "content": records_map.get(doc_id, {}).get("content", "")[:500]
                }
                for doc_id, score in zip(doc_ids, scores)
                if doc_id in records_map
            ]

        return []

    async def cross_modal_search(
        self,
        text_query: str = None,
        image_url: str = None,
        modality: str = "text",
        top_k: int = 5
    ) -> List[Dict]:
        """跨模态检索"""
        if modality == "text" and text_query:
            return await self.search_similar(text_query, top_k)

        elif modality == "image" and image_url:
            logger.warning("Image embedding not fully implemented, using text fallback")
            return []

        elif modality == "hybrid" and text_query and image_url:
            text_results = await self.search_similar(text_query, top_k * 2)
            return text_results[:top_k]

        return []


embedding_service = EmbeddingServiceWrapper()
