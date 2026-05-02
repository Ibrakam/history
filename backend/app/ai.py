from __future__ import annotations

import asyncio
import json
import re
from copy import deepcopy
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException

from .config import get_settings
from .demo_content import build_demo_lesson
from .media import build_demo_asset, build_search_queries, generate_ai_hero_asset, search_wikimedia_assets
from .schemas import GenerateLessonResponse, LessonLayout, MediaAsset
from .source_materials import SourceChunk, build_source_quiz, format_source_context, search_materials
from .theme_logic import infer_visual_mode

VALID_VISUAL_MODES = {"chronicle", "empire", "warfront", "reform", "archive"}
VALID_SECTION_TYPES = {"narrative", "timeline", "person_card_grid", "artifact_gallery", "quote_callout"}
REQUIRED_SECTION_TYPES = ["narrative", "timeline", "person_card_grid", "artifact_gallery", "quote_callout"]


BLUEPRINT_SCHEMA = {
    "type": "object",
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
            "properties": {
                "visualMode": {
                    "type": "string",
                    "enum": ["chronicle", "empire", "warfront", "reform", "archive"],
                },
                "hero": {
                    "type": "object",
                    "properties": {
                        "eyebrow": {"type": "string"},
                        "intro": {"type": "string"},
                        "slotId": {"type": "string"},
                    },
                    "required": ["eyebrow", "intro", "slotId"],
                },
                "sections": {
                    "type": "array",
                    "items": {
                        "type": "object",
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
                                    "properties": {
                                        "year": {"type": "string"},
                                        "title": {"type": "string"},
                                        "description": {"type": "string"},
                                    },
                                    "required": ["year", "title", "description"],
                                },
                            },
                            "personCards": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "role": {"type": "string"},
                                        "summary": {"type": "string"},
                                        "slotId": {"type": ["string", "null"]},
                                    },
                                    "required": ["name", "role", "summary", "slotId"],
                                },
                            },
                            "artifactCards": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "title": {"type": "string"},
                                        "summary": {"type": "string"},
                                        "slotId": {"type": ["string", "null"]},
                                    },
                                    "required": ["title", "summary", "slotId"],
                                },
                            },
                            "quoteText": {"type": ["string", "null"]},
                            "quoteCaption": {"type": ["string", "null"]},
                            "slotId": {"type": ["string", "null"]},
                            "visible": {"type": "boolean"},
                        },
                        "required": ["id", "blockType", "title"],
                    },
                },
                "imageSlots": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "slotId": {"type": "string"},
                            "label": {"type": "string"},
                            "searchQueries": {"type": "array", "items": {"type": "string"}},
                            "role": {"type": "string"},
                        },
                        "required": ["slotId", "label", "searchQueries", "role"],
                    },
                },
            },
            "required": ["visualMode", "hero", "sections", "imageSlots"],
        },
        "quiz": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string"},
                    "options": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "correctOptionIndex": {"type": "integer"},
                    "explanation": {"type": "string"},
                },
                "required": ["prompt", "options", "correctOptionIndex", "explanation"],
            },
        },
    },
    "required": ["title", "topic", "heroSubtitle", "visualMode", "lessonLayout", "quiz"],
}


SYSTEM_PROMPT = """
Ты создаёшь визуальный школьный урок истории на русском языке.
Верни строго JSON по схеме.

Требования:
- Корневой объект обязан содержать ключи: title, topic, heroSubtitle, visualMode, lessonLayout, quiz.
- Пиши понятно для школьника 7-11 класса.
- Сформируй красивую структуру урока как лендинг.
- Всегда делай hero, narrative, timeline, person_card_grid, artifact_gallery и quote_callout.
- Для каждого image slot дай 2-3 поисковых запроса на русском, чтобы найти исторические изображения или карты.
- Для person_card_grid и artifact_gallery старайся давать 2-4 карточки.
- visualMode выбери из chronicle, empire, warfront, reform, archive.
- Не вставляй HTML и CSS, только чистые данные.
- Если даны фрагменты учебников, основное содержание урока и тест должны опираться на них.
- Не выдумывай точные даты, имена, термины и причины, если их нет в источниках.
- Тест должен быть строго по теме урока и по источникам: 5-7 вопросов, каждый с 4 вариантами ответа и только одним правильным.
- Вопросы теста должны проверять факты, причины, последствия, термины, личности или хронологию, а не общие рассуждения.
- Неправильные варианты должны быть правдоподобными, но однозначно неверными по источникам.
- Для всех полей секций всегда возвращай значение: если поле не используется, ставь null или [].
- Для каждой секции обязательно заполни поля: id, blockType, title, lead, body, timelineItems, personCards, artifactCards, quoteText, quoteCaption, slotId, visible.
""".strip()


