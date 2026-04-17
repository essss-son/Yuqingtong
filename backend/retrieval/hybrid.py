"""混合检索系统 - Hybrid Retrieval实现"""
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import faiss
import logging
import asyncio
from datetime import datetime, timedelta
from dataclasses import dataclass
import hashlib

from ..config import settings
from ..memory import db, cache
from ..models.schemas import YuqingItem, SourceType, SentimentType

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """检索结果"""
    id: int
    title: str
    content: str
    score: float
    source: str
    publish_time: datetime
    metadata: Dict[str, Any] = None


class EmbeddingService:
    """嵌入向量服务"""

    def __init__(self):
        self.model = None
        self.dimension = settings.EMBEDDING_DIM
        self.index: Optional[faiss.IndexFlatIP] = None
        self.id_mapping: Dict[int, int] = {}
        self._initialized = False

    async def init(self):
        """初始化嵌入模型"""
        if self._initialized:
            return

        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(settings.EMBEDDING_MODEL)
            self.dimension = self.model.get_sentence_embedding_dimension()

            self.index = faiss.IndexFlatIP(self.dimension)
            logger.info(f"Embedding model loaded: {settings.EMBEDDING_MODEL}, dim={self.dimension}")
            self._initialized = True
        except Exception as e:
            logger.warning(f"Failed to load embedding model: {e}, using mock mode")
            self._initialized = True

    async def encode(self, texts: List[str]) -> np.ndarray:
        """编码文本为向量"""
        if not self._initialized:
            await self.init()

        if self.model:
            embeddings = self.model.encode(texts, convert_to_numpy=True)
            faiss.normalize_L2(embeddings)
            return embeddings
        else:
            return np.random.randn(len(texts), self.dimension).astype(np.float32)

    async def encode_single(self, text: str) -> np.ndarray:
        """编码单个文本"""
        embeddings = await self.encode([text])
        return embeddings[0]

    async def add_to_index(self, doc_id: int, embedding: np.ndarray):
        """添加向量到索引"""
        if self.index is not None:
            idx = self.index.ntotal
            self.index.add(embedding.reshape(1, -1))
            self.id_mapping[idx] = doc_id

    async def search_similar(
        self,
        query_embedding: np.ndarray,
        top_k: int = 20
    ) -> List[Tuple[int, float]]:
        """搜索相似向量"""
        if self.index is None or self.index.ntotal == 0:
            return []

        query_embedding = query_embedding.reshape(1, -1)
        faiss.normalize_L2(query_embedding)

        scores, indices = self.index.search(query_embedding, min(top_k, self.index.ntotal))

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0 and idx in self.id_mapping:
                results.append((self.id_mapping[idx], float(score)))

        return results


class QueryExpander:
    """查询扩展器"""

    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self.synonyms_cache = {}

    async def expand(self, query: str, num_expansions: int = 3) -> List[str]:
        """扩展查询，生成多个相关查询"""
        expansions = [query]

        if self.llm_client:
            try:
                prompt = f"""请为以下查询生成{num_expansions}个语义相关但表达不同的查询变体。
每个变体应该从不同角度描述相同的信息需求。

原查询：{query}

请直接输出变体查询，每行一个，不要编号。"""

                response = await self.llm_client.generate(prompt)
                variants = [line.strip() for line in response.split("\n") if line.strip()]
                expansions.extend(variants[:num_expansions])
            except Exception as e:
                logger.warning(f"Query expansion failed: {e}")

        expansions.extend(self._rule_based_expansion(query))
        return list(set(expansions))[:num_expansions + 1]

    def _rule_based_expansion(self, query: str) -> List[str]:
        """基于规则的查询扩展"""
        expansions = []

        synonyms = {
            "问题": ["事件", "情况", "现象"],
            "影响": ["后果", "结果", "效果"],
            "原因": ["起因", "缘由", "因素"],
            "发展": ["进展", "动态", "趋势"],
            "最新": ["近期", "当前", "今天"],
        }

        for word, syns in synonyms.items():
            if word in query:
                for syn in syns:
                    expansions.append(query.replace(word, syn))

        return expansions


class HyDEGenerator:
    """Hypothetical Document Embeddings生成器"""

    def __init__(self, llm_client=None, embedding_service: EmbeddingService = None):
        self.llm_client = llm_client
        self.embedding_service = embedding_service

    async def generate_hypothetical_doc(self, query: str) -> str:
        """生成假设文档"""
        if not self.llm_client:
            return query

        try:
            prompt = f"""请根据以下查询，生成一段可能包含答案的假设性新闻内容。
内容应该是客观、中立的新闻报道风格，大约200字。

查询：{query}

假设内容："""

            response = await self.llm_client.generate(prompt)
            return response.strip()
        except Exception as e:
            logger.warning(f"HyDE generation failed: {e}")
            return query

    async def get_hyde_embedding(self, query: str) -> np.ndarray:
        """获取HyDE嵌入"""
        hyp_doc = await self.generate_hypothetical_doc(query)
        return await self.embedding_service.encode_single(hyp_doc)


