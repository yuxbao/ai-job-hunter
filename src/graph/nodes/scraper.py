from __future__ import annotations

from src.tools.web_scraper import WebScraperTool
from src.utils.logger import logger
from src.utils.progress import ProgressCallback, emit_progress


async def run(
    state: dict,
    scraper: WebScraperTool,
    progress_callback: ProgressCallback | None = None,
) -> dict:
    """抓取节点: 对搜索结果中缺少详细信息的页面进行抓取"""
    raw_results = state.get("raw_results", [])
    scraped_pages = []  # 每轮重新开始

    logger.info(f"[Scraper] 开始抓取详情页, 待处理 {len(raw_results)} 条")

    total_items = len(raw_results) or 1
    for index, raw in enumerate(raw_results, 1):
        source = raw.get("source", "")
        url = raw.get("job_url", raw.get("url", ""))
        description = raw.get("description", raw.get("content", ""))

        # Mock 来源或已有足够描述信息，跳过抓取
        if source == "mock" or (description and len(description) > 50):
            scraped_pages.append(raw)
            await emit_progress(
                progress_callback,
                {
                    "event": "stage_progress",
                    "stage": "scraper",
                    "message": f"跳过抓取：{raw.get('title', '未知岗位')}",
                    "stage_progress": index / total_items,
                    "counts": {"scraped_pages": len(scraped_pages)},
                },
            )
            continue

        if not url:
            scraped_pages.append(raw)
            await emit_progress(
                progress_callback,
                {
                    "event": "stage_progress",
                    "stage": "scraper",
                    "message": f"缺少链接：{raw.get('title', '未知岗位')}",
                    "stage_progress": index / total_items,
                    "counts": {"scraped_pages": len(scraped_pages)},
                },
            )
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
        await emit_progress(
            progress_callback,
            {
                "event": "stage_progress",
                "stage": "scraper",
                "message": f"已处理详情页：{raw.get('title', '未知岗位')}",
                "stage_progress": index / total_items,
                "counts": {"scraped_pages": len(scraped_pages)},
            },
        )

    logger.info(f"[Scraper] 抓取完成, 共 {len(scraped_pages)} 条")
    return {"scraped_pages": scraped_pages, "status": "scraping"}