def _first_mapping_value(mapping: dict, *keys: str):
    for key in keys:
        if key in mapping:
            return mapping[key]
    return None


def _as_text(value, fallback: str = "") -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    if value is not None and not isinstance(value, (dict, list, tuple, set)):
        text = str(value).strip()
        if text:
            return text
    return fallback


def _as_text_list(value) -> list[str]:
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    if isinstance(value, list):
        return [_as_text(item) for item in value if _as_text(item)]
    return []


def _normalize_visual_mode(value, topic: str) -> str:
    text = _as_text(value)
    if text in VALID_VISUAL_MODES:
        return text
    return infer_visual_mode(topic)


def _normalize_section(section: dict, fallback: dict | None = None) -> dict:
    fallback = fallback or {}
    defaults = {
        "id": fallback.get("id", "section"),
        "blockType": fallback.get("blockType", "narrative"),
        "title": fallback.get("title", "Раздел урока"),
        "lead": fallback.get("lead"),
        "body": deepcopy(fallback.get("body", [])),
        "timelineItems": deepcopy(fallback.get("timelineItems", [])),
        "personCards": deepcopy(fallback.get("personCards", [])),
        "artifactCards": deepcopy(fallback.get("artifactCards", [])),
        "quoteText": fallback.get("quoteText"),
        "quoteCaption": fallback.get("quoteCaption"),
        "slotId": fallback.get("slotId"),
        "visible": fallback.get("visible", True),
    }
    normalized = dict(defaults)
    normalized.update(section)
    normalized["id"] = _as_text(_first_mapping_value(normalized, "id", "sectionId", "section_id"), defaults["id"])
    block_type = _as_text(_first_mapping_value(normalized, "blockType", "block_type"), defaults["blockType"])
    normalized["blockType"] = block_type if block_type in VALID_SECTION_TYPES else defaults["blockType"]
    normalized["title"] = _as_text(normalized.get("title"), defaults["title"])
    normalized["lead"] = _as_text(normalized.get("lead")) or None
    normalized["body"] = _as_text_list(normalized.get("body")) or _as_text_list(defaults.get("body"))
    normalized["quoteText"] = _as_text(_first_mapping_value(normalized, "quoteText", "quote_text")) or None
    normalized["quoteCaption"] = _as_text(_first_mapping_value(normalized, "quoteCaption", "quote_caption")) or None
    normalized["slotId"] = _as_text(_first_mapping_value(normalized, "slotId", "slot_id")) or None
    normalized["visible"] = bool(normalized.get("visible", True))

    timeline_items = []
    for index, item in enumerate(normalized.get("timelineItems") or normalized.get("timeline_items") or []):
        if isinstance(item, dict):
            timeline_items.append(
                {
                    "year": _as_text(item.get("year"), f"{index + 1} этап"),
                    "title": _as_text(item.get("title"), "Событие"),
                    "description": _as_text(item.get("description"), "Краткое описание события."),
                }
            )
        elif _as_text(item):
            timeline_items.append({"year": f"{index + 1} этап", "title": _as_text(item), "description": _as_text(item)})
    normalized["timelineItems"] = timeline_items or deepcopy(defaults.get("timelineItems", []))

    person_cards = []
    for item in normalized.get("personCards") or normalized.get("person_cards") or []:
        if isinstance(item, dict):
            person_cards.append(
                {
                    "name": _as_text(item.get("name"), "Историческая личность"),
                    "role": _as_text(item.get("role"), "Участник событий"),
                    "summary": _as_text(item.get("summary"), "Связан с ключевыми событиями темы."),
                    "slotId": _as_text(_first_mapping_value(item, "slotId", "slot_id")) or None,
                }
            )
    normalized["personCards"] = person_cards or deepcopy(defaults.get("personCards", []))

    artifact_cards = []
    for item in normalized.get("artifactCards") or normalized.get("artifact_cards") or []:
        if isinstance(item, dict):
            artifact_cards.append(
                {
                    "title": _as_text(item.get("title"), "Артефакт эпохи"),
                    "summary": _as_text(item.get("summary"), "Материальный след, который помогает понять тему."),
                    "slotId": _as_text(_first_mapping_value(item, "slotId", "slot_id")) or None,
                }
            )
    normalized["artifactCards"] = artifact_cards or deepcopy(defaults.get("artifactCards", []))

    return normalized


