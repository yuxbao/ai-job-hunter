from __future__ import annotations

from dataclasses import dataclass
from functools import partial
from typing import Any

from langgraph.graph import StateGraph, END

from config.settings import settings
from src.graph.nodes import enricher, evaluator, filter, planner, quality_gate, reporter, scraper, searcher
from src.sources.boss_zhipin import BossZhipinSource
from src.sources.liepin import LiepinSource
from src.sources.mock_source import MockSource
from src.sources.zhaopin import ZhaopinSource
from src.state.job_search_state import JobSearchState
from src.tools.search_engine import SearchEngineTool
from src.tools.web_scraper import WebScraperTool
from src.utils.logger import logger


@dataclass
class GraphRuntime:
    graph: Any
    search_tool: SearchEngineTool
    web_scraper_tool: WebScraperTool

    async def aclose(self) -> None:
        await self.search_tool.aclose()
        await self.web_scraper_tool.aclose()


def build_graph() -> GraphRuntime:
    """构建 LangGraph 状态机"""

    # 初始化 LLM（仅在 API Key 有效时）
    llm = None
    if settings.LLM_API_KEY and settings.LLM_API_KEY not in ("sk-placeholder", "sk-xxx", ""):
        try:
            from langchain_openai import ChatOpenAI

            llm = ChatOpenAI(
                api_key=settings.LLM_API_KEY,
                model=settings.LLM_MODEL,
                base_url=settings.LLM_BASE_URL,
                temperature=0.3,
            )
            logger.info(f"[Graph] LLM 已初始化: {settings.LLM_MODEL}")
        except Exception as e:
            logger.warning(f"[Graph] LLM 初始化失败: {e}")
    else:
        logger.info("[Graph] 未配置 LLM API Key，使用规则引擎模式")

    # 初始化工具
    search_tool = SearchEngineTool(settings.TAVILY_API_KEY)
    web_scraper_tool = WebScraperTool()

    # 初始化数据源
    sources = {}
    if settings.MOCK_MODE:
        sources["mock"] = MockSource()
        logger.info("[Graph] Mock 模式: 使用模拟数据源")
    else:
        sources["boss_zhipin"] = BossZhipinSource(search_tool)
        sources["liepin"] = LiepinSource(search_tool)
        sources["zhaopin"] = ZhaopinSource(search_tool)
        sources["mock"] = MockSource()  # 作为 fallback
        logger.info(f"[Graph] 真实模式: 数据源 {list(sources.keys())}")

    # 使用 partial 绑定依赖到节点函数
    planner_node = partial(planner.run, llm=llm)
    searcher_node = partial(
        searcher.run,
        sources=sources,
        max_concurrency=settings.SEARCH_CONCURRENCY,
    )
    scraper_node = partial(scraper.run, scraper=web_scraper_tool)
    filter_node = partial(filter.run, llm=llm)
    enricher_node = partial(enricher.run, llm=llm)

    # 构建图
    graph = StateGraph(JobSearchState)

    # 添加节点
    graph.add_node("planner", planner_node)
    graph.add_node("searcher", searcher_node)
    graph.add_node("scraper", scraper_node)
    graph.add_node("quality_gate", quality_gate.run)
    graph.add_node("filter", filter_node)
    graph.add_node("enricher", enricher_node)
    graph.add_node("evaluator", evaluator.run)
    graph.add_node("reporter", reporter.run)

    # 定义边
    graph.set_entry_point("planner")
    graph.add_edge("planner", "searcher")
    graph.add_edge("searcher", "scraper")
    graph.add_edge("scraper", "quality_gate")
    graph.add_edge("quality_gate", "filter")
    graph.add_edge("filter", "enricher")
    graph.add_edge("enricher", "evaluator")

    # 条件路由: 评估后决定继续搜索还是完成
    graph.add_conditional_edges(
        "evaluator",
        evaluator.route_decision,
        {
            "continue_search": "planner",
            "report": "reporter",
        },
    )
    graph.add_edge("reporter", END)

    return GraphRuntime(
        graph=graph.compile(),
        search_tool=search_tool,
        web_scraper_tool=web_scraper_tool,
    )
