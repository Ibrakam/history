from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone

from slugify import slugify
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .media import build_demo_asset, build_search_queries, generate_ai_hero_asset, search_wikimedia_assets
from .models import Lesson, LessonStatus, QuizAttempt, QuizQuestion
from .sanitization import sanitize_lesson_html
from .schemas import AdminQuizQuestion, ImageSlot, LessonLayout, LessonSaveRequest


def normalize_visual_mode(visual_mode: str) -> str:
    if visual_mode in {"chronicle", "empire", "warfront", "reform", "archive"}:
        return visual_mode
    return "chronicle"


def _make_image_slot(slot_id: str, label: str, role: str, topic: str) -> dict:
    return {
        "slotId": slot_id,
        "label": label,
        "searchQueries": build_search_queries(label, topic, role),
        "selectedAsset": None,
        "candidateAssets": [],
        "role": role,
    }


def ensure_lesson_layout_slots(db: Session, lesson: Lesson) -> Lesson:
    layout = deepcopy(lesson.lesson_layout or {})
    if not layout:
        return lesson

    slots = layout.setdefault("imageSlots", [])
    slot_ids = {slot.get("slotId") for slot in slots if slot.get("slotId")}
    changed = False

    for slot in slots:
        if "searchQueries" not in slot:
            slot["searchQueries"] = build_search_queries(slot.get("label", lesson.topic), lesson.topic, slot.get("role", "section"))
            changed = True
        if "candidateAssets" not in slot:
            slot["candidateAssets"] = [slot["selectedAsset"]] if slot.get("selectedAsset") else []
            changed = True

    hero = layout.get("hero") or {}
    hero_slot_id = hero.get("slotId")
    if hero_slot_id and hero_slot_id not in slot_ids:
        slots.insert(0, _make_image_slot(hero_slot_id, lesson.title, "hero", lesson.topic))
        slot_ids.add(hero_slot_id)
        changed = True

    role_by_block = {
        "narrative": "section",
        "timeline": "timeline",
        "person_card_grid": "person",
        "artifact_gallery": "artifact",
        "quote_callout": "quote",
    }

    for section in layout.get("sections", []):
        role = role_by_block.get(section.get("blockType"), "section")
        section_slot_id = section.get("slotId")
        if section_slot_id and section_slot_id not in slot_ids:
            slots.append(_make_image_slot(section_slot_id, section.get("title", lesson.title), role, lesson.topic))
            slot_ids.add(section_slot_id)
            changed = True

        for person in section.get("personCards", []):
            person_slot_id = person.get("slotId")
            if person_slot_id and person_slot_id not in slot_ids:
                slots.append(_make_image_slot(person_slot_id, person.get("name", lesson.title), "person", lesson.topic))
                slot_ids.add(person_slot_id)
                changed = True

        for artifact in section.get("artifactCards", []):
            artifact_slot_id = artifact.get("slotId")
            if artifact_slot_id and artifact_slot_id not in slot_ids:
                slots.append(_make_image_slot(artifact_slot_id, artifact.get("title", lesson.title), "artifact", lesson.topic))
                slot_ids.add(artifact_slot_id)
                changed = True

    if changed:
        lesson.lesson_layout = layout
        db.add(lesson)
        db.commit()
        db.refresh(lesson)

    return lesson


def build_unique_slug(db: Session, title: str, lesson_id: int | None = None) -> str:
    base_slug = slugify(title, lowercase=True) or "lesson"
    slug = base_slug
    counter = 2
    while True:
        query = select(Lesson).where(Lesson.slug == slug)
        if lesson_id is not None:
            query = query.where(Lesson.id != lesson_id)
        existing = db.scalar(query)
        if not existing:
            return slug
        slug = f"{base_slug}-{counter}"
        counter += 1


def serialize_admin_question(question: QuizQuestion) -> AdminQuizQuestion:
    return AdminQuizQuestion(
        prompt=question.prompt,
        options=question.options,
        correctOptionIndex=question.correct_option_index,
        explanation=question.explanation,
    )


def _sanitize_lesson_layout(layout: LessonLayout | dict | None, visual_mode: str) -> dict | None:
    if not layout:
        return None

    layout_model = LessonLayout.model_validate(layout)
    payload = layout_model.model_dump()
    payload["visualMode"] = normalize_visual_mode(visual_mode)
    return payload


def _build_public_layout(layout: dict | None) -> dict | None:
    if not layout:
        return None

    public_layout = deepcopy(layout)
    for slot in public_layout.get("imageSlots", []):
        slot["searchQueries"] = []
        slot["candidateAssets"] = []
    return public_layout


def lesson_to_detail(lesson: Lesson) -> dict:
    return {
        "id": lesson.id,
        "title": lesson.title,
        "topic": lesson.topic,
        "slug": lesson.slug,
        "heroSubtitle": lesson.hero_subtitle,
        "visualMode": normalize_visual_mode(lesson.theme_key),
        "lessonLayout": lesson.lesson_layout,
        "lessonHtml": lesson.lesson_html,
        "status": lesson.status.value,
        "createdAt": lesson.created_at,
        "updatedAt": lesson.updated_at,
        "publishedAt": lesson.published_at,
        "quiz": [serialize_admin_question(question) for question in lesson.quiz_questions],
    }


def lesson_to_public_detail(lesson: Lesson) -> dict:
    return {
        "id": lesson.id,
        "title": lesson.title,
        "topic": lesson.topic,
        "slug": lesson.slug,
        "heroSubtitle": lesson.hero_subtitle,
        "visualMode": normalize_visual_mode(lesson.theme_key),
        "lessonLayout": _build_public_layout(lesson.lesson_layout),
        "lessonHtml": lesson.lesson_html,
        "publishedAt": lesson.published_at,
        "quiz": [
            {
                "id": question.id,
                "prompt": question.prompt,
                "options": question.options,
                "explanation": question.explanation,
            }
            for question in lesson.quiz_questions
        ],
    }