GENERIC_QUIZ_MARKERS = (
    "с чего лучше начинать",
    "зачем включать",
    "что делает урок более понятным",
    "просто занять место",
    "причинно-следственная логика",
)


def _question_is_grounded(question: dict, topic: str, source_chunks: list[SourceChunk]) -> bool:
    text = " ".join(
        [
            _as_text(question.get("prompt")),
            " ".join(_as_text_list(question.get("options"))),
            _as_text(question.get("explanation")),
        ]
    ).lower()
    if any(marker in text for marker in GENERIC_QUIZ_MARKERS):
        return False
    if not source_chunks:
        return True

    topic_tokens = set(_as_text_list(topic)) or set()
    topic_tokens = {token for token in re.findall(r"[A-Za-zА-Яа-яЁёЎўҚқҒғҲҳІіʼ'’-]{3,}|\d{3,4}", topic.lower())}
    source_tokens = {
        token
        for chunk in source_chunks
        for token in re.findall(r"[A-Za-zА-Яа-яЁёЎўҚқҒғҲҳІіʼ'’-]{3,}|\d{3,4}", chunk.text.lower())
    }
    question_tokens = set(re.findall(r"[A-Za-zА-Яа-яЁёЎўҚқҒғҲҳІіʼ'’-]{3,}|\d{3,4}", text))
    return bool(question_tokens & topic_tokens) and len(question_tokens & source_tokens) >= 4


def _normalize_quiz(questions, fallback_questions: list[dict], topic: str, source_chunks: list[SourceChunk]) -> list[dict]:
    normalized: list[dict] = []
    for index, question in enumerate(questions if isinstance(questions, list) else []):
        if not isinstance(question, dict):
            continue
        fallback = fallback_questions[min(index, len(fallback_questions) - 1)]
        options = _as_text_list(question.get("options"))
        if len(options) < 4:
            options = [*options, *fallback["options"]]
        options = options[:4]
        try:
            correct_index = int(_first_mapping_value(question, "correctOptionIndex", "correct_option_index") or 0)
        except (TypeError, ValueError):
            correct_index = 0
        if not (0 <= correct_index <= 3):
            correct_index = 0
        normalized_question = {
            "prompt": _as_text(question.get("prompt"), fallback["prompt"]),
            "options": options,
            "correctOptionIndex": correct_index,
            "explanation": _as_text(question.get("explanation"), fallback["explanation"]),
        }
        if _question_is_grounded(normalized_question, topic, source_chunks):
            normalized.append(normalized_question)

    target_count = min(max(len(fallback_questions), 5), 7)
    for fallback in fallback_questions:
        if len(normalized) >= target_count:
            break
        normalized.append(deepcopy(fallback))
    return normalized


def _normalize_image_slots(slots, fallback_slots: list[dict], topic: str) -> list[dict]:
    normalized_by_id: dict[str, dict] = {}

    def add_slot(slot: dict, fallback: dict | None = None) -> None:
        fallback = fallback or {}
        slot_id = _as_text(_first_mapping_value(slot, "slotId", "slot_id"), fallback.get("slotId", ""))
        if not slot_id:
            return
        label = _as_text(slot.get("label"), fallback.get("label", topic))
        role = _as_text(slot.get("role"), fallback.get("role", "section"))
        search_queries = _as_text_list(_first_mapping_value(slot, "searchQueries", "search_queries")) or _as_text_list(
            fallback.get("searchQueries")
        )
        normalized_by_id[slot_id] = {
            "slotId": slot_id,
            "label": label,
            "searchQueries": search_queries,
            "role": role,
        }

    for slot in fallback_slots:
        add_slot(slot)
    for index, slot in enumerate(slots if isinstance(slots, list) else []):
        if isinstance(slot, dict):
            add_slot(slot, fallback_slots[min(index, len(fallback_slots) - 1)] if fallback_slots else None)

    return list(normalized_by_id.values())


