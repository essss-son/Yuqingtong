"""爬虫工具封装"""
from .base import BaseTool, ToolResult, register_tool
from typing import List, Dict, Any, Optional
from datetime import datetime
import aiohttp
import asyncio
from bs4 import BeautifulSoup
import feedparser
import logging
from urllib.parse import urljoin, urlparse
import hashlib

logger = logging.getLogger(__name__)


class WebCrawler:
    """网页爬虫"""

    def __init__(self, timeout: int = 30, max_retries: int = 3):
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.max_retries = max_retries
        self.session: Optional[aiohttp.ClientSession] = None

    async def init(self):
        """初始化会话"""
        if not self.session:
            self.session = aiohttp.ClientSession(timeout=self.timeout)

    async def close(self):
        """关闭会话"""
        if self.session:
            await self.session.close()
            self.session = None

    async def fetch(self, url: str, headers: Dict = None) -> Optional[str]:
        """抓取页面"""
        await self.init()

        default_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        headers = {**default_headers, **(headers or {})}

        for attempt in range(self.max_retries):
            try:
                async with self.session.get(url, headers=headers) as response:
                    if response.status == 200:
                        return await response.text()
                    logger.warning(f"HTTP {response.status} for {url}")
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
                await asyncio.sleep(1)

        return None

    async def parse_news(self, html: str, base_url: str) -> Dict[str, Any]:
        """解析新闻页面"""
        soup = BeautifulSoup(html, "html.parser")

        title = soup.find("title")
        title_text = title.get_text().strip() if title else ""

        meta_desc = soup.find("meta", attrs={"name": "description"})
        description = meta_desc.get("content", "") if meta_desc else ""

        article = soup.find("article") or soup.find("div", class_=lambda x: x and "content" in x.lower())
        content_text = ""
        if article:
            paragraphs = article.find_all("p")
            content_text = "\n".join([p.get_text().strip() for p in paragraphs if p.get_text().strip()])

        images = []
        for img in soup.find_all("img", src=True):
            src = img.get("src")
            if src and not src.startswith("data:"):
                images.append(urljoin(base_url, src))

        return {
            "title": title_text,
            "content": content_text or description,
            "images": images[:5],
            "crawl_time": datetime.now()
        }


class RSSCrawler:
    """RSS源爬虫"""

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.web_crawler = WebCrawler(timeout=timeout)

    async def fetch_feed(self, feed_url: str) -> List[Dict]:
        """抓取RSS Feed"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(feed_url) as response:
                    content = await response.text()

            feed = feedparser.parse(content)
            items = []

            for entry in feed.entries[:20]:
                item = {
                    "title": entry.get("title", ""),
                    "content": entry.get("summary", entry.get("description", "")),
                    "source_url": entry.get("link", ""),
                    "author": entry.get("author", ""),
                    "publish_time": datetime(*entry.published_parsed[:6]) if hasattr(entry, "published_parsed") else datetime.now(),
                    "crawl_time": datetime.now()
                }
                items.append(item)

            return items

        except Exception as e:
            logger.error(f"RSS fetch failed for {feed_url}: {e}")
            return []

    async def close(self):
        await self.web_crawler.close()


@register_tool
class CrawlerTool(BaseTool):
    """网页爬取工具"""

    name = "crawl_webpage"
    description = "抓取指定URL的网页内容"
    parameters_schema = {
        "url": {
            "type": "string",
            "description": "目标URL",
            "required": True
        },
        "parse_type": {
            "type": "string",
            "enum": ["news", "raw", "text"],
            "description": "解析类型",
            "default": "news"
        }
    }

    def __init__(self):
        super().__init__()
        self.crawler = WebCrawler()

    async def execute(self, **kwargs) -> ToolResult:
        """执行爬取"""
        url = kwargs.get("url")
        parse_type = kwargs.get("parse_type", "news")

        if not url:
            return ToolResult(success=False, error="URL不能为空")

        try:
            html = await self.crawler.fetch(url)
            if not html:
                return ToolResult(success=False, error="无法获取页面内容")

            if parse_type == "news":
                data = await self.crawler.parse_news(html, url)
                data["source_url"] = url
            elif parse_type == "text":
                soup = BeautifulSoup(html, "html.parser")
                data = {"text": soup.get_text(), "source_url": url}
            else:
                data = {"html": html, "source_url": url}

            return ToolResult(success=True, data=data)

        except Exception as e:
            logger.error(f"Crawl failed: {e}")
            return ToolResult(success=False, error=str(e))


@register_tool
class RSSFetchTool(BaseTool):
    """RSS源抓取工具"""

    name = "fetch_rss"
    description = "抓取RSS订阅源内容"
    parameters_schema = {
        "feed_url": {
            "type": "string",
            "description": "RSS Feed URL",
            "required": True
        },
        "max_items": {
            "type": "integer",
            "description": "最大条目数",
            "default": 20
        }
    }

    def __init__(self):
        super().__init__()
        self.rss_crawler = RSSCrawler()

    async def execute(self, **kwargs) -> ToolResult:
        """执行RSS抓取"""
        feed_url = kwargs.get("feed_url")
        max_items = kwargs.get("max_items", 20)

        if not feed_url:
            return ToolResult(success=False, error="Feed URL不能为空")

        try:
            items = await self.rss_crawler.fetch_feed(feed_url)
            items = items[:max_items]

            return ToolResult(
                success=True,
                data={
                    "feed_url": feed_url,
                    "items": items,
                    "total": len(items)
                }
            )

        except Exception as e:
            logger.error(f"RSS fetch failed: {e}")
            return ToolResult(success=False, error=str(e))


@register_tool
class MultiSourceCrawlTool(BaseTool):
    """多源爬取工具"""

    name = "crawl_multiple"
    description = "批量抓取多个URL内容"
    parameters_schema = {
        "urls": {
            "type": "array",
            "items": {"type": "string"},
            "description": "URL列表",
            "required": True
        },
        "concurrency": {
            "type": "integer",
            "description": "并发数",
            "default": 3
        }
    }

    def __init__(self):
        super().__init__()
        self.crawler = WebCrawler()

    async def execute(self, **kwargs) -> ToolResult:
        """执行多源爬取"""
        urls = kwargs.get("urls", [])
        concurrency = kwargs.get("concurrency", 3)

        if not urls:
            return ToolResult(success=False, error="URL列表不能为空")

        semaphore = asyncio.Semaphore(concurrency)

        async def fetch_one(url: str) -> Dict:
            async with semaphore:
                try:
                    html = await self.crawler.fetch(url)
                    if html:
                        data = await self.crawler.parse_news(html, url)
                        data["source_url"] = url
                        data["success"] = True
                        return data
                except Exception as e:
                    logger.warning(f"Failed to crawl {url}: {e}")
                return {"source_url": url, "success": False, "error": "crawl_failed"}

        try:
            tasks = [fetch_one(url) for url in urls]
            results = await asyncio.gather(*tasks)

            successful = [r for r in results if r.get("success")]
            failed = [r for r in results if not r.get("success")]

            return ToolResult(
                success=True,
                data={
                    "results": successful,
                    "successful_count": len(successful),
                    "failed_count": len(failed),
                    "total": len(urls)
                }
            )

        except Exception as e:
            logger.error(f"Multi-source crawl failed: {e}")
            return ToolResult(success=False, error=str(e))
