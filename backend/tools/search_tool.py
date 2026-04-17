"""检索工具封装"""
from .base import BaseTool, ToolResult, register_tool
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


@register_tool
class SearchTool(BaseTool):
    """语义检索工具"""

    name = "semantic_search"
    description = "在舆情数据库中进行语义检索，返回相关舆情条目"
    parameters_schema = {
        "query": {
            "type": "string",
            "description": "搜索查询文本",
            "required": True
        },
        "top_k": {
            "type": "integer",
            "description": "返回结果数量，默认5",
            "default": 5
        },
        "sources": {
            "type": "array",
            "items": {"type": "string"},
            "description": "限定数据源类型"
        },
        "time_range": {
            "type": "integer",
            "description": "时间范围（小时）"
        }
    }

    def __init__(self):
        super().__init__()
        self._retriever = None

    def set_retriever(self, retriever):
        """设置检索器"""
        self._retriever = retriever

    async def execute(self, **kwargs) -> ToolResult:
        """执行检索"""
        if not self._retriever:
            return ToolResult(
                success=False,
                error="检索器未初始化"
            )

        query = kwargs.get("query", "")
        top_k = kwargs.get("top_k", 5)
        sources = kwargs.get("sources")
        time_range = kwargs.get("time_range")

        try:
            results = await self._retriever.search(
                query=query,
                top_k=top_k,
                sources=sources,
                time_range=time_range
            )

            return ToolResult(
                success=True,
                data={
                    "query": query,
                    "results": results,
                    "total": len(results)
                }
            )

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return ToolResult(success=False, error=str(e))


@register_tool
class KeywordSearchTool(BaseTool):
    """关键词检索工具"""

    name = "keyword_search"
    description = "基于关键词匹配进行检索，支持布尔查询"
    parameters_schema = {
        "keywords": {
            "type": "array",
            "items": {"type": "string"},
            "description": "关键词列表",
            "required": True
        },
        "operator": {
            "type": "string",
            "enum": ["AND", "OR"],
            "description": "逻辑操作符",
            "default": "OR"
        },
        "top_k": {
            "type": "integer",
            "description": "返回结果数量",
            "default": 10
        }
    }

    def __init__(self):
        super().__init__()
        self._db_client = None

    def set_db_client(self, client):
        """设置数据库客户端"""
        self._db_client = client

    async def execute(self, **kwargs) -> ToolResult:
        """执行关键词检索"""
        if not self._db_client:
            return ToolResult(success=False, error="数据库客户端未初始化")

        keywords = kwargs.get("keywords", [])
        operator = kwargs.get("operator", "OR")
        top_k = kwargs.get("top_k", 10)

        try:
            results = await self._db_client.keyword_search(
                keywords=keywords,
                operator=operator,
                limit=top_k
            )

            return ToolResult(
                success=True,
                data={
                    "keywords": keywords,
                    "operator": operator,
                    "results": results,
                    "total": len(results)
                }
            )

        except Exception as e:
            logger.error(f"Keyword search failed: {e}")
            return ToolResult(success=False, error=str(e))


@register_tool
class MultiModalSearchTool(BaseTool):
    """多模态检索工具"""

    name = "multimodal_search"
    description = "支持文本和图像的跨模态检索"
    parameters_schema = {
        "query": {
            "type": "string",
            "description": "文本查询"
        },
        "image_url": {
            "type": "string",
            "description": "图像URL（可选）"
        },
        "modality": {
            "type": "string",
            "enum": ["text", "image", "hybrid"],
            "description": "检索模态",
            "default": "text"
        },
        "top_k": {
            "type": "integer",
            "description": "返回结果数量",
            "default": 5
        }
    }

    def __init__(self):
        super().__init__()
        self._embedding_service = None

    def set_embedding_service(self, service):
        """设置嵌入服务"""
        self._embedding_service = service

    async def execute(self, **kwargs) -> ToolResult:
        """执行多模态检索"""
        if not self._embedding_service:
            return ToolResult(success=False, error="嵌入服务未初始化")

        query = kwargs.get("query", "")
        image_url = kwargs.get("image_url")
        modality = kwargs.get("modality", "text")
        top_k = kwargs.get("top_k", 5)

        try:
            results = await self._embedding_service.cross_modal_search(
                text_query=query,
                image_url=image_url,
                modality=modality,
                top_k=top_k
            )

            return ToolResult(
                success=True,
                data={
                    "modality": modality,
                    "results": results,
                    "total": len(results)
                }
            )

        except Exception as e:
            logger.error(f"Multi-modal search failed: {e}")
            return ToolResult(success=False, error=str(e))
