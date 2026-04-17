"""API路由定义"""
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import List, Optional
from datetime import datetime

from ..models.schemas import (
    SearchQuery, SearchResponse, SearchResult,
    BriefingRequest, Briefing,
    CrawlerTask, HotTopic,
    EmbeddingRequest, EmbeddingResponse,
    RerankRequest, RerankResponse,
    ApiResponse, YuqingItem, SourceType
)
from ..agents import qna_agent, briefing_agent
from ..services import briefing_service, embedding_service, crawler_service
from ..memory import db, cache
from ..retrieval import retriever, ranker

router = APIRouter()


@router.get("/")
async def root():
    """根路径"""
    return {
        "name": "Yuqingtong API",
        "version": "1.0.0",
        "status": "running"
    }


@router.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@router.post("/search", response_model=SearchResponse)
async def search(query: SearchQuery):
    """语义搜索"""
    try:
        results = await retriever.search(
            query=query.query,
            top_k=query.top_k,
            sources=query.sources,
            time_range=24 if query.start_date else None,
            use_expansion=query.use_expansion,
            use_hyde=query.use_hyde
        )

        ranked = await ranker.rank(query.query, results, top_k=query.top_k)

        search_results = [
            SearchResult(
                item=YuqingItem(
                    id=r.id,
                    title=r.title,
                    content=r.content[:500],
                    source=r.source,
                    source_url=r.metadata.get("source_url", "") if r.metadata else "",
                    publish_time=r.publish_time
                ),
                score=r.score,
                highlight=None
            )
            for r in ranked
        ]

        return SearchResponse(
            query=query.query,
            results=[r.model_dump() for r in search_results],
            total=len(search_results),
            elapsed_time=0.0
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat")
async def chat(
    message: str,
    session_id: Optional[str] = None
):
    """智能问答"""
    try:
        response = await qna_agent.process(message, session_id)
        return {
            "success": True,
            "data": {
                "response": response,
                "session_id": session_id
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/briefing", response_model=Briefing)
async def generate_briefing(request: BriefingRequest):
    """生成舆情简报"""
    try:
        briefing = await briefing_service.generate(request)
        return briefing
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/briefings", response_model=List[Briefing])
async def list_briefings(limit: int = Query(20, ge=1, le=100)):
    """获取简报历史"""
    try:
        briefings = await briefing_service.get_history(limit)
        return briefings
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/hot-topics")
async def get_hot_topics(
    limit: int = Query(10, ge=1, le=50),
    time_range: int = Query(24, ge=1, le=168)
):
    """获取热点话题"""
    try:
        topics = await db.get_hot_topics(limit=limit, time_range=time_range)
        return {"success": True, "data": topics}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics/{metric}")
async def get_statistics(
    metric: str,
    time_range: int = Query(24, ge=1, le=720)
):
    """获取统计数据"""
    try:
        from datetime import timedelta
        start_time = datetime.now() - timedelta(hours=time_range)

        if metric == "sentiment":
            data = await db.get_sentiment_distribution(start_time)
        elif metric == "keywords":
            data = await db.get_hot_keywords(start_time)
        elif metric == "sources":
            data = await db.get_source_distribution(start_time)
        elif metric == "trend":
            data = await db.get_trend_data(start_time)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown metric: {metric}")

        return {"success": True, "data": data}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/embeddings", response_model=EmbeddingResponse)
async def create_embeddings(request: EmbeddingRequest):
    """创建文本嵌入"""
    try:
        embeddings = await embedding_service.encode_texts(request.texts)
        return EmbeddingResponse(
            embeddings=embeddings,
            model=request.model or "default",
            dimension=len(embeddings[0]) if embeddings else 0,
            elapsed_time=0.0
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rerank", response_model=RerankResponse)
async def rerank_documents(request: RerankRequest):
    """文档重排序"""
    try:
        from ..retrieval import RetrievalResult

        results = [
            RetrievalResult(
                id=i,
                title="",
                content=doc,
                score=0.0,
                source="",
                publish_time=datetime.now()
            )
            for i, doc in enumerate(request.documents)
        ]

        ranked = await ranker.rank(
            request.query,
            results,
            top_k=request.top_k
        )

        return RerankResponse(
            results=[
                {"index": r.id, "document": r.content, "score": r.score}
                for r in ranked
            ],
            elapsed_time=0.0
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/crawl/url")
async def crawl_url(
    url: str,
    source: SourceType = SourceType.NEWS
):
    """抓取单个URL"""
    try:
        data = await crawler_service.crawl_url(url)
        if data:
            await crawler_service.save_yuqing(data, source)
            return {"success": True, "data": data}
        return {"success": False, "error": "Failed to crawl URL"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/crawl/rss")
async def crawl_rss(
    feed_url: str,
    source: SourceType = SourceType.NEWS,
    max_items: int = Query(20, ge=1, le=100)
):
    """抓取RSS源"""
    try:
        items = await crawler_service.crawl_rss(feed_url, max_items)
        if items:
            saved = await crawler_service.batch_save_yuqing(items, source)
            return {"success": True, "data": {"crawled": len(items), "saved": saved}}
        return {"success": False, "error": "No items found"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/yuqing")
async def list_yuqing(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    source: Optional[SourceType] = None
):
    """获取舆情列表"""
    try:
        sources = [source] if source else None
        records = await db.search_yuqing(
            sources=sources,
            limit=limit,
            offset=offset
        )

        items = [
            YuqingItem(
                id=r.id,
                title=r.title,
                content=r.content[:500],
                source=r.source,
                source_url=r.source_url,
                author=r.author,
                publish_time=r.publish_time,
                sentiment=r.sentiment,
                keywords=r.keywords or []
            )
            for r in records
        ]

        return {"success": True, "data": items, "total": len(items)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tools")
async def list_tools():
    """列出可用工具"""
    from ..tools import tool_registry
    return {
        "success": True,
        "data": tool_registry.get_all_schemas()
    }
