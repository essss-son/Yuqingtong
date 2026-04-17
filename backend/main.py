"""主应用入口"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import asyncio
from contextlib import asynccontextmanager

from .config import settings
from .api import router
from .memory import cache, db
from .agents import qna_agent, briefing_agent
from .services import embedding_service
from .retrieval import retriever, ranker

logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("Starting up Yuqingtong...")

    try:
        logger.info("Initializing database...")
        await db.init()

        logger.info("Initializing cache...")
        await cache.init()

        logger.info("Initializing embedding service...")
        await embedding_service.init()

        logger.info("Initializing retriever...")
        await retriever.init()

        logger.info("Initializing ranker...")
        await ranker.init()

        logger.info("Initializing agents...")
        await qna_agent.init()
        await briefing_agent.init()
        briefing_agent.set_qna_agent(qna_agent)

        logger.info("Yuqingtong started successfully")

        yield

    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise
    finally:
        logger.info("Shutting down Yuqingtong...")

        await cache.close()
        await db.close()

        logger.info("Yuqingtong shutdown complete")


app = FastAPI(
    title="Yuqingtong API",
    description="舆情智能问答与检索Agent系统",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG
    )