class KnowledgeGraphRetriever:
    """知识图谱检索器"""

    def __init__(self):
        self.entity_relations: Dict[str, List[str]] = {}
        self._initialized = False

    async def init(self):
        """初始化知识图谱"""
        self.entity_relations = {
            "舆情": ["热点", "事件", "话题", "传播"],
            "传播": ["媒体", "社交", "论坛", "新闻"],
            "情感": ["正面", "负面", "中性", "态度"],
            "事件": ["时间", "地点", "人物", "影响"],
        }
        self._initialized = True

    async def get_related_entities(self, entity: str, depth: int = 1) -> List[str]:
        """获取相关实体"""
        if not self._initialized:
            await self.init()

        related = []
        to_visit = [entity]
        visited = set()

        for _ in range(depth):
            new_nodes = []
            for node in to_visit:
                if node in visited:
                    continue
                visited.add(node)
                relations = self.entity_relations.get(node, [])
                related.extend(relations)
                new_nodes.extend(relations)
            to_visit = new_nodes

        return list(set(related))


class HybridRetriever:
    """混合检索器"""

    def __init__(self, embedding_service: EmbeddingService = None):
        self.embedding_service = embedding_service or EmbeddingService()
        self.query_expander = QueryExpander()
        self.hyde_generator = HyDEGenerator(embedding_service=self.embedding_service)
        self.kg_retriever = KnowledgeGraphRetriever()
        self.db = db

    async def init(self):
        """初始化"""
        await self.embedding_service.init()
        await self.kg_retriever.init()

    async def search(
        self,
        query: str,
        top_k: int = 5,
        sources: List[SourceType] = None,
        time_range: int = None,
        use_expansion: bool = True,
        use_hyde: bool = True,
        use_kg: bool = True
    ) -> List[RetrievalResult]:
        """执行混合检索"""

        queries = [query]
        if use_expansion:
            expansions = await self.query_expander.expand(query, num_expansions=2)
            queries.extend(expansions)

        all_results = []
        seen_ids = set()

        for q in queries:
            results = await self._single_search(
                query=q,
                top_k=top_k * 2,
                sources=sources,
                time_range=time_range,
                use_hyde=use_hyde,
                use_kg=use_kg
            )
            for r in results:
                if r.id not in seen_ids:
                    all_results.append(r)
                    seen_ids.add(r.id)

        all_results.sort(key=lambda x: x.score, reverse=True)
        return all_results[:top_k]

    async def _single_search(
        self,
        query: str,
        top_k: int,
        sources: List[SourceType] = None,
        time_range: int = None,
        use_hyde: bool = True,
        use_kg: bool = True
    ) -> List[RetrievalResult]:
        """单次检索"""

        query_embedding = await self.embedding_service.encode_single(query)
        semantic_results = await self.embedding_service.search_similar(query_embedding, top_k)

        hyde_embedding = None
        if use_hyde:
            hyde_embedding = await self.hyde_generator.get_hyde_embedding(query)
            hyde_results = await self.embedding_service.search_similar(hyde_embedding, top_k)
            semantic_results.extend(hyde_results)

        kg_entities = []
        if use_kg:
            query_words = query.split()
            for word in query_words:
                entities = await self.kg_retriever.get_related_entities(word)
                kg_entities.extend(entities)

        keyword_results = await self._keyword_search(
            keywords=[query] + kg_entities,
            sources=sources,
            time_range=time_range,
            limit=top_k
        )

        combined = self._combine_results(
            semantic_results=semantic_results,
            keyword_results=keyword_results,
            top_k=top_k
        )

        return combined

    async def _keyword_search(
        self,
        keywords: List[str],
        sources: List[SourceType] = None,
        time_range: int = None,
        limit: int = 20
    ) -> List[RetrievalResult]:
        """关键词检索"""
        start_time = None
        if time_range:
            start_time = datetime.now() - timedelta(hours=time_range)

        records = await self.db.search_yuqing(
            keywords=keywords,
            sources=sources,
            start_time=start_time,
            limit=limit
        )

        results = []
        for r in records:
            score = self._calculate_keyword_score(keywords, r.title, r.content)
            results.append(RetrievalResult(
                id=r.id,
                title=r.title,
                content=r.content,
                score=score,
                source=r.source.value if r.source else "unknown",
                publish_time=r.publish_time,
                metadata={
                    "source_url": r.source_url,
                    "sentiment": r.sentiment.value if r.sentiment else None
                }
            ))

        return results

    def _calculate_keyword_score(self, keywords: List[str], title: str, content: str) -> float:
        """计算关键词匹配分数"""
        text = (title + " " + content).lower()
        matches = sum(1 for kw in keywords if kw.lower() in text)
        return matches / len(keywords) if keywords else 0.0

    def _combine_results(
        self,
        semantic_results: List[Tuple[int, float]],
        keyword_results: List[RetrievalResult],
        top_k: int
    ) -> List[RetrievalResult]:
        """融合语义检索和关键词检索结果"""

        combined_scores: Dict[int, float] = {}

        for doc_id, score in semantic_results:
            combined_scores[doc_id] = combined_scores.get(doc_id, 0) + score * 0.6

        for result in keyword_results:
            combined_scores[result.id] = combined_scores.get(result.id, 0) + result.score * 0.4

        sorted_ids = sorted(combined_scores.keys(), key=lambda x: combined_scores[x], reverse=True)[:top_k]

        results_map = {r.id: r for r in keyword_results}

        final_results = []
        for doc_id in sorted_ids:
            if doc_id in results_map:
                result = results_map[doc_id]
                result.score = combined_scores[doc_id]
                final_results.append(result)

        return final_results


retriever = HybridRetriever()
