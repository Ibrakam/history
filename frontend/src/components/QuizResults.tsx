import { useEffect, useState } from "react";

import { fetchQuizResults } from "../api";
import type { QuizAttempt } from "../types";

type Props = {
  lessonId: number;
};

export function QuizResults({ lessonId }: Props) {
  const [attempts, setAttempts] = useState<QuizAttempt[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchQuizResults(lessonId)
      .then((data) => setAttempts(data.attempts))
      .catch(() => setAttempts([]))
      .finally(() => setLoading(false));
  }, [lessonId]);

  if (loading) {
    return <div className="quiz-results-panel">Загрузка результатов...</div>;
  }

  if (attempts.length === 0) {
    return (
      <div className="quiz-results-panel">
        <p className="empty-hint">Пока никто не прошёл тест.</p>
      </div>
    );
  }

  return (
    <div className="quiz-results-panel">
      <div className="section-heading">
        <h3>Результаты теста</h3>
        <span>{attempts.length} попыток</span>
      </div>
      <table className="quiz-results-table">
        <thead>
          <tr>
            <th>Ученик</th>
            <th>Балл</th>
            <th>%</th>
            <th>Дата</th>
          </tr>
        </thead>
        <tbody>
          {attempts.map((a) => (
            <tr key={a.id}>
              <td>{a.studentName}</td>
              <td>
                {a.score}/{a.total}
              </td>
              <td>{a.percentage.toFixed(0)}%</td>
              <td>{new Date(a.createdAt).toLocaleDateString("ru-RU")}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
