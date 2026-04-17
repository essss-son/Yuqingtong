"""数据库查询工具封装"""
from .base import BaseTool, ToolResult, register_tool
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


@register_tool
class DatabaseQueryTool(BaseTool):
    """数据库查询工具"""

    name = "database_query"
    description = "在舆情数据库中执行结构化查询"
    parameters_schema = {
        "table": {
            "type": "string",
            "description": "表名",
            "required": True
        },
        "filters": {
            "type": "object",
            "description": "过滤条件"
        },
        "fields": {
            "type": "array",
            "items": {"type": "string"},
            "description": "返回字段列表"
        },
        "order_by": {
            "type": "string",
            "description": "排序字段"
        },
        "limit": {
            "type": "integer",
            "description": "返回数量限制",
            "default": 20
        },
        "offset": {
            "type": "integer",
            "description": "偏移量",
            "default": 0
        }
    }

    def __init__(self):
        super().__init__()
        self._db_client = None

    def set_db_client(self, client):
        """设置数据库客户端"""
        self._db_client = client

    async def execute(self, **kwargs) -> ToolResult:
        """执行数据库查询"""
        if not self._db_client:
            return ToolResult(success=False, error="数据库客户端未初始化")

        table = kwargs.get("table")
        filters = kwargs.get("filters", {})
        fields = kwargs.get("fields")
        order_by = kwargs.get("order_by", "created_at DESC")
        limit = kwargs.get("limit", 20)
        offset = kwargs.get("offset", 0)

        try:
            results = await self._db_client.query(
                table=table,
                filters=filters,
                fields=fields,
                order_by=order_by,
                limit=limit,
                offset=offset
            )

            return ToolResult(
                success=True,
                data={
                    "table": table,
                    "results": results,
                    "count": len(results),
                    "limit": limit,
                    "offset": offset
                }
            )

        except Exception as e:
            logger.error(f"Database query failed: {e}")
            return ToolResult(success=False, error=str(e))


@register_tool
class StatisticsTool(BaseTool):
    """统计分析工具"""

    name = "get_statistics"
    description = "获取舆情统计数据，包括情感分布、热词、趋势等"
    parameters_schema = {
        "metric": {
            "type": "string",
            "enum": ["sentiment", "keywords", "sources", "trend"],
            "description": "统计指标类型",
            "required": True
        },
        "time_range": {
            "type": "integer",
            "description": "时间范围（小时）",
            "default": 24
        },
        "filters": {
            "type": "object",
            "description": "过滤条件"
        }
    }

    def __init__(self):
        super().__init__()
        self._db_client = None

    def set_db_client(self, client):
        """设置数据库客户端"""
        self._db_client = client

    async def execute(self, **kwargs) -> ToolResult:
        """执行统计分析"""
        if not self._db_client:
            return ToolResult(success=False, error="数据库客户端未初始化")

        metric = kwargs.get("metric")
        time_range = kwargs.get("time_range", 24)
        filters = kwargs.get("filters", {})

        try:
            start_time = datetime.now() - timedelta(hours=time_range)

            if metric == "sentiment":
                data = await self._db_client.get_sentiment_distribution(
                    start_time=start_time,
                    filters=filters
                )
            elif metric == "keywords":
                data = await self._db_client.get_hot_keywords(
                    start_time=start_time,
                    filters=filters
                )
            elif metric == "sources":
                data = await self._db_client.get_source_distribution(
                    start_time=start_time,
                    filters=filters
                )
            elif metric == "trend":
                data = await self._db_client.get_trend_data(
                    start_time=start_time,
                    filters=filters
                )
            else:
                return ToolResult(success=False, error=f"未知指标: {metric}")

            return ToolResult(
                success=True,
                data={
                    "metric": metric,
                    "time_range": time_range,
                    "data": data
                }
            )

        except Exception as e:
            logger.error(f"Statistics query failed: {e}")
            return ToolResult(success=False, error=str(e))


@register_tool
class HotTopicTool(BaseTool):
    """热点话题工具"""

    name = "get_hot_topics"
    description = "获取当前热点话题列表"
    parameters_schema = {
        "limit": {
            "type": "integer",
            "description": "返回数量",
            "default": 10
        },
        "min_frequency": {
            "type": "integer",
            "description": "最小出现频次",
            "default": 5
        },
        "time_range": {
            "type": "integer",
            "description": "时间范围（小时）",
            "default": 24
        }
    }

    def __init__(self):
        super().__init__()
        self._db_client = None
        self._cache = None

    def set_db_client(self, client):
        """设置数据库客户端"""
        self._db_client = client

    def set_cache(self, cache):
        """设置缓存"""
        self._cache = cache

    async def execute(self, **kwargs) -> ToolResult:
        """获取热点话题"""
        if not self._db_client:
            return ToolResult(success=False, error="数据库客户端未初始化")

        limit = kwargs.get("limit", 10)
        min_frequency = kwargs.get("min_frequency", 5)
        time_range = kwargs.get("time_range", 24)

        cache_key = f"hot_topics:{time_range}:{min_frequency}:{limit}"

        try:
            if self._cache:
                cached = await self._cache.get(cache_key)
                if cached:
                    return ToolResult(
                        success=True,
                        data=cached,
                        metadata={"from_cache": True}
                    )

            topics = await self._db_client.get_hot_topics(
                limit=limit,
                min_frequency=min_frequency,
                time_range=time_range
            )

            result_data = {
                "topics": topics,
                "time_range": time_range,
                "generated_at": datetime.now().isoformat()
            }

            if self._cache:
                await self._cache.set(cache_key, result_data, ttl=300)

            return ToolResult(
                success=True,
                data=result_data,
                metadata={"from_cache": False}
            )

        except Exception as e:
            logger.error(f"Get hot topics failed: {e}")
            return ToolResult(success=False, error=str(e))
