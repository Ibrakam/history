import { useEffect, useRef, useState } from "react";

import type { MaterialCollection } from "../types";

type Props = {
  onGenerate: (topic: string, materialCollection: MaterialCollection) => Promise<void>;
  generating: boolean;
};

const STAGES = [
  "Изучаем источники по теме",
  "Собираем структуру урока",
  "Пишем тексты разделов",
  "Подбираем иллюстрации",
  "Готовим вопросы теста",
  "Финализируем визуальный стиль",
];

export function TopicGenerator({ onGenerate, generating }: Props) {
  const [topicInput, setTopicInput] = useState("Древняя Русь");
  const [materialCollection, setMaterialCollection] = useState<MaterialCollection>("auto");
  const [progress, setProgress] = useState(0);
  const [stageIndex, setStageIndex] = useState(0);
  const progressTimer = useRef<number | null>(null);
  const stageTimer = useRef<number | null>(null);

  useEffect(() => {
    if (!generating) {
      if (progressTimer.current) window.clearInterval(progressTimer.current);
      if (stageTimer.current) window.clearInterval(stageTimer.current);
      if (progress > 0) {
        setProgress(100);
        const reset = window.setTimeout(() => {
          setProgress(0);
          setStageIndex(0);
        }, 600);
        return () => window.clearTimeout(reset);
      }
      return;
    }

    setProgress(6);
    setStageIndex(0);

    progressTimer.current = window.setInterval(() => {
      setProgress((prev) => {
        if (prev >= 92) return prev;
        const remaining = 92 - prev;
        return prev + Math.max(0.4, remaining * 0.04);
      });
    }, 220);

    stageTimer.current = window.setInterval(() => {
      setStageIndex((prev) => (prev + 1) % STAGES.length);
    }, 2400);

    return () => {
      if (progressTimer.current) window.clearInterval(progressTimer.current);
      if (stageTimer.current) window.clearInterval(stageTimer.current);
    };
  }, [generating]);

  return (
    <header className="workspace-top">
      <div>
        <span className="eyebrow">Генерация</span>
        <h2>Тема урока</h2>
      </div>

      <div className="generator-row">
        <select
          value={materialCollection}
          onChange={(event) => setMaterialCollection(event.target.value as MaterialCollection)}
          disabled={generating}
          aria-label="Источник материалов"
        >
          <option value="auto">Авто</option>
          <option value="uzbekistan_history">История Узбекистана</option>
          <option value="history">Всемирная история</option>
        </select>
        <input
          value={topicInput}
          onChange={(event) => setTopicInput(event.target.value)}
          disabled={generating}
        />
        <button
          type="button"
          className="primary-button"
          onClick={() => void onGenerate(topicInput, materialCollection)}
          disabled={generating}
        >
          {generating ? "Генерируем..." : "Сгенерировать"}
        </button>
      </div>

      {generating || progress > 0 ? (
        <div className="generation-progress" role="status" aria-live="polite">
          <div className="generation-progress-head">
            <span className="generation-progress-stage">
              <span className="generation-pulse" aria-hidden="true" />
              {STAGES[stageIndex]}
            </span>
            <span className="generation-progress-value">{Math.round(progress)}%</span>
          </div>
          <div className="generation-progress-track">
            <div
              className="generation-progress-fill"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      ) : null}
    </header>
  );
}
