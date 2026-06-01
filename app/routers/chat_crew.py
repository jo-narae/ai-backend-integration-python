"""CrewAI 멀티에이전트 /chat/crew 라우트.

핵심 패턴:
- CrewAI는 비동기 실행용 kickoff_async()를 제공하므로 await로 호출합니다
  → 동기 kickoff()를 그대로 부르면 FastAPI 이벤트 루프가 차단됩니다
- 에이전트마다 LLM을 호출하므로 LangChain 단일 체인 대비 비용·시간이 수 배 증가합니다
"""

from crewai import Agent, Crew, Process, Task
from crewai import LLM as CrewLLM
from fastapi import APIRouter, Depends

from ..dependencies import Settings, get_settings
from ..schemas import ChatResponse, CrewRequest

router = APIRouter(prefix="/chat", tags=["chat-crew"])


def _build_crew(topic: str, settings: Settings) -> Crew:
    """Researcher + Writer 순차 협업 Crew를 구성합니다."""
    llm = CrewLLM(
        model=f"openai/{settings.model_name}",
        api_key=settings.openai_api_key,
    )

    researcher = Agent(
        role="Researcher",
        goal=f"{topic}에 대한 핵심 사실 3가지를 정리한다",
        backstory="기술 동향을 빠르게 수집하는 리서처입니다.",
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )
    writer = Agent(
        role="Writer",
        goal="리서치 결과를 한국어 단락으로 다듬는다",
        backstory="명료한 기술 글쓰기에 특화된 라이터입니다.",
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )

    research_task = Task(
        description=f"주제 '{topic}'에 대해 핵심 사실 3가지를 수집합니다.",
        expected_output="bullet 3개로 구성된 사실 목록",
        agent=researcher,
    )
    write_task = Task(
        description="리서치 결과를 200자 내외 한국어 단락으로 작성합니다.",
        expected_output="200자 내외 한국어 단락",
        agent=writer,
        context=[research_task],
    )

    return Crew(
        agents=[researcher, writer],
        tasks=[research_task, write_task],
        process=Process.sequential,
        verbose=False,
    )


@router.post("/crew", response_model=ChatResponse)
async def chat_crew(
    req: CrewRequest,
    settings: Settings = Depends(get_settings),
) -> ChatResponse:
    """CrewAI 멀티에이전트 호출. kickoff_async()로 이벤트 루프를 차단하지 않습니다."""
    crew = _build_crew(req.topic, settings)
    result = await crew.kickoff_async()
    return ChatResponse(answer=str(result), model=f"crew-{settings.model_name}")
