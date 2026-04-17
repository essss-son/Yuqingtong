"""工具基类与标准化接口"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field
import time
import asyncio
from functools import wraps
import logging

logger = logging.getLogger(__name__)


class ToolResult(BaseModel):
    """工具执行结果"""
    success: bool = True
    data: Optional[Any] = None
    error: Optional[str] = None
    elapsed_time: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BaseTool(ABC):
    """工具基类"""

    name: str = "base_tool"
    description: str = "基础工具类"
    parameters_schema: Dict[str, Any] = {}

    def __init__(self):
        self._lock = asyncio.Lock()

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """执行工具逻辑"""
        pass

    def validate_parameters(self, **kwargs) -> bool:
        """校验参数"""
        return True

    def get_schema(self) -> Dict[str, Any]:
        """获取工具Schema（供LLM调用）"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": self.parameters_schema,
                "required": [k for k, v in self.parameters_schema.items()
                            if v.get("required", False)]
            }
        }

    async def __call__(self, **kwargs) -> ToolResult:
        """调用工具"""
        start_time = time.time()

        try:
            if not self.validate_parameters(**kwargs):
                return ToolResult(
                    success=False,
                    error="参数校验失败",
                    elapsed_time=time.time() - start_time
                )

            result = await self.execute(**kwargs)
            result.elapsed_time = time.time() - start_time
            logger.info(f"Tool {self.name} executed in {result.elapsed_time:.3f}s")
            return result

        except Exception as e:
            logger.error(f"Tool {self.name} failed: {str(e)}")
            return ToolResult(
                success=False,
                error=str(e),
                elapsed_time=time.time() - start_time
            )


class ToolRegistry:
    """工具注册中心"""

    _instance = None
    _tools: Dict[str, BaseTool] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def register(self, tool: BaseTool) -> None:
        """注册工具"""
        self._tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")

    def get(self, name: str) -> Optional[BaseTool]:
        """获取工具"""
        return self._tools.get(name)

    def list_tools(self) -> List[str]:
        """列出所有工具"""
        return list(self._tools.keys())

    def get_all_schemas(self) -> List[Dict[str, Any]]:
        """获取所有工具的Schema"""
        return [tool.get_schema() for tool in self._tools.values()]


tool_registry = ToolRegistry()


def register_tool(tool_class):
    """工具注册装饰器"""
    tool = tool_class()
    tool_registry.register(tool)
    return tool_class
