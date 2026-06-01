"""의존성 주입 — Settings와 LLM 클라이언트.

요청마다 ChatOpenAI 인스턴스를 새로 만들면 비효율적이므로
@lru_cache로 캐시된 팩토리를 Depends로 노출합니다.
"""

from functools import lru_cache

from langchain_openai import ChatOpenAI
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """환경변수 기반 설정.

    .env 파일이 있으면 자동 로드합니다.
    """

    openai_api_key: str
    model_name: str = "gpt-5-nano"
    port: int = 8000
    request_timeout: float = 30.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    """Settings 싱글톤. 첫 호출 시 1회만 생성됩니다."""
    return Settings()


@lru_cache
def get_llm() -> ChatOpenAI:
    """ChatOpenAI 싱글톤.

    Depends(get_llm)으로 주입받으면 요청마다 객체가 재사용됩니다.
    """
    settings = get_settings()
    return ChatOpenAI(
        model=settings.model_name,
        api_key=settings.openai_api_key,
        timeout=settings.request_timeout,
    )
