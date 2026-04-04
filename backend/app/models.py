from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class LessonStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"


class Lesson(Base):
    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    topic: Mapped[str] = mapped_column(String(255), index=True)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hero_subtitle: Mapped[str] = mapped_column(String(255))
    lesson_html: Mapped[str] = mapped_column(Text)
    lesson_layout: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    theme_key: Mapped[str] = mapped_column(String(50), default="chronicle")
    status: Mapped[LessonStatus] = mapped_column(
        Enum(LessonStatus),
        default=LessonStatus.DRAFT,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    quiz_questions: Mapped[list["QuizQuestion"]] = relationship(
        back_populates="lesson",
        cascade="all, delete-orphan",
        order_by="QuizQuestion.position",
    )


class QuizQuestion(Base):
    __tablename__ = "quiz_questions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    prompt: Mapped[str] = mapped_column(Text)
    options: Mapped[list[str]] = mapped_column(JSON)
    correct_option_index: Mapped[int] = mapped_column(Integer)
    explanation: Mapped[str] = mapped_column(Text)

    lesson: Mapped[Lesson] = relationship(back_populates="quiz_questions")
