export type VisualMode = "chronicle" | "empire" | "warfront" | "reform" | "archive";
export type MaterialCollection = "auto" | "uzbekistan_history" | "history";
export type SectionType =
  | "narrative"
  | "timeline"
  | "person_card_grid"
  | "artifact_gallery"
  | "quote_callout";
export type AssetProvider = "wikimedia" | "openai" | "demo" | "upload";

export type AdminQuizQuestion = {
  prompt: string;
  options: string[];
  correctOptionIndex: number;
  explanation: string;
};

export type PublicQuizQuestion = {
  id: number;
  prompt: string;
  options: string[];
  explanation: string;
};

export type MediaAsset = {
  assetId: string;
  title: string;
  imageUrl: string;
  thumbUrl: string;
  sourceUrl: string;
  author: string;
  license: string;
  provider: AssetProvider;
  alt: string;
};

export type ImageSlot = {
  slotId: string;
  label: string;
  searchQueries: string[];
  selectedAsset: MediaAsset | null;
  candidateAssets: MediaAsset[];
  role: string;
};

export type TimelineItem = {
  year: string;
  title: string;
  description: string;
};

export type PersonCard = {
  name: string;
  role: string;
  summary: string;
  slotId?: string | null;
};

export type ArtifactCard = {
  title: string;
  summary: string;
  slotId?: string | null;
};

export type HeroBlock = {
  eyebrow: string;
  intro: string;
  slotId: string;
};

export type LessonSection = {
  id: string;
  blockType: SectionType;
  title: string;
  lead?: string | null;
  body: string[];
  timelineItems: TimelineItem[];
  personCards: PersonCard[];
  artifactCards: ArtifactCard[];
  quoteText?: string | null;
  quoteCaption?: string | null;
  slotId?: string | null;
  visible: boolean;
};

export type LessonLayout = {
  visualMode: VisualMode;
  hero: HeroBlock;
  sections: LessonSection[];
  imageSlots: ImageSlot[];
};

export type LessonListItem = {
  id: number;
  title: string;
  topic: string;
  slug: string;
  themeKey: VisualMode;
  status: string;
  createdAt: string;
  updatedAt: string;
  publishedAt: string | null;
};

export type LessonDetail = {
  id: number;
  title: string;
  topic: string;
  slug: string;
  heroSubtitle: string;
  visualMode: VisualMode;
  lessonLayout: LessonLayout | null;
  lessonHtml: string;
  status: string;
  createdAt: string;
  updatedAt: string;
  publishedAt: string | null;
  quiz: AdminQuizQuestion[];
};

export type PublicLessonDetail = {
  id: number;
  title: string;
  topic: string;
  slug: string;
  heroSubtitle: string;
  visualMode: VisualMode;
  lessonLayout: LessonLayout | null;
  lessonHtml: string;
  publishedAt: string | null;
  quiz: PublicQuizQuestion[];
};

export type GenerateLessonResponse = {
  title: string;
  topic: string;
  heroSubtitle: string;
  visualMode: VisualMode;
  lessonLayout: LessonLayout;
  quiz: AdminQuizQuestion[];
};

export type QuizSubmitResponse = {
  score: number;
  total: number;
  percentage: number;
  answerReview: {
    questionId: number;
    prompt: string;
    selectedOptionIndex: number | null;
    correctOptionIndex: number;
    isCorrect: boolean;
    explanation: string;
    correctOptionText: string;
  }[];
};

export type QuizAttempt = {
  id: number;
  studentName: string;
  score: number;
  total: number;
  percentage: number;
  createdAt: string;
};

export type QuizResultsResponse = {
  lessonId: number;
  lessonTitle: string;
  attempts: QuizAttempt[];
};

export type LessonForm = {
  id?: number;
  title: string;
  topic: string;
  heroSubtitle: string;
  visualMode: VisualMode;
  lessonLayout: LessonLayout | null;
  lessonHtml: string;
  quiz: AdminQuizQuestion[];
  status?: string;
  slug?: string;
};
