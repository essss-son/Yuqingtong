"""智能问答Agent系统"""
from typing import List, Dict, Any, Optional, Callable
from abc import ABC, abstractmethod
import json
import logging
import time
import uuid
from datetime import datetime

from ..config import settings
from ..models.schemas import (
    AgentMessage, AgentSession, ToolCallRequest, ToolCallResponse,
    SearchQuery, SearchResponse, YuqingItem
)
from ..tools import tool_registry
from ..memory import cache, db
from ..retrieval import retriever, ranker

logger = logging.getLogger(__name__)


class LLMClient:
    """LLM客户端封装"""

    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.api_base = settings.OPENAI_API_BASE
        self.model = settings.LLM_MODEL
        self._client = None

    async def init(self):
        """初始化客户端"""
        try:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.api_base
            )
            logger.info("LLM client initialized")
        except Exception as e:
            logger.warning(f"Failed to init LLM client: {e}")

    async def generate(
        self,
        messages: List[Dict],
        tools: List[Dict] = None,
        tool_choice: str = "auto"
    ) -> Dict:
        """生成回复"""
        if not self._client:
            return {"content": "LLM客户端未初始化", "tool_calls": None}

        try:
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.7,
            }

            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = tool_choice

            response = await self._client.chat.completions.create(**kwargs)

            message = response.choices[0].message

            result = {
                "content": message.content,
                "tool_calls": None
            }

            if message.tool_calls:
                result["tool_calls"] = [
                    {
                        "id": tc.id,
                        "name": tc.function.name,
                        "arguments": json.loads(tc.function.arguments)
                    }
                    for tc in message.tool_calls
                ]

            return result

        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return {"content": f"生成失败: {str(e)}", "tool_calls": None}


class BaseAgent(ABC):
    """Agent基类"""

    def __init__(self, name: str):
        self.name = name
        self.llm = LLMClient()
        self.tools: Dict[str, Callable] = {}

    @abstractmethod
    async def process(self, message: str, session: AgentSession) -> str:
        """处理消息"""
        pass

    def register_tool(self, name: str, func: Callable):
        """注册工具"""
        self.tools[name] = func

    def get_tools_schema(self) -> List[Dict]:
        """获取工具Schema"""
        schemas = tool_registry.get_all_schemas()
        return schemas


class QnAAgent(BaseAgent):
    """舆情问答Agent"""

    system_prompt = """你是一个专业的舆情分析助手，帮助用户了解舆情动态、分析舆情趋势。

你可以使用以下工具来获取信息：
1. semantic_search: 语义搜索舆情内容
2. keyword_search: 关键词搜索
3. database_query: 数据库查询
4. get_statistics: 获取统计数据
5. get_hot_topics: 获取热点话题
6. crawl_webpage: 抓取网页内容
7. fetch_rss: 获取RSS内容

回答时请：
- 基于检索到的事实信息作答
- 注明信息来源和时间
- 如果信息不足，请诚实告知
- 对于情感分析，保持客观中立"""

    def __init__(self):
        super().__init__("qna_agent")
        self.sessions: Dict[str, AgentSession] = {}

    async def init(self):
        """初始化"""
        await self.llm.init()
        await retriever.init()
        await ranker.init()

    async def create_session(self) -> AgentSession:
        """创建会话"""
        session_id = str(uuid.uuid4())
        session = AgentSession(session_id=session_id)
        self.sessions[session_id] = session
        return session

    async def process(self, message: str, session_id: str = None) -> str:
        """处理用户问题"""
        if not session_id:
            session = await self.create_session()
            session_id = session.session_id
        else:
            session = self.sessions.get(session_id)
            if not session:
                session = await self.create_session()

        user_message = AgentMessage(role="user", content=message)
        session.messages.append(user_message)

        messages = self._build_messages(session)

        tools = self.get_tools_schema()

        response = await self.llm.generate(messages, tools=tools)

        if response.get("tool_calls"):
            tool_results = await self._execute_tool_calls(response["tool_calls"])

            tool_messages = []
            for tc, result in zip(response["tool_calls"], tool_results):
                tool_messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": json.dumps(result, ensure_ascii=False)
                })

            messages.append({
                "role": "assistant",
                "content": response["content"],
                "tool_calls": response["tool_calls"]
            })
            messages.extend(tool_messages)

            final_response = await self.llm.generate(messages, tools=None)
            assistant_message = AgentMessage(
                role="assistant",
                content=final_response["content"]
            )
        else:
            assistant_message = AgentMessage(
                role="assistant",
                content=response["content"] or "抱歉，我无法理解您的问题。"
            )

        session.messages.append(assistant_message)
        session.updated_at = datetime.now()

        return assistant_message.content

    def _build_messages(self, session: AgentSession) -> List[Dict]:
        """构建消息列表"""
        messages = [{"role": "system", "content": self.system_prompt}]

        for msg in session.messages[-20:]:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })

        return messages

    async def _execute_tool_calls(self, tool_calls: List[Dict]) -> List[Dict]:
        """执行工具调用"""
        results = []

        for tc in tool_calls:
            tool_name = tc["name"]
            arguments = tc["arguments"]

            tool = tool_registry.get(tool_name)
            if not tool:
                results.append({
                    "success": False,
                    "error": f"工具 {tool_name} 不存在"
                })
                continue

            try:
                result = await tool(**arguments)
                results.append({
                    "success": result.success,
                    "data": result.data,
                    "error": result.error
                })
            except Exception as e:
                logger.error(f"Tool execution failed: {e}")
                results.append({
                    "success": False,
                    "error": str(e)
                })

        return results

    async def search_with_context(
        self,
        query: str,
        top_k: int = 5
    ) -> SearchResponse:
        """带上下文的搜索"""
        start_time = time.time()

        cache_key = f"search:{hash(query)}:{top_k}"
        cached = await cache.get(cache_key)
        if cached:
            return SearchResponse(**cached)

        results = await retriever.search(query, top_k=top_k)

        ranked_results = await ranker.rank(query, results, top_k=top_k)

        search_results = []
        for r in ranked_results:
            item = YuqingItem(
                id=r.id,
                title=r.title,
                content=r.content[:500],
                source=r.source,
                source_url=r.metadata.get("source_url", "") if r.metadata else "",
                publish_time=r.publish_time,
                sentiment=r.metadata.get("sentiment") if r.metadata else None
            )
            search_results.append({
                "item": item.model_dump(),
                "score": r.score,
                "highlight": self._highlight(query, r.content[:200])
            })

        response = SearchResponse(
            query=query,
            results=search_results,
            total=len(search_results),
            elapsed_time=time.time() - start_time
        )

        await cache.set(cache_key, response.model_dump(), ttl=300)

        return response

    def _highlight(self, query: str, text: str) -> str:
        """生成高亮片段"""
        words = query.split()
        for word in words:
            if len(word) > 1:
                text = text.replace(word, f"**{word}**")
        return text[:200]


