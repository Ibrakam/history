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
} from "../api";
import { LessonRenderer } from "../components/LessonRenderer";
import { MediaInspector } from "../components/MediaInspector";
import { QuizEditor } from "../components/QuizEditor";
import { EMPTY_FORM, VISUAL_MODES } from "../theme";
import type {
  ArtifactCard,
  ImageSlot,
  LessonDetail,
  LessonForm,
  LessonListItem,
  LessonSection,
  MediaAsset,
  PersonCard,
  TimelineItem,
  VisualMode,
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

function splitParagraphs(value: string): string[] {
  return value
    .split(/\n{2,}/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function joinParagraphs(value: string[]): string {
  return value.join("\n\n");
}

export function AdminDashboardPage() {
  const navigate = useNavigate();
  const [lessons, setLessons] = useState<LessonListItem[]>([]);
  const [form, setForm] = useState<LessonForm>(EMPTY_FORM());
  const [topicInput, setTopicInput] = useState("Древняя Русь");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loadingLessons, setLoadingLessons] = useState(true);
  const [saving, setSaving] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [refreshingSlotId, setRefreshingSlotId] = useState<string | null>(null);

  const publicLink = form.slug ? `${window.location.origin}/lesson/${form.slug}` : "";
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

  const handleGenerate = async () => {
    setGenerating(true);
    setError("");
    setMessage("");
    try {
      const generated = await generateLesson(topicInput);
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

  const handleLogout = () => {
    clearToken();
    navigate("/admin/login");
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

  const updateTimelineItem = (
    sectionId: string,
    itemIndex: number,
    patch: Partial<TimelineItem>,
  ) => {
    updateSection(sectionId, (section) => {
      section.timelineItems = section.timelineItems.map((item, index) =>
        index === itemIndex ? { ...item, ...patch } : item,
      );
    });
  };

  const updatePersonCard = (sectionId: string, itemIndex: number, patch: Partial<PersonCard>) => {
    updateSection(sectionId, (section) => {
      section.personCards = section.personCards.map((item, index) =>
        index === itemIndex ? { ...item, ...patch } : item,
      );
    });
  };

  const updateArtifactCard = (
    sectionId: string,
    itemIndex: number,
    patch: Partial<ArtifactCard>,
  ) => {
    updateSection(sectionId, (section) => {
      section.artifactCards = section.artifactCards.map((item, index) =>
        index === itemIndex ? { ...item, ...patch } : item,
      );
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

  return (
    <main className={`dashboard-shell visual-mode-${form.visualMode}`}>
      <aside className="sidebar">
        <div className="sidebar-head">
          <span className="eyebrow">Админка</span>
          <h1>History AI</h1>
          <p>Генерация визуальных уроков с тематическими изображениями и готовой страницей.</p>
        </div>

        <div className="sidebar-actions">
          <button type="button" className="primary-button" onClick={resetEditor}>
            Новый урок
          </button>
          <button type="button" className="ghost-button" onClick={handleLogout}>
            Выйти
          </button>
        </div>

        <div className="lesson-list">
          <div className="section-heading">
            <h3>Уроки</h3>
            <span>{loadingLessons ? "..." : lessons.length}</span>
          </div>

          {lessons.map((lesson) => (
            <div key={lesson.id} className={`lesson-list-row ${form.id === lesson.id ? "active" : ""}`}>
              <button
                type="button"
                className={`lesson-list-item ${form.id === lesson.id ? "active" : ""}`}
                onClick={() => void openLesson(lesson.id)}
              >
                <strong>{lesson.title}</strong>
                <span>{lesson.topic}</span>
                <small>{lesson.status === "published" ? "Опубликован" : "Черновик"}</small>
              </button>
              <button
                type="button"
                className="delete-lesson-button"
                onClick={() => void handleDeleteLesson(lesson.id)}
                aria-label={`Удалить ${lesson.title}`}
                disabled={saving}
              >
                ×
              </button>
            </div>
          ))}
        </div>
      </aside>

      <section className="workspace">
        <header className="workspace-top">
          <div>
            <span className="eyebrow">Генерация</span>
            <h2>Тема урока</h2>
          </div>

          <div className="generator-row">
            <input value={topicInput} onChange={(event) => setTopicInput(event.target.value)} />
            <button
              type="button"
              className="primary-button"
              onClick={() => void handleGenerate()}
              disabled={generating}
            >
              {generating ? "Генерируем..." : "Сгенерировать"}
            </button>
          </div>
        </header>

        {message ? <div className="form-success">{message}</div> : null}
        {error ? <div className="form-error">{error}</div> : null}

        <div className="editor-grid editor-grid-rich">
          <section className="editor-panel">
            <div className="section-heading">
              <div>
                <h3>Редактор урока</h3>
                <p>Правка заголовков, секций, карточек и визуального режима.</p>
              </div>
              <div className="chip" style={{ borderColor: visualMeta.accent }}>
                {visualMeta.name}
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
              Тема
              <input
                value={form.topic}
                onChange={(event) => setForm((prev) => ({ ...prev, topic: event.target.value }))}
              />
            </label>

            <label>
              Подзаголовок
              <input
                value={form.heroSubtitle}
                onChange={(event) =>
                  setForm((prev) => ({
                    ...prev,
                    heroSubtitle: event.target.value,
                  }))
                }
              />
            </label>

            <label>
              Визуальный режим
              <select
                value={form.visualMode}
                onChange={(event) => {
                  const nextMode = event.target.value as VisualMode;
                  setForm((prev) => ({
                    ...prev,
                    visualMode: nextMode,
                    lessonLayout: prev.lessonLayout
                      ? { ...prev.lessonLayout, visualMode: nextMode }
                      : prev.lessonLayout,
                  }));
                }}
              >
                {Object.entries(VISUAL_MODES).map(([key, meta]) => (
                  <option key={key} value={key}>
                    {meta.name} - {meta.description}
                  </option>
                ))}
              </select>
            </label>

            {form.lessonLayout ? (
              <>
                <label>
                  Hero eyebrow
                  <input
                    value={form.lessonLayout.hero.eyebrow}
                    onChange={(event) =>
                      updateLayout((layout) => {
                        layout.hero.eyebrow = event.target.value;
                      })
                    }
                  />
                </label>

                <label>
                  Hero intro
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
                  <article key={section.id} className="section-editor-card">
                    <div className="section-card-head">
                      <div>
                        <strong>{section.blockType}</strong>
                        <small>{section.id}</small>
                      </div>
                      <label className="toggle-row">
                        <input
                          type="checkbox"
                          checked={section.visible}
                          onChange={(event) =>
                            updateSection(section.id, (current) => {
                              current.visible = event.target.checked;
                            })
                          }
                        />
                        Показывать
                      </label>
                    </div>

                    <label>
                      Заголовок секции
                      <input
                        value={section.title}
                        onChange={(event) =>
                          updateSection(section.id, (current) => {
                            current.title = event.target.value;
                          })
                        }
                      />
                    </label>

                    {"lead" in section ? (
                      <label>
                        Lead
                        <textarea
                          rows={2}
                          value={section.lead ?? ""}
                          onChange={(event) =>
                            updateSection(section.id, (current) => {
                              current.lead = event.target.value;
                            })
                          }
                        />
                      </label>
                    ) : null}

                    {section.blockType === "narrative" ? (
                      <label>
                        Параграфы
                        <textarea
                          rows={8}
                          value={joinParagraphs(section.body)}
                          onChange={(event) =>
                            updateSection(section.id, (current) => {
                              current.body = splitParagraphs(event.target.value);
                            })
                          }
                        />
                      </label>
                    ) : null}

                    {section.blockType === "timeline" ? (
                      <div className="card-stack">
                        {section.timelineItems.map((item, index) => (
                          <div key={`${section.id}-timeline-${index}`} className="subcard">
                            <label>
                              Год / этап
                              <input
                                value={item.year}
                                onChange={(event) =>
                                  updateTimelineItem(section.id, index, { year: event.target.value })
                                }
                              />
                            </label>
                            <label>
                              Заголовок
                              <input
                                value={item.title}
                                onChange={(event) =>
                                  updateTimelineItem(section.id, index, { title: event.target.value })
                                }
                              />
                            </label>
                            <label>
                              Описание
                              <textarea
                                rows={3}
                                value={item.description}
                                onChange={(event) =>
                                  updateTimelineItem(section.id, index, {
                                    description: event.target.value,
                                  })
                                }
                              />
                            </label>
                          </div>
                        ))}
                      </div>
                    ) : null}

                    {section.blockType === "person_card_grid" ? (
                      <div className="card-stack">
                        {section.personCards.map((card, index) => (
                          <div key={`${section.id}-person-${index}`} className="subcard">
                            <label>
                              Имя
                              <input
                                value={card.name}
                                onChange={(event) =>
                                  updatePersonCard(section.id, index, { name: event.target.value })
                                }
                              />
                            </label>
                            <label>
                              Роль
                              <input
                                value={card.role}
                                onChange={(event) =>
                                  updatePersonCard(section.id, index, { role: event.target.value })
                                }
                              />
                            </label>
                            <label>
                              Описание
                              <textarea
                                rows={3}
                                value={card.summary}
                                onChange={(event) =>
                                  updatePersonCard(section.id, index, { summary: event.target.value })
                                }
                              />
                            </label>
                          </div>
                        ))}
                      </div>
                    ) : null}

                    {section.blockType === "artifact_gallery" ? (
                      <div className="card-stack">
                        {section.artifactCards.map((card, index) => (
                          <div key={`${section.id}-artifact-${index}`} className="subcard">
                            <label>
                              Название
                              <input
                                value={card.title}
                                onChange={(event) =>
                                  updateArtifactCard(section.id, index, { title: event.target.value })
                                }
                              />
                            </label>
                            <label>
                              Описание
                              <textarea
                                rows={3}
                                value={card.summary}
                                onChange={(event) =>
                                  updateArtifactCard(section.id, index, { summary: event.target.value })
                                }
                              />
                            </label>
                          </div>
                        ))}
                      </div>
                    ) : null}

                    {section.blockType === "quote_callout" ? (
                      <>
                        <label>
                          Цитата
                          <textarea
                            rows={4}
                            value={section.quoteText ?? ""}
                            onChange={(event) =>
                              updateSection(section.id, (current) => {
                                current.quoteText = event.target.value;
                              })
                            }
                          />
                        </label>
                        <label>
                          Подпись
                          <input
                            value={section.quoteCaption ?? ""}
                            onChange={(event) =>
                              updateSection(section.id, (current) => {
                                current.quoteCaption = event.target.value;
                              })
                            }
                          />
                        </label>
                      </>
                    ) : null}
                  </article>
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
          </section>

          <MediaInspector
            slots={slots}
            currentSlotId={slots.find((slot) => slot.selectedAsset)?.slotId}
            refreshingSlotId={refreshingSlotId}
            canRefresh={Boolean(form.id)}
            onSelectAsset={handleSelectAsset}
            onRefreshSlot={(slotId) => void handleRefreshSlot(slotId)}
          />

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

            <LessonRenderer
              title={form.title || "Название урока"}
              heroSubtitle={form.heroSubtitle || "Короткое описание урока."}
              visualMode={form.visualMode}
              layout={form.lessonLayout}
              lessonHtml={form.lessonHtml}
              renderMode="preview"
            />

            {publicLink ? (
              <div className="public-link-box">
                <strong>Публичная ссылка</strong>
                <a href={publicLink} target="_blank" rel="noreferrer">
                  {publicLink}
                </a>
              </div>
            ) : null}
          </section>
        </div>
      </section>
    </main>
  );
}
