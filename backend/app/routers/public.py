from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..crud import create_quiz_attempt, get_published_lesson_by_slug, lesson_to_public_detail
from ..deps import DbSession
from ..schemas import PublicLessonDetail, QuizAnswerReview, QuizSubmitRequest, QuizSubmitResponse


router = APIRouter(prefix="/api/public", tags=["public"])


@router.get("/lessons/{slug}", response_model=PublicLessonDetail)
def get_public_lesson(slug: str, db: DbSession) -> PublicLessonDetail:
    lesson = get_published_lesson_by_slug(db, slug)
    if not lesson:
        raise HTTPException(status_code=404, detail="Опубликованный урок не найден.")
    return PublicLessonDetail.model_validate(lesson_to_public_detail(lesson))


@router.post("/lessons/{slug}/submit-quiz", response_model=QuizSubmitResponse)
def submit_quiz(slug: str, payload: QuizSubmitRequest, db: DbSession) -> QuizSubmitResponse:
    lesson = get_published_lesson_by_slug(db, slug)
    if not lesson:
        raise HTTPException(status_code=404, detail="Опубликованный урок не найден.")

    reviews: list[QuizAnswerReview] = []
    score = 0

    for idx, question in enumerate(lesson.quiz_questions):
        selected = payload.answers[idx] if idx < len(payload.answers) else None
        is_correct = selected == question.correct_option_index
        if is_correct:
            score += 1
        reviews.append(
            QuizAnswerReview(
                questionId=question.id,
                prompt=question.prompt,
                selectedOptionIndex=selected,
                correctOptionIndex=question.correct_option_index,
                isCorrect=is_correct,
                explanation=question.explanation,
                correctOptionText=question.options[question.correct_option_index],
            )
        )

    total = len(lesson.quiz_questions)
    percentage = round((score / total) * 100, 2) if total else 0.0

    create_quiz_attempt(
        db=db,
        lesson_id=lesson.id,
        student_name=payload.studentName.strip(),
        score=score,
        total=total,
        percentage=percentage,
        answers=payload.answers,
    )

    return QuizSubmitResponse(score=score, total=total, percentage=percentage, answerReview=reviews)
