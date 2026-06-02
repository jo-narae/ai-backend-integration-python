"""CrewAI RAG /chat/rag 라우트.

흐름:
- @tool 로 정의한 '회사 문서 검색 도구'가 LangChain retriever 를 감쌉니다
- 인사팀 에이전트가 이 도구로 벡터 DB(POST /ingest 로 적재된 PDF)를 검색해
  근거에 기반한 답변을 생성합니다

핵심 패턴:
- 검색 도구 안에서 get_retriever() 를 lazy 호출합니다. 모듈 import 시점에
  벡터스토어를 만들지 않으므로 OpenAI 키 없이도 import/테스트가 가능합니다.
- CrewAI 는 kickoff_async() 로 호출해 FastAPI 이벤트 루프를 막지 않습니다.
"""

from crewai import Agent, Crew, Process, Task
from crewai import LLM as CrewLLM
from crewai.tools import tool
from fastapi import APIRouter, Depends

from ..dependencies import Settings, get_retriever, get_settings
from ..schemas import ChatResponse, RagRequest

router = APIRouter(prefix="/rag", tags=["rag"])


@tool("company_doc_search")
def company_doc_search(query: str) -> str:
    """회사 내부 문서(규정, 매뉴얼 등)에서 질문과 관련된 내용을 검색합니다."""
    # retriever 가 질문과 가장 유사한 청크 k개를 벡터 DB에서 찾아옵니다
    retriever = get_retriever()
    docs = retriever.invoke(query)
    if not docs:
        return "관련 문서를 찾지 못했습니다. 먼저 POST /ingest 로 문서를 업로드하세요."
    # 출처(파일명)와 함께 본문을 반환해 에이전트가 근거를 인용할 수 있게 합니다
    return "\n\n".join(
        f"[출처: {d.metadata.get('source', '?')}]\n{d.page_content}" for d in docs
    )


def _build_crew(question: str, settings: Settings) -> Crew:
    """검색 도구를 장착한 인사팀 에이전트 Crew를 구성합니다."""
    llm = CrewLLM(
        model=f"openai/{settings.model_name}",
        api_key=settings.openai_api_key,
    )

    policy_agent = Agent(
        role="인사팀 에이전트",
        goal="사내 규정에 맞게 직원의 질문에 정확히 답변한다",
        backstory="사내 모든 규정을 숙지하고 있는 친절한 인사팀 담당자입니다.",
        tools=[company_doc_search],
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )

    answer_task = Task(
        description=(
            f"직원의 질문에 답하세요: '{question}'\n"
            "반드시 '회사 문서 검색 도구'로 사내 문서를 먼저 검색하고, "
            "검색된 근거에 기반해 한국어로 답하세요. "
            "문서에 없는 내용은 추측하지 말고 모른다고 답하세요."
        ),
        expected_output="사내 문서 근거에 기반한 한국어 답변",
        agent=policy_agent,
    )

    return Crew(
        agents=[policy_agent],
        tasks=[answer_task],
        process=Process.sequential,
        verbose=False,
    )


@router.post("/chat", response_model=ChatResponse)
async def chat_rag(
    req: RagRequest,
    settings: Settings = Depends(get_settings),
) -> ChatResponse:
    """CrewAI 인사팀 에이전트가 벡터 DB를 검색해 답합니다."""
    crew = _build_crew(req.question, settings)
    result = await crew.kickoff_async()
    return ChatResponse(answer=str(result), model=f"rag-{settings.model_name}")
