import type { AdminQuizQuestion } from "../types";

type Props = {
  quiz: AdminQuizQuestion[];
  onChange: (nextQuiz: AdminQuizQuestion[]) => void;
};

export function QuizEditor({ quiz, onChange }: Props) {
  const updateQuestion = (index: number, patch: Partial<AdminQuizQuestion>) => {
    const next = quiz.map((item, itemIndex) =>
      itemIndex === index ? { ...item, ...patch } : item,
    );
    onChange(next);
  };

  const updateOption = (questionIndex: number, optionIndex: number, value: string) => {
    const options = [...quiz[questionIndex].options];
    options[optionIndex] = value;
    updateQuestion(questionIndex, { options });
  };

  const addQuestion = () => {
    onChange([
      ...quiz,
      {
        prompt: `Вопрос ${quiz.length + 1}`,
        options: ["Вариант 1", "Вариант 2", "Вариант 3", "Вариант 4"],
        correctOptionIndex: 0,
        explanation: "Пояснение к правильному ответу.",
      },
    ]);
  };

  const removeQuestion = (index: number) => {
    if (quiz.length <= 3) {
      return;
    }
    onChange(quiz.filter((_, itemIndex) => itemIndex !== index));
  };

  return (
    <div className="quiz-editor">
      <div className="section-heading">
        <div>
          <h3>Тест</h3>
          <p>Вопросы и правильные ответы можно править вручную перед публикацией.</p>
        </div>
        <button type="button" className="ghost-button" onClick={addQuestion}>
          Добавить вопрос
        </button>
      </div>

      {quiz.map((question, questionIndex) => (
        <div key={`${question.prompt}-${questionIndex}`} className="quiz-card">
          <div className="quiz-card-header">
            <strong>Вопрос {questionIndex + 1}</strong>
            <button type="button" className="link-button" onClick={() => removeQuestion(questionIndex)}>
              Удалить
            </button>
          </div>

          <label>
            Формулировка
            <textarea
              value={question.prompt}
              onChange={(event) => updateQuestion(questionIndex, { prompt: event.target.value })}
              rows={3}
            />
          </label>

          <div className="quiz-options">
            {question.options.map((option, optionIndex) => (
              <label key={`${questionIndex}-${optionIndex}`}>
                Вариант {optionIndex + 1}
                <input
                  value={option}
                  onChange={(event) => updateOption(questionIndex, optionIndex, event.target.value)}
                />
              </label>
            ))}
          </div>

          <label>
            Правильный ответ
            <select
              value={question.correctOptionIndex}
              onChange={(event) =>
                updateQuestion(questionIndex, {
                  correctOptionIndex: Number(event.target.value),
                })
              }
            >
              {question.options.map((option, optionIndex) => (
                <option key={`${questionIndex}-correct-${optionIndex}`} value={optionIndex}>
                  {optionIndex + 1}. {option}
                </option>
              ))}
            </select>
          </label>

          <label>
            Пояснение
            <textarea
              value={question.explanation}
              onChange={(event) => updateQuestion(questionIndex, { explanation: event.target.value })}
              rows={3}
            />
          </label>
        </div>
      ))}
    </div>
  );
}

