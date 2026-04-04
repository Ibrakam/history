from __future__ import annotations

import json
from copy import deepcopy

import httpx
from fastapi import HTTPException

from .config import get_settings
from .demo_content import build_demo_lesson
from .media import build_demo_asset, generate_ai_hero_asset, search_wikimedia_assets
from .schemas import GenerateLessonResponse, LessonLayout, MediaAsset
from .theme_logic import infer_visual_mode


BLUEPRINT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["title", "topic", "heroSubtitle", "visualMode", "lessonLayout", "quiz"],
    "properties": {
        "title": {"type": "string"},
        "topic": {"type": "string"},
        "heroSubtitle": {"type": "string"},
        "visualMode": {
            "type": "string",
            "enum": ["chronicle", "empire", "warfront", "reform", "archive"],
        },
        "lessonLayout": {
            "type": "object",
            "additionalProperties": False,
            "required": ["visualMode", "hero", "sections", "imageSlots"],
            "properties": {
                "visualMode": {
                    "type": "string",
                    "enum": ["chronicle", "empire", "warfront", "reform", "archive"],
                },
                "hero": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["eyebrow", "intro", "slotId"],
                    "properties": {
                        "eyebrow": {"type": "string"},
                        "intro": {"type": "string"},
                        "slotId": {"type": "string"},
                    },
                },
                "sections": {
                    "type": "array",
                    "minItems": 4,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": [
                            "id",
                            "blockType",
                            "title",
                            "lead",
                            "body",
                            "timelineItems",
                            "personCards",
                            "artifactCards",
                            "quoteText",
                            "quoteCaption",
                            "slotId",
                            "visible",
                        ],
                        "properties": {
                            "id": {"type": "string"},
                            "blockType": {
                                "type": "string",
                                "enum": [
                                    "narrative",
                                    "timeline",
                                    "person_card_grid",
                                    "artifact_gallery",
                                    "quote_callout",
                                ],
                            },
                            "title": {"type": "string"},
                            "lead": {"type": ["string", "null"]},
                            "body": {"type": "array", "items": {"type": "string"}},
                            "timelineItems": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "required": ["year", "title", "description"],
                                    "properties": {
                                        "year": {"type": "string"},
                                        "title": {"type": "string"},
                                        "description": {"type": "string"},
                                    },
                                },
                            },
                            "personCards": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "required": ["name", "role", "summary", "slotId"],
                                    "properties": {
                                        "name": {"type": "string"},
                                        "role": {"type": "string"},
                                        "summary": {"type": "string"},
                                        "slotId": {"type": ["string", "null"]},
                                    },
                                },
                            },
                            "artifactCards": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "required": ["title", "summary", "slotId"],
                                    "properties": {
                                        "title": {"type": "string"},
                                        "summary": {"type": "string"},
                                        "slotId": {"type": ["string", "null"]},
                                    },
                                },
                            },
                            "quoteText": {"type": ["string", "null"]},
                            "quoteCaption": {"type": ["string", "null"]},
                            "slotId": {"type": ["string", "null"]},
                            "visible": {"type": "boolean"},
                        },
                    },
                },
                "imageSlots": {
                    "type": "array",
                    "minItems": 3,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["slotId", "label", "searchQueries", "role"],
                        "properties": {
                            "slotId": {"type": "string"},
                            "label": {"type": "string"},
                            "searchQueries": {"type": "array", "items": {"type": "string"}},
                            "role": {"type": "string"},
                        },
                    },
                },
            },
        },
        "quiz": {
            "type": "array",
            "minItems": 3,
            "maxItems": 8,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["prompt", "options", "correctOptionIndex", "explanation"],
                "properties": {
                    "prompt": {"type": "string"},
                    "options": {
                        "type": "array",
                        "minItems": 4,
                        "maxItems": 4,
                        "items": {"type": "string"},
                    },
                    "correctOptionIndex": {"type": "integer", "minimum": 0, "maximum": 3},
                    "explanation": {"type": "string"},
                },
            },
        },
    },
}


SYSTEM_PROMPT = """
Ты создаёшь визуальный школьный урок истории на русском языке.
Верни строго JSON по схеме.

Требования:
- Пиши понятно для школьника 7-11 класса.
- Сформируй красивую структуру урока как лендинг.
- Всегда делай hero, narrative, timeline, person_card_grid, artifact_gallery и quote_callout.
- Для каждого image slot дай 2-3 поисковых запроса на русском, чтобы найти исторические изображения или карты.
- Для person_card_grid и artifact_gallery старайся давать 2-4 карточки.
- visualMode выбери из chronicle, empire, warfront, reform, archive.
- Не вставляй HTML и CSS, только чистые данные.
- Тест должен проверять содержание урока и иметь 4 варианта ответа.
- Для всех полей секций всегда возвращай значение: если поле не используется, ставь null или [].
""".strip()


