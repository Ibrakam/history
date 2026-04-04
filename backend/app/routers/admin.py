from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response

from ..ai import generate_lesson
from ..crud import (
    create_lesson,
    delete_lesson,
    get_lesson_by_id,
    get_lessons,
    lesson_to_detail,
    normalize_visual_mode,
    publish_lesson,
    refresh_lesson_slot_images,
    unpublish_lesson,
    update_lesson,
)
from ..deps import DbSession, require_admin
from ..schemas import (
    AdminMeResponse,
    GenerateLessonRequest,
    GenerateLessonResponse,
    LessonDetail,
    LessonListItem,
    LessonSaveRequest,
    LoginRequest,
    RefreshSlotImagesRequest,
    RefreshSlotImagesResponse,
    TokenResponse,
)
from ..security import create_access_token, verify_admin_credentials


router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest) -> TokenResponse:
    if not verify_admin_credentials(payload.username, payload.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный логин или пароль.")
    return TokenResponse(access_token=create_access_token())


@router.get("/me", response_model=AdminMeResponse)
def me(_: str = Depends(require_admin)) -> AdminMeResponse:
    return AdminMeResponse(username="admin")


@router.get("/lessons", response_model=list[LessonListItem])
def list_lessons(db: DbSession, _: str = Depends(require_admin)) -> list[LessonListItem]:
    lessons = get_lessons(db)
    return [
        LessonListItem.model_validate(
            {
                "id": lesson.id,
                "title": lesson.title,
                "topic": lesson.topic,
                "slug": lesson.slug,
                "themeKey": normalize_visual_mode(lesson.theme_key),
                "status": lesson.status.value,
                "createdAt": lesson.created_at,
                "updatedAt": lesson.updated_at,
                "publishedAt": lesson.published_at,
            }
        )
        for lesson in lessons
    ]


@router.get("/lessons/{lesson_id}", response_model=LessonDetail)
def get_lesson(lesson_id: int, db: DbSession, _: str = Depends(require_admin)) -> LessonDetail:
    lesson = get_lesson_by_id(db, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Урок не найден.")
    return LessonDetail.model_validate(lesson_to_detail(lesson))


@router.post("/lessons/generate", response_model=GenerateLessonResponse)
async def generate(payload: GenerateLessonRequest, _: str = Depends(require_admin)) -> GenerateLessonResponse:
    generated = await generate_lesson(payload.topic)
    return GenerateLessonResponse.model_validate(generated)


@router.post("/lessons", response_model=LessonDetail)
def create(payload: LessonSaveRequest, db: DbSession, _: str = Depends(require_admin)) -> LessonDetail:
    lesson = create_lesson(db, payload)
    return LessonDetail.model_validate(lesson_to_detail(lesson))


@router.put("/lessons/{lesson_id}", response_model=LessonDetail)
def update(lesson_id: int, payload: LessonSaveRequest, db: DbSession, _: str = Depends(require_admin)) -> LessonDetail:
    lesson = get_lesson_by_id(db, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Урок не найден.")
    lesson = update_lesson(db, lesson, payload)
    return LessonDetail.model_validate(lesson_to_detail(lesson))


@router.post("/lessons/{lesson_id}/refresh-slot-images", response_model=RefreshSlotImagesResponse)
async def refresh_slot_images(
    lesson_id: int,
    payload: RefreshSlotImagesRequest,
    db: DbSession,
    _: str = Depends(require_admin),
) -> RefreshSlotImagesResponse:
    lesson = get_lesson_by_id(db, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Урок не найден.")
    try:
        slot = await refresh_lesson_slot_images(db, lesson, payload.slotId)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return RefreshSlotImagesResponse(slot=slot)


@router.post("/lessons/{lesson_id}/publish", response_model=LessonDetail)
def publish(lesson_id: int, db: DbSession, _: str = Depends(require_admin)) -> LessonDetail:
    lesson = get_lesson_by_id(db, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Урок не найден.")
    lesson = publish_lesson(db, lesson)
    return LessonDetail.model_validate(lesson_to_detail(lesson))


@router.post("/lessons/{lesson_id}/unpublish", response_model=LessonDetail)
def unpublish(lesson_id: int, db: DbSession, _: str = Depends(require_admin)) -> LessonDetail:
    lesson = get_lesson_by_id(db, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Урок не найден.")
    lesson = unpublish_lesson(db, lesson)
    return LessonDetail.model_validate(lesson_to_detail(lesson))


@router.delete("/lessons/{lesson_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_lesson(lesson_id: int, db: DbSession, _: str = Depends(require_admin)) -> Response:
    lesson = get_lesson_by_id(db, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Урок не найден.")
    delete_lesson(db, lesson)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
