import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import {
  clearToken,
  createLesson,
  deleteLesson,
  fetchLesson,
  fetchLessons,
  fetchMe,
  generateLesson,
  publishLesson,
  refreshSlotImages,
  unpublishLesson,
  updateLesson,
  uploadImageAsset,
} from "../api";
import { LessonRenderer } from "../components/LessonRenderer";
import { LessonSidebar } from "../components/LessonSidebar";
import { MediaPickerModal } from "../components/MediaPickerModal";
import { QuizEditor } from "../components/QuizEditor";
import { QuizResults } from "../components/QuizResults";
import { SectionEditor } from "../components/SectionEditor";
import { TopicGenerator } from "../components/TopicGenerator";
import { EMPTY_FORM, VISUAL_MODES } from "../theme";
import type {
  LessonDetail,
  LessonForm,
  LessonListItem,
  LessonSection,
  MaterialCollection,
  MediaAsset,
} from "../types";

function lessonToForm(lesson: LessonDetail): LessonForm {
  return {
    id: lesson.id,
    title: lesson.title,
    topic: lesson.topic,
    heroSubtitle: lesson.heroSubtitle,
    visualMode: lesson.visualMode,
    lessonLayout: lesson.lessonLayout,
    lessonHtml: lesson.lessonHtml,
    quiz: lesson.quiz,
    status: lesson.status,
    slug: lesson.slug,
  };
}

