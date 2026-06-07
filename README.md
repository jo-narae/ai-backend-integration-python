# ai-backend-integration-python (Day 1 산출물)

FastAPI로 LangChain과 CrewAI를 노출하는 Python 백엔드입니다. Day 2~5에서 Spring 게이트웨이가 이 서버를 호출합니다.

## 사전 요구사항

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (`pip install uv` 또는 `curl -LsSf https://astral.sh/uv/install.sh | sh`)
- OpenAI API Key

## 셋업

```bash
# 1) 의존성 설치 + 가상환경 생성
uv sync

# 2) 환경변수 설정
cp .env.example .env
# .env 파일을 열어 OPENAI_API_KEY 를 실제 값으로 교체

# 3) 서버 실행
uv run uvicorn app.main:app --reload
```

서버 기동 후 다음 경로에 접속하실 수 있습니다.

- Swagger UI: <http://localhost:8000/docs>
- ReDoc: <http://localhost:8000/redoc>
- 헬스 체크: <http://localhost:8000/health>

## 엔드포인트

| 메서드 | 경로 | 설명 | 사용 위치 |
|--------|------|------|----------|
| GET | `/health` | 헬스 체크 | Day1 B2 |
| POST | `/echo` | Pydantic 검증 시연 | Day1 B3 |
| POST | `/chat` | LangChain 단일 체인 호출 (본문: `prompt`) | Day1 B5, Day5에서 Spring이 호출 |
| POST | `/chat/crew` | CrewAI Researcher+Writer 순차 협업 (본문: `topic`) | Day1 B6 |

> `/chat`은 자유 질문(`prompt`), `/chat/crew`는 리서치 주제(`topic`)를 받습니다. 엔드포인트마다 의미에 맞는 별도 스키마(`ChatRequest`, `CrewRequest`)를 사용합니다.
> 사용자 식별은 Spring 게이트웨이가 JWT로 처리하므로 Python 요청 본문에는 `user_id`가 없습니다. (Spring이 보내는 추가 필드는 Pydantic이 무시합니다.)

`/chat` 요청 예시:

```bash
curl -X POST http://localhost:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"FastAPI를 한 줄로 설명해 주세요"}'
```

`/chat/crew` 요청 예시:

```bash
curl -X POST http://localhost:8000/chat/crew \
  -H 'Content-Type: application/json' \
  -d '{"topic":"파이썬"}'
```

`/chat` 응답 예시:

```json
{
  "answer": "FastAPI는 Python 타입 힌트 기반의 비동기 친화 웹 프레임워크입니다.",
  "model": "gpt-5-nano"
}
```

응답 헤더에 `X-Process-Time`(초)이 자동 추가됩니다.

## 디렉터리 구조

```
app/
├── main.py             FastAPI 인스턴스, 미들웨어·예외 핸들러 등록
├── schemas.py          Pydantic v2 요청·응답 스키마
├── dependencies.py     Settings, get_llm() with @lru_cache
├── middleware.py       X-Process-Time 헤더 미들웨어
├── errors.py           500 전역 핸들러
└── routers/
    ├── chat_langchain.py   POST /chat — ChatOpenAI + ainvoke
    └── chat_crew.py        POST /chat/crew — CrewAI + kickoff_async
tests/
└── test_health.py      OpenAI 키 없이도 통과하는 최소 검증
```

## 강의 매핑

| 블록 | 학습 내용 | 핵심 파일 |
|------|----------|----------|
| Day1 B1 | 환경 준비 (`uv init`, `uv add`) | `pyproject.toml` |
| Day1 B2 | FastAPI 기본 + `/health` + `/docs` | `app/main.py` |
| Day1 B3 | Pydantic v2 스키마 + `/echo` | `app/schemas.py` |
| Day1 B4 | Depends + 미들웨어 + CORS | `app/dependencies.py`, `app/middleware.py` |
| Day1 B5 | LangChain `/chat` (ainvoke) | `app/routers/chat_langchain.py` |
| Day1 B6 | CrewAI `/chat/crew` (kickoff_async) | `app/routers/chat_crew.py` |
| Day1 B7 | 전역 예외 핸들러 + 로깅 | `app/errors.py` |

## 테스트

```bash
uv run pytest -v
```

OpenAI 키 없이도 `test_health.py`는 통과합니다.

## 트러블슈팅

| 증상 | 원인 | 해결 |
|------|------|------|
| `ValidationError: openai_api_key` | `.env` 미생성 또는 키 누락 | `.env.example` 복사 후 키 입력 |
| `/chat` 응답이 매우 느림 | `ainvoke` 대신 `invoke` 사용 | `await chain.ainvoke(...)` 확인 |
| `/chat/crew`가 다른 요청을 막음 | 동기 `crew.kickoff()` 직접 호출 | `await crew.kickoff_async()` 확인 |
| CORS 차단 | 허용 오리진 미설정 | `app/main.py`의 `allow_origins` 확인 |
