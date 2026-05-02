from __future__ import annotations

import secrets
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response

from ..ai import generate_lesson
from ..config import get_settings
from ..crud import (
    create_lesson,
    delete_lesson,
    get_lesson_by_id,
    get_lessons,
    get_quiz_attempts,
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
    MediaAsset,
    QuizAttemptResponse,
    QuizResultsResponse,
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
    generated = await generate_lesson(payload.topic, payload.materialCollection)
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


@router.get("/lessons/{lesson_id}/quiz-results", response_model=QuizResultsResponse)
def quiz_results(lesson_id: int, db: DbSession, _: str = Depends(require_admin)) -> QuizResultsResponse:
    lesson = get_lesson_by_id(db, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Урок не найден.")
    attempts = get_quiz_attempts(db, lesson_id)
    return QuizResultsResponse(
        lessonId=lesson.id,
        lessonTitle=lesson.title,
        attempts=[
            QuizAttemptResponse(
                id=a.id,
                studentName=a.student_name,
                score=a.score,
                total=a.total,
                percentage=a.percentage,
                createdAt=a.created_at,
            )
            for a in attempts
        ],
    )


ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
ALLOWED_IMAGE_MIME = {"image/jpeg", "image/png", "image/webp", "image/gif"}


@router.post("/uploads/image", response_model=MediaAsset)
async def upload_image(
    file: UploadFile = File(...),
    _: str = Depends(require_admin),
) -> MediaAsset:
    settings = get_settings()
    extension = Path(file.filename or "").suffix.lower()
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Поддерживаются JPG, PNG, WEBP и GIF.")
    if file.content_type and file.content_type not in ALLOWED_IMAGE_MIME:
        raise HTTPException(status_code=400, detail="Неверный тип файла.")

    contents = await file.read()
    if len(contents) > settings.upload_max_bytes:
        max_mb = settings.upload_max_bytes // (1024 * 1024)
        raise HTTPException(status_code=413, detail=f"Файл больше {max_mb} МБ.")
    if not contents:
        raise HTTPException(status_code=400, detail="Пустой файл.")

    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    asset_id = secrets.token_hex(12)
    target = settings.upload_dir / f"{asset_id}{extension}"
    target.write_bytes(contents)

    image_url = f"/api/uploads/{target.name}"
    title = Path(file.filename or "Загруженное изображение").stem or "Загруженное изображение"

    return MediaAsset(
        assetId=f"upload-{asset_id}",
        title=title,
        imageUrl=image_url,
        thumbUrl=image_url,
        sourceUrl=image_url,
        author="Учитель",
        license="custom",
        provider="upload",
        alt=title,
    )


@router.delete("/lessons/{lesson_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_lesson(lesson_id: int, db: DbSession, _: str = Depends(require_admin)) -> Response:
    lesson = get_lesson_by_id(db, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Урок не найден.")
    delete_lesson(db, lesson)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
