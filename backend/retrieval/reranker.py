"""重排序模块 - Cross-Encoder精排"""
from typing import List, Dict, Any, Tuple
import numpy as np
import logging
import time

from ..config import settings
from ..retrieval.hybrid import RetrievalResult

logger = logging.getLogger(__name__)


class CrossEncoderReranker:
    """Cross-Encoder重排序器"""

    def __init__(self, model_name: str = None):
        self.model_name = model_name or settings.RERANKER_MODEL
        self.model = None
        self._initialized = False

    async def init(self):
        """初始化模型"""
        if self._initialized:
            return

        try:
            from sentence_transformers import CrossEncoder
            self.model = CrossEncoder(self.model_name)
            logger.info(f"Reranker model loaded: {self.model_name}")
            self._initialized = True
        except Exception as e:
            logger.warning(f"Failed to load reranker model: {e}, using mock mode")
            self._initialized = True

    async def rerank(
        self,
        query: str,
        results: List[RetrievalResult],
        top_k: int = None
    ) -> List[RetrievalResult]:
        """执行重排序"""
        if not results:
            return []

        if not self._initialized:
            await self.init()

        top_k = top_k or len(results)

        if self.model:
            pairs = [(query, f"{r.title} {r.content[:500]}") for r in results]
            scores = self.model.predict(pairs)

            sorted_indices = np.argsort(scores)[::-1][:top_k]
            reranked = [results[i] for i in sorted_indices]

            for i, idx in enumerate(sorted_indices):
                reranked[i].score = float(scores[idx])
        else:
            reranked = sorted(results, key=lambda x: x.score, reverse=True)[:top_k]

        return reranked


class MultiStageRanker:
    """多阶段排序器"""

    def __init__(self):
        self.reranker = CrossEncoderReranker()

    async def init(self):
        """初始化"""
        await self.reranker.init()

    async def rank(
        self,
        query: str,
        candidates: List[RetrievalResult],
        top_k: int = 5,
        stages: List[str] = None
    ) -> List[RetrievalResult]:
        """多阶段排序"""
        stages = stages or ["rerank", "diversity", "freshness"]

        if not candidates:
            return []

        results = candidates.copy()

        if "rerank" in stages:
            results = await self.reranker.rerank(query, results, top_k * 2)

        if "diversity" in stages:
            results = self._diversity_rerank(results, top_k * 2)

        if "freshness" in stages:
            results = self._freshness_adjust(results)

        return results[:top_k]

    def _diversity_rerank(
        self,
        results: List[RetrievalResult],
        top_k: int
    ) -> List[RetrievalResult]:
        """多样性重排 - MMR算法"""
        if len(results) <= top_k:
            return results

        selected = [results[0]]
        remaining = results[1:]

        while len(selected) < top_k and remaining:
            best_idx = 0
            best_score = -1

            for i, candidate in enumerate(remaining):
                max_sim = max(
                    self._text_similarity(candidate.content, s.content)
                    for s in selected
                )
                mmr_score = 0.7 * candidate.score - 0.3 * max_sim

                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = i

            selected.append(remaining[best_idx])
            remaining.pop(best_idx)

        return selected

    def _freshness_adjust(
        self,
        results: List[RetrievalResult]
    ) -> List[RetrievalResult]:
        """新鲜度调整"""
        now = time.time()

        for r in results:
            if r.publish_time:
                age_hours = (now - r.publish_time.timestamp()) / 3600
                freshness_factor = max(0.5, 1.0 - age_hours / 168)
                r.score *= freshness_factor

        return sorted(results, key=lambda x: x.score, reverse=True)

    def _text_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0.0


class RelevanceScorer:
    """相关度评分器"""

    def __init__(self):
        self.weights = {
            "semantic": 0.4,
            "keyword": 0.25,
            "freshness": 0.15,
            "source_quality": 0.1,
            "engagement": 0.1
        }

    def score(
        self,
        result: RetrievalResult,
        query: str,
        context: Dict[str, Any] = None
    ) -> float:
        """计算综合相关度分数"""
        scores = {}

        scores["semantic"] = result.score

        scores["keyword"] = self._keyword_match_score(query, result.title, result.content)

        scores["freshness"] = self._freshness_score(result.publish_time)

        scores["source_quality"] = self._source_quality_score(result.source)

        scores["engagement"] = 0.5

        final_score = sum(
            scores[k] * self.weights[k]
            for k in self.weights
        )

        return min(1.0, final_score)

    def _keyword_match_score(self, query: str, title: str, content: str) -> float:
        """关键词匹配分数"""
        query_words = set(query.lower().split())
        text_words = set((title + " " + content).lower().split())

        if not query_words:
            return 0.0

        matches = len(query_words & text_words)
        return matches / len(query_words)

    def _freshness_score(self, publish_time) -> float:
        """新鲜度分数"""
        if not publish_time:
            return 0.5

        now = time.time()
        pub_timestamp = publish_time.timestamp() if hasattr(publish_time, 'timestamp') else now
        age_hours = (now - pub_timestamp) / 3600

        if age_hours < 24:
            return 1.0
        elif age_hours < 72:
            return 0.8
        elif age_hours < 168:
            return 0.6
        else:
            return max(0.3, 1.0 - age_hours / 720)

    def _source_quality_score(self, source: str) -> float:
        """来源质量分数"""
        quality_map = {
            "news": 0.9,
            "wechat": 0.8,
            "weibo": 0.7,
            "social": 0.6,
            "forum": 0.5
        }
        return quality_map.get(source, 0.5)


ranker = MultiStageRanker()
scorer = RelevanceScorer()