def _build_source_fallback_lesson(topic: str, source_chunks: list[SourceChunk]) -> dict:
    lesson = build_demo_lesson(topic)
    if not source_chunks:
        return lesson

    statements = []
    for chunk in source_chunks[:5]:
        for sentence in re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", chunk.text)):
            sentence = sentence.strip()
            if 50 <= len(sentence) <= 260:
                statements.append(sentence)
            if len(statements) >= 8:
                break
        if len(statements) >= 8:
            break

    visual_mode = infer_visual_mode(topic)
    lesson["title"] = f"{topic.strip()}: материал по учебнику"
    lesson["heroSubtitle"] = "Урок собран на основе загруженных школьных материалов и базовой лекции."
    lesson["visualMode"] = visual_mode
    lesson["lessonLayout"]["visualMode"] = visual_mode
    lesson["lessonLayout"]["hero"]["intro"] = (
        "Разберём тему по фрагментам учебника: ключевые факты, причины, последствия и проверочные вопросы."
    )

    sections = lesson["lessonLayout"]["sections"]
    sections[0]["title"] = "По учебнику"
    sections[0]["lead"] = "Главные сведения взяты из найденных фрагментов школьного материала."
    sections[0]["body"] = statements[:3] or [source_chunks[0].text[:500]]

    timeline_items = []
    for statement in statements:
        year_match = re.search(r"\b(\d{3,4})\b", statement)
        if year_match:
            timeline_items.append(
                {
                    "year": year_match.group(1),
                    "title": "Событие из учебника",
                    "description": statement,
                }
            )
        if len(timeline_items) >= 4:
            break
    if timeline_items:
        sections[1]["timelineItems"] = timeline_items

    if len(statements) > 3:
        sections[3]["artifactCards"] = [
            {
                "title": "Фрагмент учебного материала",
                "summary": statements[3],
                "slotId": "artifact-1",
            }
        ]
    if statements:
        sections[4]["quoteText"] = statements[0]
        sections[4]["quoteCaption"] = source_chunks[0].sourceTitle

    source_quiz = build_source_quiz(topic, source_chunks)
    if source_quiz:
        lesson["quiz"] = source_quiz
    return lesson


