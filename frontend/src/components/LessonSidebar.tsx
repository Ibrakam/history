import type { LessonListItem } from "../types";

type Props = {
  lessons: LessonListItem[];
  activeId?: number;
  loading: boolean;
  saving: boolean;
  onSelect: (id: number) => void;
  onDelete: (id: number) => void;
  onNew: () => void;
  onLogout: () => void;
};

export function LessonSidebar({
  lessons,
  activeId,
  loading,
  saving,
  onSelect,
  onDelete,
  onNew,
  onLogout,
}: Props) {
  return (
    <aside className="sidebar">
      <div className="lesson-list">
        <div className="section-heading">
          <h3>Уроки</h3>
          <span>{loading ? "..." : lessons.length}</span>
        </div>

        {lessons.map((lesson) => (
          <div
            key={lesson.id}
            className={`lesson-list-row ${activeId === lesson.id ? "active" : ""}`}
          >
            <button
              type="button"
              className={`lesson-list-item ${activeId === lesson.id ? "active" : ""}`}
              onClick={() => onSelect(lesson.id)}
            >
              <strong>{lesson.title}</strong>
              <span>{lesson.topic}</span>
              <small>{lesson.status === "published" ? "Опубликован" : "Черновик"}</small>
            </button>
            <button
              type="button"
              className="delete-lesson-button"
              onClick={() => onDelete(lesson.id)}
              aria-label={`Удалить ${lesson.title}`}
              disabled={saving}
            >
              ×
            </button>
          </div>
        ))}
      </div>

      <div className="sidebar-actions">
        <button type="button" className="primary-button" onClick={onNew}>
          Новый урок
        </button>
        <button type="button" className="ghost-button" onClick={onLogout}>
          Выйти
        </button>
      </div>
    </aside>
  );
}
