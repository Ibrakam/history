import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { fetchPublicLesson, submitQuiz } from "../api";
import { LessonRenderer } from "../components/LessonRenderer";
import type { PublicLessonDetail, QuizSubmitResponse } from "../types";

export function PublicLessonPage() {
  const { slug = "" } = useParams();
  const [lesson, setLesson] = useState<PublicLessonDetail | null>(null);
  const [answers, setAnswers] = useState<Array<number | null>>([]);
  const [result, setResult] = useState<QuizSubmitResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const loadLesson = async () => {
      setLoading(true);
      setError("");
      try {
        const response = await fetchPublicLesson(slug);
        setLesson(response);
        setAnswers(new Array(response.quiz.length).fill(null));
      } catch (err) {
        setError(err instanceof Error ? err.message : "Не удалось открыть урок.");
      } finally {
        setLoading(false);
      }
    };

    void loadLesson();
  }, [slug]);

  const handleSubmit = async () => {
    setSubmitting(true);
    setError("");
    try {
      const response = await submitQuiz(slug, answers);
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось проверить тест.");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <main className="public-shell">
        <p>Загрузка урока...</p>
      </main>
    );
  }

  if (error || !lesson) {
    return (
      <main className="public-shell">
        <div className="not-found-card">
          <h1>Урок недоступен</h1>
          <p>{error || "Проверьте ссылку или обратитесь к учителю."}</p>
          <Link to="/admin/login" className="ghost-button">
            В админку
          </Link>
        </div>
      </main>
    );
  }

  return (
    <main className={`public-shell visual-mode-${lesson.visualMode}`}>
      <div className="public-lesson-wrap">
        <LessonRenderer
          title={lesson.title}
          heroSubtitle={lesson.heroSubtitle}
          visualMode={lesson.visualMode}
          layout={lesson.lessonLayout}
          lessonHtml={lesson.lessonHtml}
          renderMode="public"
        />

        <section className="public-quiz">
          <div className="section-heading">
            <div>
              <h2>Проверь себя</h2>
              <p>Выберите ответы и сразу получите результат.</p>
            </div>
          </div>

          {lesson.quiz.map((question, questionIndex) => (
            <div className="quiz-card" key={question.id}>
              <strong>
                {questionIndex + 1}. {question.prompt}
              </strong>

              <div className="public-options">
                {question.options.map((option, optionIndex) => (
                  <label key={`${question.id}-${optionIndex}`} className="option-row">
                    <input
                      type="radio"
                      name={`question-${question.id}`}
                      checked={answers[questionIndex] === optionIndex}
                      onChange={() =>
                        setAnswers((prev) =>
                          prev.map((value, index) => (index === questionIndex ? optionIndex : value)),
                        )
                      }
                    />
                    <span>{option}</span>
                  </label>
                ))}
              </div>
            </div>
          ))}

          <button
            type="button"
            className="primary-button"
            onClick={() => void handleSubmit()}
            disabled={submitting}
          >
            {submitting ? "Проверяем..." : "Проверить тест"}
          </button>

          {result ? (
            <div className="result-card">
              <h3>
                Результат: {result.score} из {result.total} ({result.percentage}%)
              </h3>
              {result.answerReview.map((review, index) => (
                <div
                  key={review.questionId}
                  className={`review-row ${review.isCorrect ? "ok" : "bad"}`}
                >
                  <strong>
                    {index + 1}. {review.isCorrect ? "Верно" : "Ошибка"}
                  </strong>
                  <p>{review.prompt}</p>
                  {!review.isCorrect ? <p>Правильный ответ: {review.correctOptionText}</p> : null}
                  <p>{review.explanation}</p>
                </div>
              ))}
            </div>
          ) : null}
        </section>
      </div>
    </main>
  );
}
