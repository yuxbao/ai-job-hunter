from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # LLM 配置
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_BASE_URL: str | None = None

    # 搜索 API
    TAVILY_API_KEY: str = ""

    # Agent 配置
    TARGET_JOB_COUNT: int = 50
    MAX_ITERATIONS: int = 5
    BATCH_SIZE: int = 10
    SEARCH_CONCURRENCY: int = 4
    FILTER_CONCURRENCY: int = 4
    SCRAPE_TIMEOUT: int = 30
    ENRICH_CANDIDATE_BUFFER: int = 10
    ENRICH_CONCURRENCY: int = 4
    SHOW_LLM_OUTPUT: bool = True
    LLM_OUTPUT_MAX_CHARS: int = 2000
    WRITE_LLM_OUTPUT_FILES: bool = True

    # 输出
    OUTPUT_DIR: str = "output"

    # 模式
    MOCK_MODE: bool = False

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
