"""최소 검증 테스트.

OpenAI 키 없이도 통과해야 합니다.
"""

from fastapi.testclient import TestClient


def test_health_returns_ok():
    """헬스 엔드포인트가 200/ok를 반환합니다."""
    # 지연 임포트 — 모듈 임포트 시점에 Settings 검증을 피하기 위함
    from app.main import app

    client = TestClient(app)
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_echo_validates_prompt_length():
    """빈 prompt는 422로 거부됩니다."""
    from app.main import app

    client = TestClient(app)
    res = client.post("/echo", json={"prompt": ""})
    assert res.status_code == 422
