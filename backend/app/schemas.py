from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


VisualMode = Literal["chronicle", "empire", "warfront", "reform", "archive"]
SectionType = Literal["narrative", "timeline", "person_card_grid", "artifact_gallery", "quote_callout"]
AssetProvider = Literal["wikimedia", "openai", "demo"]


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    username: str
    password: str


class AdminMeResponse(BaseModel):
    username: str


class QuizQuestionBase(BaseModel):
    prompt: str
    options: list[str]
    explanation: str


class AdminQuizQuestion(QuizQuestionBase):
    correctOptionIndex: int


class PublicQuizQuestion(QuizQuestionBase):
    id: int


class MediaAsset(BaseModel):
    assetId: str
    title: str
    imageUrl: str
    thumbUrl: str
    sourceUrl: str
    author: str
    license: str
    provider: AssetProvider
    alt: str


class ImageSlot(BaseModel):
    slotId: str
    label: str
    searchQueries: list[str] = []
    selectedAsset: MediaAsset | None = None
    candidateAssets: list[MediaAsset] = []
    role: str = "inline"


class TimelineItem(BaseModel):
    year: str
    title: str
    description: str


class PersonCard(BaseModel):
    name: str
    role: str
    summary: str
    slotId: str | None = None


class ArtifactCard(BaseModel):
    title: str
    summary: str
    slotId: str | None = None


class HeroBlock(BaseModel):
    eyebrow: str
    intro: str
    slotId: str


class LessonSection(BaseModel):
    id: str
    blockType: SectionType
    title: str
    lead: str | None = None
    body: list[str] = []
    timelineItems: list[TimelineItem] = []
    personCards: list[PersonCard] = []
    artifactCards: list[ArtifactCard] = []
    quoteText: str | None = None
    quoteCaption: str | None = None
    slotId: str | None = None
    visible: bool = True


class LessonLayout(BaseModel):
    visualMode: VisualMode
    hero: HeroBlock
    sections: list[LessonSection]
    imageSlots: list[ImageSlot]


class GenerateLessonRequest(BaseModel):
    topic: str = Field(min_length=2, max_length=200)


class GenerateLessonResponse(BaseModel):
    title: str
    topic: str
    heroSubtitle: str
    visualMode: VisualMode
    lessonLayout: LessonLayout
    quiz: list[AdminQuizQuestion]


class RefreshSlotImagesRequest(BaseModel):
    slotId: str


class RefreshSlotImagesResponse(BaseModel):
    slot: ImageSlot


class LessonSaveRequest(BaseModel):
    title: str
    topic: str
    heroSubtitle: str
    visualMode: VisualMode
    lessonLayout: LessonLayout | None = None
    quiz: list[AdminQuizQuestion]
    lessonHtml: str = ""


class LessonListItem(BaseModel):
    id: int
    title: str
    topic: str
    slug: str
    themeKey: str
    status: str
    createdAt: datetime
    updatedAt: datetime
    publishedAt: datetime | None


class LessonDetail(BaseModel):
    id: int
    title: str
    topic: str
    slug: str
    heroSubtitle: str
    visualMode: VisualMode
    lessonLayout: LessonLayout | None = None
    lessonHtml: str = ""
    status: str
    createdAt: datetime
    updatedAt: datetime
    publishedAt: datetime | None
    quiz: list[AdminQuizQuestion]


class PublicLessonDetail(BaseModel):
    id: int
    title: str
    topic: str
    slug: str
    heroSubtitle: str
    visualMode: VisualMode
    lessonLayout: LessonLayout | None = None
    lessonHtml: str = ""
    publishedAt: datetime | None
    quiz: list[PublicQuizQuestion]


class QuizSubmitRequest(BaseModel):
    answers: list[int | None]


class QuizAnswerReview(BaseModel):
    questionId: int
    prompt: str
    selectedOptionIndex: int | None
    correctOptionIndex: int
    isCorrect: bool
    explanation: str
    correctOptionText: str


class QuizSubmitResponse(BaseModel):
    score: int
    total: int
    percentage: float
    answerReview: list[QuizAnswerReview]