def _extract_output_text(payload: dict) -> str | None:
    output_text = payload.get("output_text")
    if output_text:
        return output_text

    for item in payload.get("output", []):
        for content in item.get("content", []):
            if content.get("type") == "output_text" and content.get("text"):
                return content["text"]
    return None


def _pick_default_asset(slot: dict, visual_mode: str) -> MediaAsset:
    return build_demo_asset(slot["label"], visual_mode, slot["slotId"])


def _queries_for_slot(slot: dict, topic: str) -> list[str]:
    base_queries = [query for query in slot.get("searchQueries", []) if isinstance(query, str) and query.strip()]
    role = str(slot.get("role", "")).lower()

    role_queries = {
        "hero": [
            f"{topic} историческая живопись",
            f"{topic} реконструкция",
            f"{topic} архитектура",
        ],
        "section": [
            f"{topic} историческая сцена",
            f"{topic} культура",
            topic,
        ],
        "timeline": [
            f"{topic} карта",
            f"{topic} хронология",
            f"{topic} схема",
        ],
        "person": [
            f"{topic} портрет правителя",
            f"{topic} князь",
            f"{topic} исторический портрет",
        ],
        "artifact": [
            f"{topic} артефакт",
            f"{topic} архитектура",
            f"{topic} предметы культуры",
        ],
        "quote": [
            f"{topic} рукопись",
            f"{topic} летопись",
            f"{topic} исторический документ",
        ],
    }.get(role, [topic])

    ordered_queries: list[str] = []
    for query in [*role_queries, *base_queries]:
        normalized = query.strip()
        if normalized and normalized not in ordered_queries:
            ordered_queries.append(normalized)
    return ordered_queries[:6]


async def _enrich_layout_assets(lesson: dict) -> dict:
    layout = deepcopy(lesson["lessonLayout"])
    visual_mode = lesson["visualMode"]
    hero_slot_id = layout["hero"]["slotId"]
    settings = get_settings()

    for slot in layout["imageSlots"]:
        queries = _queries_for_slot(slot, lesson["topic"])
        candidates = []
        if settings.enable_external_media_search:
            try:
                candidates = [asset.model_dump() for asset in await search_wikimedia_assets(queries, limit=6)]
            except Exception:
                candidates = []

        selected_asset: dict | None = candidates[0] if candidates else None

        if slot["slotId"] == hero_slot_id and not selected_asset and settings.openai_api_key and not settings.use_demo_ai:
            ai_asset = await generate_ai_hero_asset(lesson["topic"], lesson["heroSubtitle"], visual_mode)
            if ai_asset:
                selected_asset = ai_asset.model_dump()
                candidates = [selected_asset]

        if not selected_asset:
            fallback = _pick_default_asset(slot, visual_mode).model_dump()
            selected_asset = fallback
            candidates = candidates or [fallback]

        slot["selectedAsset"] = selected_asset
        slot["candidateAssets"] = candidates[:6]

    lesson["lessonLayout"] = LessonLayout.model_validate(layout).model_dump()
    return lesson


async def _generate_blueprint_via_openai(topic: str) -> dict:
    settings = get_settings()
    request_payload = {
        "model": settings.openai_model,
        "input": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Тема урока: {topic}. "
                    "Сгенерируй визуальный урок истории для школьного проекта с ярким hero и насыщенными секциями."
                ),
            },
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "history_visual_lesson",
                "strict": True,
                "schema": BLUEPRINT_SCHEMA,
            }
        },
    }

    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{settings.openai_base_url.rstrip('/')}/responses",
            headers=headers,
            json=request_payload,
        )

    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"OpenAI API error: {response.text}")

    output_text = _extract_output_text(response.json())
    if not output_text:
        raise HTTPException(status_code=502, detail="OpenAI response did not contain output_text.")

    try:
        return json.loads(output_text)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail=f"Invalid JSON from OpenAI: {exc}") from exc


async def generate_lesson(topic: str) -> dict:
    settings = get_settings()
    lesson = build_demo_lesson(topic) if settings.use_demo_ai or not settings.openai_api_key else await _generate_blueprint_via_openai(topic)
    lesson["topic"] = topic.strip()
    lesson["visualMode"] = lesson.get("visualMode") or lesson.get("lessonLayout", {}).get("visualMode") or infer_visual_mode(topic)
    lesson["lessonLayout"]["visualMode"] = lesson["visualMode"]
    lesson = await _enrich_layout_assets(lesson)
    return GenerateLessonResponse.model_validate(lesson).model_dump()
