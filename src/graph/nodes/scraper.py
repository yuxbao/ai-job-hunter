from __future__ import annotations

from src.tools.web_scraper import WebScraperTool
from src.utils.logger import logger


async def run(state: dict, scraper: WebScraperTool) -> dict:
    """抓取节点: 对搜索结果中缺少详细信息的页面进行抓取"""
    raw_results = state.get("raw_results", [])
    scraped_pages = []  # 每轮重新开始

    logger.info(f"[Scraper] 开始抓取详情页, 待处理 {len(raw_results)} 条")

    for raw in raw_results:
        source = raw.get("source", "")
        url = raw.get("job_url", raw.get("url", ""))
        description = raw.get("description", raw.get("content", ""))

        # Mock 来源或已有足够描述信息，跳过抓取
        if source == "mock" or (description and len(description) > 50):
            scraped_pages.append(raw)
            continue

        if not url:
            scraped_pages.append(raw)
            continue

        try:
            result = await scraper.execute(url)
            if result.success and result.data:
                # 合并抓取内容到原始数据
                content = result.data[0].get("content", "")
                raw["description"] = content if content else description
                raw["scraped"] = True
                logger.debug(f"[Scraper] 抓取成功: {url[:60]}...")
            else:
                logger.debug(f"[Scraper] 抓取失败: {url[:60]}...")
        except Exception as e:
            logger.debug(f"[Scraper] 抓取异常: {e}")

        scraped_pages.append(raw)

    logger.info(f"[Scraper] 抓取完成, 共 {len(scraped_pages)} 条")
    return {"scraped_pages": scraped_pages, "status": "scraping"}