def create_lesson(db: Session, payload: LessonSaveRequest) -> Lesson:
    lesson = Lesson(
        title=payload.title.strip(),
        topic=payload.topic.strip(),
        slug=build_unique_slug(db, payload.title),
        hero_subtitle=payload.heroSubtitle.strip(),
        lesson_html=sanitize_lesson_html(payload.lessonHtml) if payload.lessonHtml else "",
        lesson_layout=_sanitize_lesson_layout(payload.lessonLayout, payload.visualMode),
        theme_key=normalize_visual_mode(payload.visualMode),
        status=LessonStatus.DRAFT,
    )
    lesson.quiz_questions = [
        QuizQuestion(
            position=index,
            prompt=question.prompt.strip(),
            options=question.options,
            correct_option_index=question.correctOptionIndex,
            explanation=question.explanation.strip(),
        )
        for index, question in enumerate(payload.quiz)
    ]
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return get_lesson_by_id(db, lesson.id)


def update_lesson(db: Session, lesson: Lesson, payload: LessonSaveRequest) -> Lesson:
    lesson.title = payload.title.strip()
    lesson.topic = payload.topic.strip()
    lesson.slug = build_unique_slug(db, payload.title, lesson.id)
    lesson.hero_subtitle = payload.heroSubtitle.strip()
    lesson.lesson_html = sanitize_lesson_html(payload.lessonHtml) if payload.lessonHtml else ""
    lesson.lesson_layout = _sanitize_lesson_layout(payload.lessonLayout, payload.visualMode)
    lesson.theme_key = normalize_visual_mode(payload.visualMode)
    lesson.quiz_questions.clear()
    lesson.quiz_questions.extend(
        [
            QuizQuestion(
                position=index,
                prompt=question.prompt.strip(),
                options=question.options,
                correct_option_index=question.correctOptionIndex,
                explanation=question.explanation.strip(),
            )
            for index, question in enumerate(payload.quiz)
        ]
    )
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return get_lesson_by_id(db, lesson.id)


def get_lessons(db: Session) -> list[Lesson]:
    query = select(Lesson).order_by(Lesson.updated_at.desc())
    return list(db.scalars(query))


def get_lesson_by_id(db: Session, lesson_id: int) -> Lesson | None:
    query = (
        select(Lesson)
        .where(Lesson.id == lesson_id)
        .options(selectinload(Lesson.quiz_questions))
    )
    lesson = db.scalar(query)
    if not lesson:
        return None
    return ensure_lesson_layout_slots(db, lesson)


def get_published_lesson_by_slug(db: Session, slug: str) -> Lesson | None:
    query = (
        select(Lesson)
        .where(Lesson.slug == slug, Lesson.status == LessonStatus.PUBLISHED)
        .options(selectinload(Lesson.quiz_questions))
    )
    lesson = db.scalar(query)
    if not lesson:
        return None
    return ensure_lesson_layout_slots(db, lesson)


def delete_lesson(db: Session, lesson: Lesson) -> None:
    db.delete(lesson)
    db.commit()


def publish_lesson(db: Session, lesson: Lesson) -> Lesson:
    lesson.status = LessonStatus.PUBLISHED
    lesson.published_at = datetime.now(timezone.utc)
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return get_lesson_by_id(db, lesson.id)


def unpublish_lesson(db: Session, lesson: Lesson) -> Lesson:
    lesson.status = LessonStatus.DRAFT
    lesson.published_at = None
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return get_lesson_by_id(db, lesson.id)


async def refresh_lesson_slot_images(db: Session, lesson: Lesson, slot_id: str) -> ImageSlot:
    lesson = ensure_lesson_layout_slots(db, lesson)
    layout = deepcopy(lesson.lesson_layout or {})
    slots = layout.get("imageSlots", [])
    slot = next((item for item in slots if item.get("slotId") == slot_id), None)
    if not slot:
        raise ValueError("Слот изображения не найден.")

    queries = slot.get("searchQueries") or [slot.get("label", lesson.topic), lesson.topic]
    try:
        candidates = [asset.model_dump() for asset in await search_wikimedia_assets(queries, limit=6)]
    except Exception:
        candidates = []

    hero_slot_id = layout.get("hero", {}).get("slotId")
    if not candidates and slot_id == hero_slot_id:
        ai_asset = await generate_ai_hero_asset(lesson.topic, lesson.hero_subtitle, lesson.theme_key)
        if ai_asset:
            candidates = [ai_asset.model_dump()]

    if not candidates:
        fallback = build_demo_asset(slot.get("label", lesson.topic), lesson.theme_key, slot_id).model_dump()
        candidates = [fallback]

    slot["candidateAssets"] = candidates[:6]
    slot["selectedAsset"] = candidates[0]
    lesson.lesson_layout = layout
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return ImageSlot.model_validate(slot)


def create_quiz_attempt(
    db: Session,
    lesson_id: int,
    student_name: str,
    score: int,
    total: int,
    percentage: float,
    answers: list[int | None],
) -> QuizAttempt:
    attempt = QuizAttempt(
        lesson_id=lesson_id,
        student_name=student_name,
        score=score,
        total=total,
        percentage=percentage,
        answers=answers,
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return attempt


def get_quiz_attempts(db: Session, lesson_id: int) -> list[QuizAttempt]:
    query = (
        select(QuizAttempt)
        .where(QuizAttempt.lesson_id == lesson_id)
        .order_by(QuizAttempt.created_at.desc())
    )
    return list(db.scalars(query))
