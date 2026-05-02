import type {
  GenerateLessonResponse,
  ImageSlot,
  LessonDetail,
  LessonForm,
  LessonListItem,
  MaterialCollection,
  MediaAsset,
  PublicLessonDetail,
  QuizResultsResponse,
  QuizSubmitResponse,
} from "./types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";
const TOKEN_KEY = "history-admin-token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

async function request<T>(path: string, init?: RequestInit, auth = false): Promise<T> {
  const headers = new Headers(init?.headers);
  headers.set("Content-Type", "application/json");

  if (auth) {
    const token = getToken();
    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
  });

  if (!response.ok) {
    let detail = "Не удалось выполнить запрос.";
    try {
      const payload = await response.json();
      detail = payload.detail ?? detail;
    } catch {
      detail = response.statusText || detail;
    }
    throw new Error(detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export async function login(username: string, password: string): Promise<string> {
  const response = await request<{ access_token: string }>("/api/admin/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
  return response.access_token;
}

export function fetchMe(): Promise<{ username: string }> {
  return request("/api/admin/me", undefined, true);
}

export function fetchLessons(): Promise<LessonListItem[]> {
  return request("/api/admin/lessons", undefined, true);
}

export function fetchLesson(id: number): Promise<LessonDetail> {
  return request(`/api/admin/lessons/${id}`, undefined, true);
}

export function generateLesson(
  topic: string,
  materialCollection: MaterialCollection = "auto",
): Promise<GenerateLessonResponse> {
  return request(
    "/api/admin/lessons/generate",
    {
      method: "POST",
      body: JSON.stringify({ topic, materialCollection }),
    },
    true,
  );
}

export function createLesson(payload: LessonForm): Promise<LessonDetail> {
  return request(
    "/api/admin/lessons",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    true,
  );
}

export function updateLesson(id: number, payload: LessonForm): Promise<LessonDetail> {
  return request(
    `/api/admin/lessons/${id}`,
    {
      method: "PUT",
      body: JSON.stringify(payload),
    },
    true,
  );
}

export async function uploadImageAsset(file: File): Promise<MediaAsset> {
  const formData = new FormData();
  formData.append("file", file);

  const headers = new Headers();
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(`${API_BASE}/api/admin/uploads/image`, {
    method: "POST",
    body: formData,
    headers,
  });

  if (!response.ok) {
    let detail = "Не удалось загрузить изображение.";
    try {
      const payload = await response.json();
      detail = payload.detail ?? detail;
    } catch {
      detail = response.statusText || detail;
    }
    throw new Error(detail);
  }

  return (await response.json()) as MediaAsset;
}

export function refreshSlotImages(id: number, slotId: string): Promise<{ slot: ImageSlot }> {
  return request(
    `/api/admin/lessons/${id}/refresh-slot-images`,
    {
      method: "POST",
      body: JSON.stringify({ slotId }),
    },
    true,
  );
}

export function publishLesson(id: number): Promise<LessonDetail> {
  return request(`/api/admin/lessons/${id}/publish`, { method: "POST" }, true);
}

export function unpublishLesson(id: number): Promise<LessonDetail> {
  return request(`/api/admin/lessons/${id}/unpublish`, { method: "POST" }, true);
}

export async function deleteLesson(id: number): Promise<void> {
  await request(`/api/admin/lessons/${id}`, { method: "DELETE" }, true);
}

export function fetchPublicLesson(slug: string): Promise<PublicLessonDetail> {
  return request(`/api/public/lessons/${slug}`);
}

export function submitQuiz(
  slug: string,
  studentName: string,
  answers: Array<number | null>,
): Promise<QuizSubmitResponse> {
  return request(`/api/public/lessons/${slug}/submit-quiz`, {
    method: "POST",
    body: JSON.stringify({ studentName, answers }),
  });
}

export function fetchQuizResults(lessonId: number): Promise<QuizResultsResponse> {
  return request(`/api/admin/lessons/${lessonId}/quiz-results`, undefined, true);
}
