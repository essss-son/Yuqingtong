"""爬虫服务"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import asyncio

from ..models.schemas import CrawlerTask, SourceType, YuqingItem, SentimentType
from ..tools import WebCrawler, RSSCrawler
from ..memory import db
from ..services.embedding import embedding_service

logger = logging.getLogger(__name__)


class CrawlerService:
    """爬虫服务"""

    def __init__(self):
        self.web_crawler = WebCrawler()
        self.rss_crawler = RSSCrawler()
        self.db = db
        self._running_tasks = {}

    async def crawl_url(
        self,
        url: str,
        parse_type: str = "news"
    ) -> Optional[Dict]:
        """抓取单个URL"""
        try:
            html = await self.web_crawler.fetch(url)
            if not html:
                logger.warning(f"Failed to fetch: {url}")
                return None

            if parse_type == "news":
                data = await self.web_crawler.parse_news(html, url)
            else:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html, "html.parser")
                data = {"text": soup.get_text()}

            data["source_url"] = url
            data["crawl_time"] = datetime.now()

            return data

        except Exception as e:
            logger.error(f"Crawl error for {url}: {e}")
            return None

    async def crawl_rss(
        self,
        feed_url: str,
        max_items: int = 20
    ) -> List[Dict]:
        """抓取RSS源"""
        try:
            items = await self.rss_crawler.fetch_feed(feed_url)
            return items[:max_items]
        except Exception as e:
            logger.error(f"RSS crawl error for {feed_url}: {e}")
            return []

    async def crawl_multiple(
        self,
        urls: List[str],
        concurrency: int = 3
    ) -> List[Dict]:
        """批量抓取多个URL"""
        semaphore = asyncio.Semaphore(concurrency)

        async def fetch_one(url: str) -> Optional[Dict]:
            async with semaphore:
                result = await self.crawl_url(url)
                if result:
                    result["source_url"] = url
                return result

        tasks = [fetch_one(url) for url in urls]
        results = await asyncio.gather(*tasks)

        return [r for r in results if r]

    async def save_yuqing(
        self,
        data: Dict,
        source: SourceType
    ) -> int:
        """保存舆情数据"""
        record = {
            "title": data.get("title", ""),
            "content": data.get("content", ""),
            "source": source,
            "source_url": data.get("source_url", ""),
            "author": data.get("author"),
            "publish_time": data.get("publish_time", datetime.now()),
            "crawl_time": data.get("crawl_time", datetime.now()),
            "images": data.get("images", [])
        }

        return await self.db.insert_yuqing(record)

    async def batch_save_yuqing(
        self,
        items: List[Dict],
        source: SourceType
    ) -> int:
        """批量保存舆情数据"""
        records = []
        for item in items:
            record = {
                "title": item.get("title", ""),
                "content": item.get("content", ""),
                "source": source,
                "source_url": item.get("source_url", ""),
                "author": item.get("author"),
                "publish_time": item.get("publish_time", datetime.now()),
                "crawl_time": item.get("crawl_time", datetime.now()),
                "images": item.get("images", [])
            }
            records.append(record)

        return await self.db.batch_insert_yuqing(records)

    async def create_task(
        self,
        name: str,
        source: SourceType,
        keywords: List[str] = None,
        urls: List[str] = None,
        schedule: str = None
    ) -> CrawlerTask:
        """创建爬虫任务"""
        task = CrawlerTask(
            name=name,
            source=source,
            keywords=keywords or [],
            urls=urls or [],
            schedule=schedule
        )

        return task

    async def run_task(
        self,
        task: CrawlerTask
    ) -> Dict[str, Any]:
        """执行爬虫任务"""
        results = []
        errors = []

        if task.urls:
            crawled = await self.crawl_multiple(task.urls)
            for item in crawled:
                try:
                    await self.save_yuqing(item, task.source)
                    results.append(item.get("source_url"))
                except Exception as e:
                    errors.append(str(e))

        return {
            "task_name": task.name,
            "total_crawled": len(results),
            "saved": len(results) - len(errors),
            "errors": errors
        }


RSS_FEEDS = {
    SourceType.NEWS: [
        "https://news.sina.com.cn/rss/news.xml",
        "https://www.chinanews.com.cn/rss/news.xml",
    ],
    SourceType.SOCIAL: [
        "https://www.zhihu.com/rss",
    ]
}


async def start_crawler():
    """启动定时爬虫"""
    service = CrawlerService()

    for source, feeds in RSS_FEEDS.items():
        for feed_url in feeds:
            try:
                items = await service.crawl_rss(feed_url, max_items=10)
                if items:
                    await service.batch_save_yuqing(items, source)
                    logger.info(f"Crawled {len(items)} items from {feed_url}")
            except Exception as e:
                logger.error(f"Failed to crawl {feed_url}: {e}")


crawler_service = CrawlerService()
