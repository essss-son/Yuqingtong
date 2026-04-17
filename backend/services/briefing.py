"""舆情简报生成服务"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging
import asyncio

from ..models.schemas import (
    Briefing, BriefingRequest, BriefingSection,
    SentimentType, SourceType, YuqingItem
)
from ..memory import db, cache
from ..agents import briefing_agent
from ..retrieval import retriever

logger = logging.getLogger(__name__)


class BriefingService:
    """简报生成服务"""

    def __init__(self):
        self.db = db
        self.cache = cache

    async def generate(self, request: BriefingRequest) -> Briefing:
        """生成舆情简报"""
        logger.info(f"Generating briefing for topic: {request.topic}")

        start_time = datetime.now() - timedelta(hours=request.time_range)

        records = await self.db.search_yuqing(
            query=request.topic,
            start_time=start_time,
            limit=request.max_items
        )

        if not records:
            return Briefing(
                topic=request.topic,
                time_range=request.time_range,
                summary="未找到相关舆情数据",
                sections=[]
            )

        items = [
            YuqingItem(
                id=r.id,
                title=r.title,
                content=r.content,
                source=r.source,
                source_url=r.source_url,
                author=r.author,
                publish_time=r.publish_time,
                crawl_time=r.crawl_time,
                sentiment=r.sentiment,
                keywords=r.keywords or [],
                images=r.images or []
            )
            for r in records
        ]

        summary = await self._generate_summary(items, request.topic)

        sections = await self._generate_sections(items, request.topic, request)

        sentiment_dist = {}
        if request.include_sentiment:
            sentiment_dist = await self._analyze_sentiment(items)

        hot_keywords = await self._extract_keywords(items)

        trend_data = None
        if request.include_trend:
            trend_data = await self._analyze_trend(items)

        source_dist = self._analyze_sources(items)

        briefing = Briefing(
            topic=request.topic,
            time_range=request.time_range,
            summary=summary,
            sections=sections,
            sentiment_distribution=sentiment_dist,
            hot_keywords=hot_keywords,
            trend_data=trend_data,
            source_distribution=source_dist
        )

        await self._save_briefing(briefing)

        return briefing

    async def _generate_summary(
        self,
        items: List[YuqingItem],
        topic: str
    ) -> str:
        """生成摘要"""
        if not items:
            return "暂无相关数据"

        total = len(items)
        sources = set(item.source.value for item in items)
        time_span = "24小时内"

        if items:
            dates = [item.publish_time for item in items if item.publish_time]
            if dates:
                latest = max(dates)
                earliest = min(dates)
                if latest and earliest:
                    hours = (latest - earliest).total_seconds() / 3600
                    if hours > 24:
                        time_span = f"{int(hours/24)}天内"

        positive = sum(1 for item in items if item.sentiment == SentimentType.POSITIVE)
        negative = sum(1 for item in items if item.sentiment == SentimentType.NEGATIVE)

        summary = f"关于「{topic}」的舆情监测，共收集到{total}条相关信息，" \
                  f"来源于{len(sources)}个渠道，时间跨度为{time_span}。" \
                  f"情感分布方面，正面信息{positive}条，负面信息{negative}条，" \
                  f"其余为中性信息。"

        return summary

    async def _generate_sections(
        self,
        items: List[YuqingItem],
        topic: str,
        request: BriefingRequest
    ) -> List[BriefingSection]:
        """生成简报章节"""
        sections = []

        key_events = await self._extract_key_events(items)
        if key_events:
            sections.append(BriefingSection(
                title="关键事件",
                content="舆情发展中的关键事件节点：",
                items=key_events[:5]
            ))

        hot_items = sorted(
            items,
            key=lambda x: len(x.keywords) if x.keywords else 0,
            reverse=True
        )[:5]
        if hot_items:
            sections.append(BriefingSection(
                title="热点内容",
                content="热度较高的相关内容：",
                items=hot_items
            ))

        negative_items = [item for item in items if item.sentiment == SentimentType.NEGATIVE]
        if negative_items:
            sections.append(BriefingSection(
                title="负面舆情",
                content="需要关注的负面舆情：",
                items=negative_items[:3]
            ))

        return sections

    async def _extract_key_events(
        self,
        items: List[YuqingItem]
    ) -> List[YuqingItem]:
        """提取关键事件"""
        sorted_items = sorted(
            items,
            key=lambda x: x.publish_time if x.publish_time else datetime.min,
            reverse=True
        )
        return sorted_items[:10]

    async def _analyze_sentiment(
        self,
        items: List[YuqingItem]
    ) -> Dict[SentimentType, int]:
        """情感分析统计"""
        distribution = {
            SentimentType.POSITIVE: 0,
            SentimentType.NEGATIVE: 0,
            SentimentType.NEUTRAL: 0
        }

        for item in items:
            if item.sentiment:
                distribution[item.sentiment] = distribution.get(item.sentiment, 0) + 1
            else:
                distribution[SentimentType.NEUTRAL] += 1

        return distribution

    async def _extract_keywords(
        self,
        items: List[YuqingItem]
    ) -> List[str]:
        """提取关键词"""
        keyword_count = {}

        for item in items:
            if item.keywords:
                for kw in item.keywords:
                    keyword_count[kw] = keyword_count.get(kw, 0) + 1

        sorted_keywords = sorted(
            keyword_count.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return [kw for kw, _ in sorted_keywords[:20]]

    async def _analyze_trend(
        self,
        items: List[YuqingItem]
    ) -> Dict[str, Any]:
        """分析趋势"""
        hourly_count = {}

        for item in items:
            if item.publish_time:
                hour_key = item.publish_time.strftime("%Y-%m-%d %H:00")
                hourly_count[hour_key] = hourly_count.get(hour_key, 0) + 1

        sorted_hours = sorted(hourly_count.items())

        return {
            "timeline": [
                {"time": h, "count": c}
                for h, c in sorted_hours
            ],
            "peak_hour": max(hourly_count.items(), key=lambda x: x[1])[0] if hourly_count else None,
            "total_items": len(items)
        }

    def _analyze_sources(
        self,
        items: List[YuqingItem]
    ) -> Dict[SourceType, int]:
        """分析来源分布"""
        distribution = {}

        for item in items:
            if item.source:
                distribution[item.source] = distribution.get(item.source, 0) + 1

        return distribution

    async def _save_briefing(self, briefing: Briefing) -> int:
        """保存简报"""
        briefing_data = {
            "topic": briefing.topic,
            "time_range": briefing.time_range,
            "summary": briefing.summary,
            "sections": [s.model_dump() for s in briefing.sections],
            "sentiment_distribution": {k.value: v for k, v in briefing.sentiment_distribution.items()},
            "hot_keywords": briefing.hot_keywords,
            "trend_data": briefing.trend_data,
            "source_distribution": {k.value: v for k, v in briefing.source_distribution.items()}
        }

        return await self.db.save_briefing(briefing_data)

    async def get_history(self, limit: int = 20) -> List[Briefing]:
        """获取历史简报"""
        records = await self.db.get_briefings(limit=limit)

        return [
            Briefing(
                id=r.id,
                topic=r.topic,
                generated_at=r.generated_at,
                time_range=r.time_range,
                summary=r.summary,
                sections=r.sections or [],
                hot_keywords=r.hot_keywords or []
            )
            for r in records
        ]


briefing_service = BriefingService()