class BriefingAgent(BaseAgent):
    """简报生成Agent"""

    system_prompt = """你是一个舆情简报生成专家，负责整理和分析舆情信息，生成结构化的舆情简报。

简报应该包含以下内容：
1. 概述：简要描述舆情主题和主要发现
2. 关键事件：列出重要的事件节点
3. 情感分析：分析舆论情感倾向
4. 传播分析：分析信息传播路径和影响范围
5. 风险提示：指出可能的舆情风险点
6. 建议措施：给出应对建议"""

    def __init__(self):
        super().__init__("briefing_agent")
        self.qna_agent = None

    async def init(self):
        """初始化"""
        await self.llm.init()

    def set_qna_agent(self, agent: QnAAgent):
        """设置问答Agent"""
        self.qna_agent = agent

    async def process(self, message: str, session: AgentSession = None) -> str:
        """生成简报"""
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": message}
        ]

        response = await self.llm.generate(messages)
        return response.get("content", "")

    async def generate_briefing(
        self,
        topic: str,
        time_range: int = 24,
        include_sentiment: bool = True,
        include_trend: bool = True
    ) -> Dict:
        """生成舆情简报"""

        if self.qna_agent:
            search_results = await self.qna_agent.search_with_context(
                topic, top_k=30
            )
        else:
            search_results = None

        prompt = f"""请根据以下信息生成舆情简报：

主题：{topic}
时间范围：最近{time_range}小时

{self._format_search_results(search_results) if search_results else "暂无相关数据"}

请生成包含概述、关键事件、情感分析、传播分析、风险提示和建议措施的简报。"""

        briefing_content = await self.process(prompt)

        return {
            "topic": topic,
            "time_range": time_range,
            "content": briefing_content,
            "generated_at": datetime.now().isoformat(),
            "data_sources": len(search_results.results) if search_results else 0
        }

    def _format_search_results(self, response: SearchResponse) -> str:
        """格式化搜索结果"""
        if not response or not response.results:
            return "未找到相关数据"

        lines = ["相关舆情数据：\n"]
        for i, r in enumerate(response.results[:10], 1):
            item = r.get("item", {})
            lines.append(f"{i}. 【{item.get('title', '未知标题')}】")
            lines.append(f"   来源：{item.get('source', '未知')}")
            lines.append(f"   相关度：{r.get('score', 0):.2f}")
            lines.append("")

        return "\n".join(lines)


qna_agent = QnAAgent()
briefing_agent = BriefingAgent()
