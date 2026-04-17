"""Redis短期缓存实现"""
import redis.asyncio as redis
from typing import Any, Optional, Dict, List
import json
import logging
from datetime import timedelta
import hashlib

from ..config import settings

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis缓存管理器"""

    def __init__(self):
        self.client: Optional[redis.Redis] = None
        self.prefix = "yuqing:cache:"
        self.default_ttl = settings.CACHE_TTL_SHORT

    async def init(self):
        """初始化Redis连接"""
        try:
            self.client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            await self.client.ping()
            logger.info("Redis cache initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Redis: {e}")
            self.client = None

    async def close(self):
        """关闭连接"""
        if self.client:
            await self.client.close()

    def _make_key(self, key: str) -> str:
        """生成缓存键"""
        return f"{self.prefix}{key}"

    async def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        if not self.client:
            return None

        try:
            cache_key = self._make_key(key)
            data = await self.client.get(cache_key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.warning(f"Cache get failed for {key}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """设置缓存"""
        if not self.client:
            return False

        try:
            cache_key = self._make_key(key)
            ttl = ttl or self.default_ttl
            data = json.dumps(value, ensure_ascii=False, default=str)
            await self.client.setex(cache_key, ttl, data)
            return True
        except Exception as e:
            logger.warning(f"Cache set failed for {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """删除缓存"""
        if not self.client:
            return False

        try:
            cache_key = self._make_key(key)
            await self.client.delete(cache_key)
            return True
        except Exception as e:
            logger.warning(f"Cache delete failed for {key}: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        if not self.client:
            return False

        try:
            cache_key = self._make_key(key)
            return await self.client.exists(cache_key) > 0
        except Exception as e:
            logger.warning(f"Cache exists check failed for {key}: {e}")
            return False

    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """计数器增加"""
        if not self.client:
            return None

        try:
            cache_key = self._make_key(key)
            return await self.client.incrby(cache_key, amount)
        except Exception as e:
            logger.warning(f"Cache increment failed for {key}: {e}")
            return None

    async def get_ttl(self, key: str) -> int:
        """获取缓存剩余时间"""
        if not self.client:
            return -1

        try:
            cache_key = self._make_key(key)
            return await self.client.ttl(cache_key)
        except Exception as e:
            logger.warning(f"Get TTL failed for {key}: {e}")
            return -1

    async def clear_pattern(self, pattern: str) -> int:
        """清除匹配模式的所有缓存"""
        if not self.client:
            return 0

        try:
            keys = await self.client.keys(f"{self.prefix}{pattern}*")
            if keys:
                return await self.client.delete(*keys)
            return 0
        except Exception as e:
            logger.warning(f"Clear pattern failed for {pattern}: {e}")
            return 0


class HotTopicCache:
    """热点话题缓存管理"""

    def __init__(self, redis_cache: RedisCache):
        self.cache = redis_cache
        self.access_counter_prefix = "access:"
        self.hot_threshold = settings.HOT_TOPIC_THRESHOLD

    async def record_access(self, topic: str) -> int:
        """记录话题访问"""
        key = f"{self.access_counter_prefix}{topic}"
        count = await self.cache.increment(key)
        if count and count == self.hot_threshold:
            await self._mark_as_hot(topic)
        return count or 0

    async def get_access_count(self, topic: str) -> int:
        """获取访问计数"""
        key = f"{self.access_counter_prefix}{topic}"
        data = await self.cache.get(key)
        return int(data) if data else 0

    async def _mark_as_hot(self, topic: str):
        """标记为热点"""
        hot_key = "hot_topics:set"
        if self.cache.client:
            await self.cache.client.sadd(hot_key, topic)
            logger.info(f"Topic marked as hot: {topic}")

    async def get_hot_topics(self) -> List[str]:
        """获取热点话题列表"""
        hot_key = "hot_topics:set"
        if self.cache.client:
            members = await self.cache.client.smembers(hot_key)
            return list(members)
        return []

    async def cache_hot_query(self, query: str, results: Any, ttl: int = None):
        """缓存热点查询结果"""
        query_hash = hashlib.md5(query.encode()).hexdigest()
        key = f"hot_query:{query_hash}"
        ttl = ttl or settings.CACHE_TTL_LONG
        await self.cache.set(key, results, ttl)

    async def get_hot_query(self, query: str) -> Optional[Any]:
        """获取热点查询缓存"""
        query_hash = hashlib.md5(query.encode()).hexdigest()
        key = f"hot_query:{query_hash}"
        return await self.cache.get(key)


class SessionCache:
    """会话缓存管理"""

    def __init__(self, redis_cache: RedisCache):
        self.cache = redis_cache
        self.session_prefix = "session:"
        self.session_ttl = 3600

    async def create_session(self, session_id: str, data: Dict) -> bool:
        """创建会话"""
        key = f"{self.session_prefix}{session_id}"
        return await self.cache.set(key, data, self.session_ttl)

    async def get_session(self, session_id: str) -> Optional[Dict]:
        """获取会话"""
        key = f"{self.session_prefix}{session_id}"
        return await self.cache.get(key)

    async def update_session(self, session_id: str, data: Dict) -> bool:
        """更新会话"""
        existing = await self.get_session(session_id)
        if existing:
            existing.update(data)
            return await self.create_session(session_id, existing)
        return False

    async def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        key = f"{self.session_prefix}{session_id}"
        return await self.cache.delete(key)


cache = RedisCache()