def _validate_and_fix_blueprint(data: dict, topic: str, source_chunks: list[SourceChunk] | None = None) -> dict:
    if not isinstance(data, dict):
        raise ValueError("AI response root must be an object")

    source_chunks = source_chunks or []
    demo = _build_source_fallback_lesson(topic, source_chunks)
    demo_layout = demo["lessonLayout"]
    source_layout = _first_mapping_value(data, "lessonLayout", "lesson_layout", "layout")
    if not isinstance(source_layout, dict):
        source_layout = {}

    visual_mode = _normalize_visual_mode(
        _first_mapping_value(data, "visualMode", "visual_mode") or _first_mapping_value(source_layout, "visualMode", "visual_mode"),
        topic,
    )

    hero_source = source_layout.get("hero") if isinstance(source_layout.get("hero"), dict) else {}
    hero = {
        "eyebrow": _as_text(hero_source.get("eyebrow"), demo_layout["hero"]["eyebrow"]),
        "intro": _as_text(hero_source.get("intro"), demo_layout["hero"]["intro"]),
        "slotId": _as_text(_first_mapping_value(hero_source, "slotId", "slot_id"), demo_layout["hero"]["slotId"]),
    }

    fallback_sections_by_type = {section["blockType"]: section for section in demo_layout["sections"]}
    raw_sections = source_layout.get("sections") if isinstance(source_layout.get("sections"), list) else []
    sections: list[dict] = []
    for raw_section in raw_sections:
        if not isinstance(raw_section, dict):
            continue
        raw_type = _as_text(_first_mapping_value(raw_section, "blockType", "block_type"))
        fallback = fallback_sections_by_type.get(raw_type) or demo_layout["sections"][min(len(sections), len(demo_layout["sections"]) - 1)]
        sections.append(_normalize_section(raw_section, fallback))

    present_types = {section["blockType"] for section in sections}
    for section_type in REQUIRED_SECTION_TYPES:
        if section_type not in present_types:
            sections.append(_normalize_section(deepcopy(fallback_sections_by_type[section_type])))

    image_slots = _normalize_image_slots(
        _first_mapping_value(source_layout, "imageSlots", "image_slots"),
        demo_layout["imageSlots"],
        topic,
    )
    slot_ids = {slot["slotId"] for slot in image_slots}

    def ensure_slot(slot_id: str | None, label: str, role: str) -> None:
        if not slot_id or slot_id in slot_ids:
            return
        image_slots.append({"slotId": slot_id, "label": label, "searchQueries": [topic, label], "role": role})
        slot_ids.add(slot_id)

    ensure_slot(hero["slotId"], f"{topic} hero", "hero")
    for section in sections:
        ensure_slot(section.get("slotId"), section["title"], section["blockType"])
        for card in section.get("personCards", []):
            ensure_slot(card.get("slotId"), card["name"], "person")
        for card in section.get("artifactCards", []):
            ensure_slot(card.get("slotId"), card["title"], "artifact")

    return {
        "title": _as_text(data.get("title"), demo["title"]),
        "topic": _as_text(data.get("topic"), topic.strip() or demo["topic"]),
        "heroSubtitle": _as_text(_first_mapping_value(data, "heroSubtitle", "hero_subtitle", "subtitle"), demo["heroSubtitle"]),
        "visualMode": visual_mode,
        "lessonLayout": {
            "visualMode": visual_mode,
            "hero": hero,
            "sections": sections,
            "imageSlots": image_slots,
        },
        "quiz": _normalize_quiz(data.get("quiz"), demo["quiz"], topic, source_chunks),
    }


def _extract_ai_json(content: str) -> dict:
    cleaned = content.strip()
    fence_match = re.search(r"```(?:json)?\s*(.*?)```", cleaned, flags=re.DOTALL | re.IGNORECASE)
    if fence_match:
        cleaned = fence_match.group(1).strip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        decoder = json.JSONDecoder()
        parsed = None
        for index, char in enumerate(cleaned):
            if char != "{":
                continue
            try:
                parsed, _ = decoder.raw_decode(cleaned[index:])
                break
            except json.JSONDecodeError:
                continue
        if parsed is None:
            raise

    if not isinstance(parsed, dict):
        raise ValueError("AI JSON must be an object")

    for key in ("lesson", "data", "result", "response"):
        nested = parsed.get(key)
        if isinstance(nested, dict):
            return nested
    return parsed


def _message_content_to_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                parts.append(_as_text(item.get("text") or item.get("content")))
            else:
                parts.append(_as_text(item))
        return "\n".join(part for part in parts if part)
    return _as_text(content)


def _is_local_ai_base_url(base_url: str) -> bool:
    host = (urlparse(base_url).hostname or "").lower()
    return host in {"localhost", "127.0.0.1", "0.0.0.0", "::1"}


def _should_use_ai() -> bool:
    settings = get_settings()
    if settings.use_demo_ai or not settings.openai_model or not settings.openai_base_url:
        return False
    if settings.openai_api_key:
        return True
    return _is_local_ai_base_url(settings.openai_base_url)


def _build_generation_user_prompt(topic: str, source_chunks: list[SourceChunk]) -> str:
    settings = get_settings()
    is_local_ai = _is_local_ai_base_url(settings.openai_base_url)
    prompt_chunks = source_chunks[:4] if is_local_ai else source_chunks
    prompt_chunk_chars = 650 if is_local_ai else 1400
    base = (
        f"Тема урока: {topic}. "
        "Сгенерируй визуальный урок истории для школьного проекта с ярким hero и насыщенными секциями."
    )
    if not source_chunks:
        return (
            f"{base}\n\n"
            "Фрагменты учебников не найдены. Сгенерируй аккуратный обзор без спорных деталей, "
            "а тест сделай только по фактам, которые сам объяснил в уроке."
        )

    return (
        f"{base}\n\n"
        "Ниже фрагменты школьных материалов. Основные факты, объяснения и все вопросы теста бери из них. "
        "Можно сжать и переформулировать текст, но нельзя добавлять неподтвержденные точные сведения.\n\n"
        f"{format_source_context(prompt_chunks, max_chars=prompt_chunk_chars)}"
    )


