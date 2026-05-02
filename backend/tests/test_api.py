from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient
from unittest.mock import patch


ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR))
TEST_DB_PATH = Path(__file__).resolve().parents[1] / "test_history.db"
if TEST_DB_PATH.exists():
    TEST_DB_PATH.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"
os.environ["USE_DEMO_AI"] = "true"
os.environ["ENABLE_EXTERNAL_MEDIA_SEARCH"] = "false"
os.environ["OPENAI_API_KEY"] = ""
os.environ["SETTINGS_SOURCE_PRIORITY"] = "env_first"

from backend.app.config import get_settings

get_settings.cache_clear()

from backend.app.main import app


client = TestClient(app)


def auth_headers() -> dict[str, str]:
    settings = get_settings()
    response = client.post(
        "/api/admin/login",
        json={"username": settings.admin_username, "password": settings.admin_password},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def build_generated_payload(topic: str = "Древняя Русь") -> dict:
    response = client.post(
        "/api/admin/lessons/generate",
        headers=auth_headers(),
        json={"topic": topic},
    )
    assert response.status_code == 200
    return response.json()


def test_login_success() -> None:
    settings = get_settings()
    response = client.post(
        "/api/admin/login",
        json={"username": settings.admin_username, "password": settings.admin_password},
    )
    assert response.status_code == 200
    assert response.json()["access_token"]


def test_login_failure() -> None:
    response = client.post("/api/admin/login", json={"username": "bad", "password": "bad"})
    assert response.status_code == 401


def test_generate_demo_lesson_returns_layout_and_slots() -> None:
    payload = build_generated_payload()
    assert payload["title"]
    assert payload["visualMode"] == "chronicle"
    assert payload["lessonLayout"]["hero"]["slotId"] == "hero-main"
    assert payload["lessonLayout"]["imageSlots"]
    assert payload["quiz"]


def test_ai_blueprint_normalization_fills_missing_required_fields() -> None:
    from backend.app.ai import _extract_ai_json, _validate_and_fix_blueprint
    from backend.app.schemas import GenerateLessonResponse

    raw = _extract_ai_json(
        """
        ```json
        {
          "lessonLayout": {
            "hero": {"intro": "Короткое вступление", "slot_id": "hero-main"},
            "sections": [
              {"id": "ai-overview", "block_type": "narrative", "title": "AI-раздел"}
            ]
          },
          "quiz": [
            {"prompt": "Вопрос?", "options": ["A", "B", "C", "D"], "correct_option_index": 1, "explanation": "Ответ B"}
          ]
        }
        ```
        """
    )
    payload = _validate_and_fix_blueprint(raw, "Древний Египет")

    GenerateLessonResponse.model_validate(payload)
    assert payload["title"]
    assert payload["lessonLayout"]["sections"][0]["title"] == "AI-раздел"
    assert {section["blockType"] for section in payload["lessonLayout"]["sections"]} >= {
        "narrative",
        "timeline",
        "person_card_grid",
        "artifact_gallery",
        "quote_callout",
    }
    assert len(payload["quiz"]) >= 3


def test_local_ai_base_url_can_run_without_api_key() -> None:
    from backend.app.ai import _should_use_ai

    with patch.dict(
        os.environ,
        {
            "USE_DEMO_AI": "false",
            "OPENAI_API_KEY": "",
            "OPENAI_BASE_URL": "http://127.0.0.1:11434/v1",
            "OPENAI_MODEL": "qwen2.5:7b-instruct",
            "SETTINGS_SOURCE_PRIORITY": "env_first",
        },
    ):
        get_settings.cache_clear()
        assert _should_use_ai() is True

    get_settings.cache_clear()


def test_create_lesson_persists_layout_and_sanitizes_legacy_html() -> None:
    generated = build_generated_payload("Петровские реформы")
    generated["lessonHtml"] = "<h2>ok</h2><script>alert(1)</script>"
    response = client.post("/api/admin/lessons", headers=auth_headers(), json=generated)
    assert response.status_code == 200
    payload = response.json()
    assert payload["lessonLayout"]["sections"]
    assert "<script>" not in payload["lessonHtml"]


def test_refresh_slot_images_returns_slot() -> None:
    generated = build_generated_payload("Куликовская битва")
    create_response = client.post("/api/admin/lessons", headers=auth_headers(), json=generated)
    lesson_id = create_response.json()["id"]

    slot_id = create_response.json()["lessonLayout"]["imageSlots"][0]["slotId"]
    response = client.post(
        f"/api/admin/lessons/{lesson_id}/refresh-slot-images",
        headers=auth_headers(),
        json={"slotId": slot_id},
    )
    assert response.status_code == 200
    assert response.json()["slot"]["slotId"] == slot_id


def test_public_endpoint_hides_candidate_images_and_queries() -> None:
    generated = build_generated_payload("Киевская Русь")
    create_response = client.post("/api/admin/lessons", headers=auth_headers(), json=generated)
    lesson_id = create_response.json()["id"]
    client.post(f"/api/admin/lessons/{lesson_id}/publish", headers=auth_headers())
    slug = create_response.json()["slug"]

    response = client.get(f"/api/public/lessons/{slug}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["lessonLayout"]["imageSlots"][0]["candidateAssets"] == []
    assert payload["lessonLayout"]["imageSlots"][0]["searchQueries"] == []


def test_legacy_unpublished_lesson_not_available_publicly() -> None:
    response = client.post(
        "/api/admin/lessons",
        headers=auth_headers(),
        json={
            "title": "Старый урок",
            "topic": "История",
            "heroSubtitle": "Старый HTML урок",
            "visualMode": "archive",
            "lessonLayout": None,
            "lessonHtml": "<h2>Черновик</h2><p>Текст для проверки.</p>",
            "quiz": [
                {
                    "prompt": "Вопрос 1",
                    "options": ["1", "2", "3", "4"],
                    "correctOptionIndex": 0,
                    "explanation": "Пояснение",
                },
                {
                    "prompt": "Вопрос 2",
                    "options": ["1", "2", "3", "4"],
                    "correctOptionIndex": 1,
                    "explanation": "Пояснение",
                },
                {
                    "prompt": "Вопрос 3",
                    "options": ["1", "2", "3", "4"],
                    "correctOptionIndex": 2,
                    "explanation": "Пояснение",
                },
            ],
        },
    )
    slug = response.json()["slug"]
    public_response = client.get(f"/api/public/lessons/{slug}")
    assert public_response.status_code == 404


def _create_and_publish(topic: str = "Древняя Русь") -> tuple[int, str]:
    generated = build_generated_payload(topic)
    create_response = client.post("/api/admin/lessons", headers=auth_headers(), json=generated)
    lesson_id = create_response.json()["id"]
    client.post(f"/api/admin/lessons/{lesson_id}/publish", headers=auth_headers())
    slug = create_response.json()["slug"]
    return lesson_id, slug


def test_submit_quiz_returns_score_and_persists() -> None:
    lesson_id, slug = _create_and_publish("Тест результатов")

    response = client.post(
        f"/api/public/lessons/{slug}/submit-quiz",
        json={"studentName": "Иванов Иван", "answers": [0, 1, 3]},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["score"] == 2
    assert payload["total"] == 3
    assert len(payload["answerReview"]) == 3

    results = client.get(
        f"/api/admin/lessons/{lesson_id}/quiz-results",
        headers=auth_headers(),
    )
    assert results.status_code == 200
    attempts = results.json()["attempts"]
    assert len(attempts) >= 1
    assert attempts[0]["studentName"] == "Иванов Иван"
    assert attempts[0]["score"] == 2


def test_submit_quiz_requires_student_name() -> None:
    _, slug = _create_and_publish("Тест без имени")

    response = client.post(
        f"/api/public/lessons/{slug}/submit-quiz",
        json={"answers": [0, 1, 3]},
    )
    assert response.status_code == 422


def test_quiz_results_empty_for_new_lesson() -> None:
    generated = build_generated_payload("Пустой тест")
    create_response = client.post("/api/admin/lessons", headers=auth_headers(), json=generated)
    lesson_id = create_response.json()["id"]

    results = client.get(
        f"/api/admin/lessons/{lesson_id}/quiz-results",
        headers=auth_headers(),
    )
    assert results.status_code == 200
    assert results.json()["attempts"] == []


def test_delete_lesson_removes_it_from_admin_list() -> None:
    generated = build_generated_payload("Удаляемый урок")
    create_response = client.post("/api/admin/lessons", headers=auth_headers(), json=generated)
    lesson_id = create_response.json()["id"]

    delete_response = client.delete(f"/api/admin/lessons/{lesson_id}", headers=auth_headers())
    assert delete_response.status_code == 204

    list_response = client.get("/api/admin/lessons", headers=auth_headers())
    assert lesson_id not in [lesson["id"] for lesson in list_response.json()]


def test_sanitization_strips_script_tags() -> None:
    from backend.app.sanitization import sanitize_lesson_html

    result = sanitize_lesson_html('<h2>Привет</h2><script>alert("xss")</script><p>Текст</p>')
    assert "<script>" not in result
    assert "<h2>" in result
    assert "<p>" in result


def test_sanitization_allows_safe_tags() -> None:
    from backend.app.sanitization import sanitize_lesson_html

    html = '<table><thead><tr><th colspan="2">Заголовок</th></tr></thead></table>'
    result = sanitize_lesson_html(html)
    assert "<table>" in result
    assert 'colspan="2"' in result


def test_sanitization_strips_onclick() -> None:
    from backend.app.sanitization import sanitize_lesson_html

    result = sanitize_lesson_html('<p onclick="alert(1)">Текст</p>')
    assert "onclick" not in result
    assert "<p>" in result


def test_health_endpoint() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_build_search_queries_deduplicates() -> None:
    from backend.app.media import build_search_queries

    result = build_search_queries("Пётр I", "Петровские реформы", "person")
    assert len(result) == len(set(result))
    assert len(result) <= 6


def test_build_search_queries_respects_existing() -> None:
    from backend.app.media import build_search_queries

    result = build_search_queries("Кремль", "Москва", "section", ["Московский Кремль"])
    assert "Московский Кремль" in result