export function AdminDashboardPage() {
  const navigate = useNavigate();
  const [lessons, setLessons] = useState<LessonListItem[]>([]);
  const [form, setForm] = useState<LessonForm>(EMPTY_FORM());
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loadingLessons, setLoadingLessons] = useState(true);
  const [saving, setSaving] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [refreshingSlotId, setRefreshingSlotId] = useState<string | null>(null);
  const [editingSlotId, setEditingSlotId] = useState<string | null>(null);

  const publicLink =
    form.slug && form.status === "published"
      ? `${window.location.origin}/lesson/${form.slug}`
      : "";
  const visualMeta = useMemo(() => VISUAL_MODES[form.visualMode], [form.visualMode]);

  useEffect(() => {
    const bootstrap = async () => {
      try {
        await fetchMe();
        const nextLessons = await fetchLessons();
        setLessons(nextLessons);
      } catch {
        clearToken();
        navigate("/admin/login");
      } finally {
        setLoadingLessons(false);
      }
    };

    void bootstrap();
  }, [navigate]);

  const refreshLessons = async () => {
    const nextLessons = await fetchLessons();
    setLessons(nextLessons);
  };

  const resetEditor = () => {
    setForm(EMPTY_FORM());
    setMessage("");
    setError("");
  };

  const openLesson = async (id: number) => {
    setError("");
    const lesson = await fetchLesson(id);
    setForm(lessonToForm(lesson));
  };

  const handleGenerate = async (topic: string, materialCollection: MaterialCollection) => {
    setGenerating(true);
    setError("");
    setMessage("");
    try {
      const generated = await generateLesson(topic, materialCollection);
      setForm({
        title: generated.title,
        topic: generated.topic,
        heroSubtitle: generated.heroSubtitle,
        visualMode: generated.visualMode,
        lessonLayout: generated.lessonLayout,
        lessonHtml: "",
        quiz: generated.quiz,
      });
      setMessage("Визуальный черновик урока собран. Проверьте блоки и изображения.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось сгенерировать урок.");
    } finally {
      setGenerating(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setError("");
    setMessage("");
    try {
      const response = form.id ? await updateLesson(form.id, form) : await createLesson(form);
      setForm(lessonToForm(response));
      await refreshLessons();
      setMessage(form.id ? "Изменения сохранены." : "Урок создан как черновик.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось сохранить урок.");
    } finally {
      setSaving(false);
    }
  };

  const togglePublish = async () => {
    if (!form.id) {
      setError("Сначала сохраните урок.");
      return;
    }

    setSaving(true);
    setError("");
    setMessage("");
    try {
      const response =
        form.status === "published" ? await unpublishLesson(form.id) : await publishLesson(form.id);
      setForm(lessonToForm(response));
      await refreshLessons();
      setMessage(
        response.status === "published"
          ? "Урок опубликован и готов для учеников."
          : "Урок снят с публикации.",
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось изменить статус публикации.");
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteLesson = async (lessonId: number) => {
    const confirmed = window.confirm("Удалить урок? Это действие нельзя отменить.");
    if (!confirmed) {
      return;
    }

    setSaving(true);
    setError("");
    setMessage("");
    try {
      await deleteLesson(lessonId);
      await refreshLessons();
      if (form.id === lessonId) {
        setForm(EMPTY_FORM());
      }
      setMessage("Урок удалён.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось удалить урок.");
    } finally {
      setSaving(false);
    }
  };

  const updateLayout = (mutate: (layout: NonNullable<LessonForm["lessonLayout"]>) => void) => {
    setForm((prev) => {
      if (!prev.lessonLayout) {
        return prev;
      }
      const nextLayout = structuredClone(prev.lessonLayout);
      mutate(nextLayout);
      nextLayout.visualMode = prev.visualMode;
      return { ...prev, lessonLayout: nextLayout };
    });
  };

  const updateSection = (sectionId: string, mutate: (section: LessonSection) => void) => {
    updateLayout((layout) => {
      const section = layout.sections.find((item) => item.id === sectionId);
      if (section) {
        mutate(section);
      }
    });
  };

  const handleSelectAsset = (slotId: string, asset: MediaAsset) => {
    updateLayout((layout) => {
      layout.imageSlots = layout.imageSlots.map((slot) =>
        slot.slotId === slotId ? { ...slot, selectedAsset: asset } : slot,
      );
    });
  };

  const handleRefreshSlot = async (slotId: string) => {
    if (!form.id) {
      setError("Обновление изображений доступно после первого сохранения урока.");
      return;
    }

    setRefreshingSlotId(slotId);
    setError("");
    try {
      const response = await refreshSlotImages(form.id, slotId);
      updateLayout((layout) => {
        layout.imageSlots = layout.imageSlots.map((slot) =>
          slot.slotId === slotId ? response.slot : slot,
        );
      });
      setMessage("Подбор изображений обновлён.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось обновить изображения.");
    } finally {
      setRefreshingSlotId(null);
    }
  };

  const slots = form.lessonLayout?.imageSlots ?? [];
  const editingSlot = editingSlotId
    ? slots.find((slot) => slot.slotId === editingSlotId) ?? null
    : null;

  return (
    <main className={`dashboard-shell visual-mode-${form.visualMode}`}>
      <header className="admin-topbar">
        <div className="admin-topbar-main">
          <div className="topbar-title">
            <strong>{form.title || "Новый урок"}</strong>
            <span>
              /admin · {form.status === "published" ? "опубликовано" : "черновик"} · {visualMeta.name}
            </span>
          </div>
        </div>

        <div className="admin-topbar-actions">
          <button
            type="button"
            className="ghost-button"
            onClick={() => {
              if (publicLink) window.open(publicLink, "_blank", "noreferrer");
            }}
            disabled={!publicLink}
          >
            Preview
          </button>
          <button
            type="button"
            className="ghost-button"
            onClick={() => void handleSave()}
            disabled={saving}
          >
            {saving ? "Сохраняем..." : "Сохранить"}
          </button>
          <button
            type="button"
            className="primary-button"
            onClick={() => void togglePublish()}
            disabled={saving}
          >
            {form.status === "published" ? "Снять" : "Опубликовать"}
          </button>
        </div>
      </header>

      <div className="admin-editor-shell">
        <LessonSidebar
          lessons={lessons}
          activeId={form.id}
          loading={loadingLessons}
          saving={saving}
          onSelect={(id) => void openLesson(id)}
          onDelete={(id) => void handleDeleteLesson(id)}
          onNew={resetEditor}
          onLogout={() => {
            clearToken();
            navigate("/admin/login");
          }}
        />

        <section className="workspace">
          <TopicGenerator onGenerate={handleGenerate} generating={generating} />

          {message ? <div className="form-success">{message}</div> : null}
          {error ? <div className="form-error">{error}</div> : null}

          <section className="preview-panel">
            <div className="section-heading">
              <div>
                <h3>Предпросмотр</h3>
                <p>{visualMeta.description}</p>
              </div>
              {form.status ? <div className="status-badge">{form.status}</div> : null}
            </div>

            <div className="reference-strip">
              {visualMeta.inspirations.map((reference) => (
                <a
                  key={`${form.visualMode}-${reference.label}`}
                  href={reference.url}
                  target="_blank"
                  rel="noreferrer"
                  className="query-pill"
                  title={reference.takeaway}
                >
                  {reference.label}
                </a>
              ))}
            </div>

            <div className="preview-frame">
              <LessonRenderer
                title={form.title || "Название урока"}
                heroSubtitle={form.heroSubtitle || "Короткое описание урока."}
                visualMode={form.visualMode}
                layout={form.lessonLayout}
                lessonHtml={form.lessonHtml}
                renderMode="preview"
                onEditSlot={(slotId) => setEditingSlotId(slotId)}
              />
            </div>

            {publicLink ? (
              <div className="public-link-box">
                <strong>Публичная ссылка</strong>
                <a href={publicLink} target="_blank" rel="noreferrer">
                  {publicLink}
                </a>
              </div>
            ) : null}
          </section>
        </section>

        <aside className="editor-panel">
          <div className="section-heading">
            <div>
              <h3>Редактор урока</h3>
              <p>Правка текста, теста и фотографий. Структуру собирает нейросеть.</p>
            </div>
          </div>

            <label>
              Заголовок
              <input
                value={form.title}
                onChange={(event) => setForm((prev) => ({ ...prev, title: event.target.value }))}
              />
            </label>

            <label>
              Подзаголовок
              <textarea
                rows={2}
                value={form.heroSubtitle}
                onChange={(event) =>
                  setForm((prev) => ({
                    ...prev,
                    heroSubtitle: event.target.value,
                  }))
                }
              />
            </label>

            {form.lessonLayout ? (
              <>
                <label>
                  Вступление
                  <textarea
                    rows={4}
                    value={form.lessonLayout.hero.intro}
                    onChange={(event) =>
                      updateLayout((layout) => {
                        layout.hero.intro = event.target.value;
                      })
                    }
                  />
                </label>

                {form.lessonLayout.sections.map((section) => (
                  <SectionEditor
                    key={section.id}
                    section={section}
                    onUpdate={updateSection}
                  />
                ))}
              </>
            ) : (
              <div className="empty-state-card">
                Сначала сгенерируйте урок. После этого появятся блоки, изображения и визуальный
                preview.
              </div>
            )}

            <QuizEditor
              quiz={form.quiz}
              onChange={(nextQuiz) => setForm((prev) => ({ ...prev, quiz: nextQuiz }))}
            />

            {form.id ? <QuizResults lessonId={form.id} /> : null}

            <div className="toolbar">
              <button
                type="button"
                className="primary-button"
                onClick={() => void handleSave()}
                disabled={saving}
              >
                {saving ? "Сохраняем..." : form.id ? "Сохранить" : "Создать урок"}
              </button>
              <button
                type="button"
                className="ghost-button"
                onClick={() => void togglePublish()}
                disabled={saving}
              >
                {form.status === "published" ? "Снять с публикации" : "Опубликовать"}
              </button>
              {form.id ? (
                <button
                  type="button"
                  className="danger-button"
                  onClick={() => void handleDeleteLesson(form.id!)}
                  disabled={saving}
                >
                  Удалить урок
                </button>
              ) : null}
            </div>
        </aside>
      </div>

      {editingSlot ? (
        <MediaPickerModal
          slot={editingSlot}
          refreshing={refreshingSlotId === editingSlot.slotId}
          canRefresh={Boolean(form.id)}
          onSelect={(asset) => handleSelectAsset(editingSlot.slotId, asset)}
          onRefresh={() => void handleRefreshSlot(editingSlot.slotId)}
          onUpload={(file) => uploadImageAsset(file)}
          onClose={() => setEditingSlotId(null)}
        />
      ) : null}
    </main>
  );
}