def _pick_default_asset(slot: dict, visual_mode: str) -> MediaAsset:
    return build_demo_asset(slot["label"], visual_mode, slot["slotId"])


async def _enrich_layout_assets(lesson: dict) -> dict:
    layout = deepcopy(lesson["lessonLayout"])
    visual_mode = lesson["visualMode"]
    hero_slot_id = layout["hero"]["slotId"]
    settings = get_settings()

    for slot in layout["imageSlots"]:
        queries = build_search_queries(slot.get("label", ""), lesson["topic"], slot.get("role", "section"), slot.get("searchQueries"))
        slot["searchQueries"] = queries
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


async def _generate_blueprint_via_chat(topic: str, source_chunks: list[SourceChunk] | None = None) -> dict:
    settings = get_settings()
    source_chunks = source_chunks or []
    is_local_ai = _is_local_ai_base_url(settings.openai_base_url)
    request_payload = {
        "model": settings.openai_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_generation_user_prompt(topic, source_chunks)},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.4 if is_local_ai else 0.7,
    }
    if is_local_ai:
        request_payload["max_tokens"] = 1800

    headers = {
        "Content-Type": "application/json",
    }
    if settings.openai_api_key:
        headers["Authorization"] = f"Bearer {settings.openai_api_key}"

    async with asyncio.timeout(settings.ai_request_timeout):
        async with httpx.AsyncClient(timeout=settings.ai_request_timeout) as client:
            response = await client.post(
                f"{settings.openai_base_url.rstrip('/')}/chat/completions",
                headers=headers,
                json=request_payload,
            )
            if response.status_code == 400 and "response_format" in request_payload:
                fallback_payload = dict(request_payload)
                fallback_payload.pop("response_format", None)
                response = await client.post(
                    f"{settings.openai_base_url.rstrip('/')}/chat/completions",
                    headers=headers,
                    json=fallback_payload,
                )

    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"AI API error ({response.status_code}): {response.text[:500]}")

    data = response.json()
    content = _message_content_to_text(data.get("choices", [{}])[0].get("message", {}).get("content", ""))
    if not content:
        raise HTTPException(status_code=502, detail="AI response did not contain content.")

    try:
        blueprint = _extract_ai_json(content)
    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=f"Invalid JSON from AI: {exc}") from exc

    try:
        blueprint = _validate_and_fix_blueprint(blueprint, topic, source_chunks)
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=f"AI returned incomplete lesson structure: {exc}") from exc

    return blueprint


async def generate_lesson(topic: str, material_collection: str = "auto") -> dict:
    settings = get_settings()
    use_ai = _should_use_ai()
    is_local_ai = _is_local_ai_base_url(settings.openai_base_url)
    collection = None if material_collection == "auto" else material_collection
    source_chunks = search_materials(topic, collection=collection) if use_ai else []
    if use_ai and settings.enable_source_materials and not source_chunks:
        scope = "загруженных материалах" if not collection else f"разделе материалов «{collection}»"
        raise HTTPException(
            status_code=422,
            detail=(
                f"Не нашёл достаточно релевантных фрагментов по теме «{topic}» в {scope}. "
                "Выберите другой раздел источников или добавьте учебник с этой темой."
            ),
        )
    if not use_ai:
        lesson = build_demo_lesson(topic)
    else:
        try:
            lesson = await _generate_blueprint_via_chat(topic, source_chunks)
        except (HTTPException, TimeoutError, httpx.HTTPError):
            if not source_chunks or not is_local_ai:
                raise
            lesson = _build_source_fallback_lesson(topic, source_chunks)

    lesson["topic"] = topic.strip()
    lesson["visualMode"] = lesson.get("visualMode") or lesson.get("lessonLayout", {}).get("visualMode") or infer_visual_mode(topic)
    lesson["lessonLayout"]["visualMode"] = lesson["visualMode"]
    lesson = await _enrich_layout_assets(lesson)
    return GenerateLessonResponse.model_validate(lesson).model_dump()
