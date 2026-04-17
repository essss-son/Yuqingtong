"""长期数据库存储实现"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, JSON, Enum, Index
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import select, delete, update, func
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging
import asyncio

from ..config import settings
from ..models.schemas import SentimentType, SourceType

logger = logging.getLogger(__name__)

Base = declarative_base()


class YuqingRecord(Base):
    """舆情记录表"""
    __tablename__ = "yuqing_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=False, index=True)
    content = Column(Text, nullable=False)
    source = Column(Enum(SourceType), nullable=False, index=True)
    source_url = Column(String(1000), unique=True, nullable=False)
    author = Column(String(200))
    publish_time = Column(DateTime, index=True)
    crawl_time = Column(DateTime, default=datetime.now, index=True)
    sentiment = Column(Enum(SentimentType))
    keywords = Column(JSON, default=list)
    images = Column(JSON, default=list)
    embedding_id = Column(String(100))

    __table_args__ = (
        Index("idx_source_publish", "source", "publish_time"),
        Index("idx_crawl_time", "crawl_time"),
    )


class HotTopicRecord(Base):
    """热点话题表"""
    __tablename__ = "hot_topics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    keyword = Column(String(200), unique=True, nullable=False, index=True)
    frequency = Column(Integer, default=0)
    trend = Column(Float, default=0)
    first_seen = Column(DateTime, default=datetime.now)
    last_seen = Column(DateTime, default=datetime.now, index=True)
    access_count = Column(Integer, default=0)
    is_hot = Column(Integer, default=0)


class BriefingRecord(Base):
    """简报记录表"""
    __tablename__ = "briefings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    topic = Column(String(200), nullable=False, index=True)
    generated_at = Column(DateTime, default=datetime.now, index=True)
    time_range = Column(Integer)
    summary = Column(Text)
    sections = Column(JSON)
    sentiment_distribution = Column(JSON)
    hot_keywords = Column(JSON)
    trend_data = Column(JSON)
    source_distribution = Column(JSON)


class CrawlerTaskRecord(Base):
    """爬虫任务表"""
    __tablename__ = "crawler_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    source = Column(Enum(SourceType), nullable=False)
    keywords = Column(JSON)
    urls = Column(JSON)
    schedule = Column(String(100))
    enabled = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.now)
    last_run = Column(DateTime)
    run_count = Column(Integer, default=0)


class Database:
    """数据库管理器"""

    def __init__(self):
        self.engine = None
        self.session_maker = None

    async def init(self):
        """初始化数据库连接"""
        try:
            self.engine = create_async_engine(
                settings.DATABASE_URL,
                echo=settings.DEBUG,
                pool_size=10,
                max_overflow=20
            )
            self.session_maker = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )

            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    async def close(self):
        """关闭连接"""
        if self.engine:
            await self.engine.dispose()

    async def get_session(self) -> AsyncSession:
        """获取会话"""
        return self.session_maker()

    async def insert_yuqing(self, data: Dict[str, Any]) -> int:
        """插入舆情记录"""
        async with self.get_session() as session:
            record = YuqingRecord(**data)
            session.add(record)
            await session.commit()
            return record.id

    async def batch_insert_yuqing(self, items: List[Dict[str, Any]]) -> int:
        """批量插入舆情记录"""
        async with self.get_session() as session:
            records = [YuqingRecord(**item) for item in items]
            session.add_all(records)
            await session.commit()
            return len(records)

    async def search_yuqing(
        self,
        query: str = None,
        sources: List[SourceType] = None,
        start_time: datetime = None,
        end_time: datetime = None,
        keywords: List[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[YuqingRecord]:
        """搜索舆情记录"""
        async with self.get_session() as session:
            stmt = select(YuqingRecord)

            if sources:
                stmt = stmt.where(YuqingRecord.source.in_(sources))

            if start_time:
                stmt = stmt.where(YuqingRecord.publish_time >= start_time)

            if end_time:
                stmt = stmt.where(YuqingRecord.publish_time <= end_time)

            if query:
                stmt = stmt.where(
                    YuqingRecord.title.ilike(f"%{query}%") |
                    YuqingRecord.content.ilike(f"%{query}%")
                )

            stmt = stmt.order_by(YuqingRecord.publish_time.desc())
            stmt = stmt.limit(limit).offset(offset)

            result = await session.execute(stmt)
            return result.scalars().all()

    async def get_by_ids(self, ids: List[int]) -> List[YuqingRecord]:
        """根据ID列表获取记录"""
        async with self.get_session() as session:
            stmt = select(YuqingRecord).where(YuqingRecord.id.in_(ids))
            result = await session.execute(stmt)
            return result.scalars().all()

    async def update_embedding_id(self, record_id: int, embedding_id: str):
        """更新嵌入ID"""
        async with self.get_session() as session:
            stmt = (
                update(YuqingRecord)
                .where(YuqingRecord.id == record_id)
                .values(embedding_id=embedding_id)
            )
            await session.execute(stmt)
            await session.commit()

    async def keyword_search(
        self,
        keywords: List[str],
        operator: str = "OR",
        limit: int = 20
    ) -> List[YuqingRecord]:
        """关键词搜索"""
        async with self.get_session() as session:
            stmt = select(YuqingRecord)

            conditions = []
            for kw in keywords:
                conditions.append(
                    YuqingRecord.title.ilike(f"%{kw}%") |
                    YuqingRecord.content.ilike(f"%{kw}%")
                )

            if operator == "AND":
                stmt = stmt.where(*conditions)
            else:
                from sqlalchemy import or_
                stmt = stmt.where(or_(*conditions))

            stmt = stmt.order_by(YuqingRecord.publish_time.desc()).limit(limit)
            result = await session.execute(stmt)
            return result.scalars().all()

    async def get_sentiment_distribution(
        self,
        start_time: datetime = None,
        filters: Dict = None
    ) -> Dict[str, int]:
        """获取情感分布"""
        async with self.get_session() as session:
            stmt = select(
                YuqingRecord.sentiment,
                func.count(YuqingRecord.id)
            ).group_by(YuqingRecord.sentiment)

            if start_time:
                stmt = stmt.where(YuqingRecord.publish_time >= start_time)

            result = await session.execute(stmt)
            return {str(row[0]): row[1] for row in result if row[0]}

    async def get_hot_keywords(
        self,
        start_time: datetime = None,
        limit: int = 20
    ) -> List[Dict]:
        """获取热门关键词"""
        async with self.get_session() as session:
            stmt = select(YuqingRecord.keywords).where(
                YuqingRecord.keywords.isnot(None)
            )

            if start_time:
                stmt = stmt.where(YuqingRecord.publish_time >= start_time)

            result = await session.execute(stmt)
            all_keywords = []
            for row in result.scalars():
                if row:
                    all_keywords.extend(row)

            from collections import Counter
            counter = Counter(all_keywords)
            return [{"keyword": k, "count": c} for k, c in counter.most_common(limit)]

    async def get_source_distribution(
        self,
        start_time: datetime = None
    ) -> Dict[str, int]:
        """获取来源分布"""
        async with self.get_session() as session:
            stmt = select(
                YuqingRecord.source,
                func.count(YuqingRecord.id)
            ).group_by(YuqingRecord.source)

            if start_time:
                stmt = stmt.where(YuqingRecord.publish_time >= start_time)

            result = await session.execute(stmt)
            return {str(row[0]): row[1] for row in result}

    async def get_trend_data(
        self,
        start_time: datetime = None,
        interval: str = "hour"
    ) -> List[Dict]:
        """获取趋势数据"""
        async with self.get_session() as session:
            stmt = select(YuqingRecord.publish_time, YuqingRecord.sentiment)

            if start_time:
                stmt = stmt.where(YuqingRecord.publish_time >= start_time)

            stmt = stmt.order_by(YuqingRecord.publish_time)
            result = await session.execute(stmt)

            return [
                {
                    "time": row[0].isoformat(),
                    "sentiment": str(row[1]) if row[1] else "unknown"
                }
                for row in result
            ]

    async def save_briefing(self, briefing_data: Dict) -> int:
        """保存简报"""
        async with self.get_session() as session:
            record = BriefingRecord(**briefing_data)
            session.add(record)
            await session.commit()
            return record.id

    async def get_briefings(self, limit: int = 20) -> List[BriefingRecord]:
        """获取简报列表"""
        async with self.get_session() as session:
            stmt = select(BriefingRecord).order_by(
                BriefingRecord.generated_at.desc()
            ).limit(limit)
            result = await session.execute(stmt)
            return result.scalars().all()

    async def update_hot_topic(self, keyword: str, increment: int = 1):
        """更新热点话题"""
        async with self.get_session() as session:
            stmt = select(HotTopicRecord).where(
                HotTopicRecord.keyword == keyword
            )
            result = await session.execute(stmt)
            record = result.scalar_one_or_none()

            if record:
                record.frequency += increment
                record.last_seen = datetime.now()
                record.access_count += 1
                if record.frequency >= settings.HOT_TOPIC_THRESHOLD:
                    record.is_hot = 1
            else:
                record = HotTopicRecord(
                    keyword=keyword,
                    frequency=increment,
                    last_seen=datetime.now()
                )
                session.add(record)

            await session.commit()

    async def get_hot_topics(
        self,
        limit: int = 10,
        min_frequency: int = 5,
        time_range: int = 24
    ) -> List[Dict]:
        """获取热点话题"""
        async with self.get_session() as session:
            start_time = datetime.now() - timedelta(hours=time_range)
            stmt = select(HotTopicRecord).where(
                HotTopicRecord.frequency >= min_frequency,
                HotTopicRecord.last_seen >= start_time
            ).order_by(
                HotTopicRecord.frequency.desc()
            ).limit(limit)

            result = await session.execute(stmt)
            records = result.scalars().all()

            return [
                {
                    "keyword": r.keyword,
                    "frequency": r.frequency,
                    "trend": r.trend,
                    "is_hot": bool(r.is_hot)
                }
                for r in records
            ]

    async def query(
        self,
        table: str,
        filters: Dict = None,
        fields: List[str] = None,
        order_by: str = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict]:
        """通用查询"""
        table_map = {
            "yuqing": YuqingRecord,
            "hot_topics": HotTopicRecord,
            "briefings": BriefingRecord,
            "crawler_tasks": CrawlerTaskRecord
        }

        model = table_map.get(table)
        if not model:
            return []

        async with self.get_session() as session:
            stmt = select(model)

            if filters:
                for key, value in filters.items():
                    if hasattr(model, key):
                        stmt = stmt.where(getattr(model, key) == value)

            if order_by:
                parts = order_by.split()
                field = parts[0]
                direction = parts[1] if len(parts) > 1 else "ASC"
                if hasattr(model, field):
                    col = getattr(model, field)
                    if direction.upper() == "DESC":
                        stmt = stmt.order_by(col.desc())
                    else:
                        stmt = stmt.order_by(col)

            stmt = stmt.limit(limit).offset(offset)
            result = await session.execute(stmt)
            records = result.scalars().all()

            return [
                {c.name: getattr(r, c.name) for c in r.__table__.columns}
                for r in records
            ]


db = Database()
