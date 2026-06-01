"""LangChain 기반 단일 체인 /chat 라우트.

핵심 패턴:
- 동기 invoke는 이벤트 루프를 차단합니다 → 반드시 ainvoke 사용
- ChatOpenAI는 Depends로 주입받아 재사용
"""

from fastapi import APIRouter, Depends
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from ..dependencies import Settings, get_llm, get_settings
from ..schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    llm: ChatOpenAI = Depends(get_llm),
    settings: Settings = Depends(get_settings),
) -> ChatResponse:
    """LangChain ChatOpenAI 단일 체인 호출."""
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "You are a helpful assistant. Respond in Korean."),
            ("human", "{q}"),
        ]
    )
    chain = prompt | llm
    result = await chain.ainvoke({"q": req.prompt})
    return ChatResponse(answer=result.content, model=settings.model_name)
