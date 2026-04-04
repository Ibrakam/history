import type { LessonForm, VisualMode } from "./types";

export const VISUAL_MODES: Record<
  VisualMode,
  {
    name: string;
    description: string;
    accent: string;
    panel: string;
    deck: string;
    inspirations: Array<{ label: string; url: string; takeaway: string }>;
  }
> = {
  chronicle: {
    name: "Летопись",
    description: "Тёплая редакционная хроника с крупным заголовком, атмосферным hero и широкими повествовательными блоками.",
    accent: "#7e5431",
    panel: "#f3e9dc",
    deck: "Редакционная история с ощущением рукописи и музейной витрины.",
    inspirations: [
      {
        label: "The Met Timeline",
        url: "https://www.metmuseum.org/toah/",
        takeaway: "Крупная serif-типографика, сильный акцент на хронологии и ощущение академической истории.",
      },
      {
        label: "Library of Congress Exhibitions",
        url: "https://www.loc.gov/exhibitions/",
        takeaway: "Архивная подача, подписи к объектам и спокойная выставочная композиция.",
      },
    ],
  },
  empire: {
    name: "Империя",
    description: "Монументальная выставочная подача с театральным hero, насыщенными фактурами и тяжёлой исторической типографикой.",
    accent: "#8f2d1d",
    panel: "#efe2dc",
    deck: "Монументальная сцена для цивилизаций, династий и больших государств.",
    inspirations: [
      {
        label: "The Met Timeline",
        url: "https://www.metmuseum.org/toah/",
        takeaway: "Музейный масштаб, академическая ритмика и работа с историческими изображениями как с центральным экспонатом.",
      },
      {
        label: "British Museum Collection",
        url: "https://www.britishmuseum.org/collection",
        takeaway: "Чистая музейная подача предметов и акцент на материальных следах эпохи.",
      },
    ],
  },
  warfront: {
    name: "Фронт",
    description: "Драматичный документальный режим с сильным hero, контрастными блоками и мемориальной атмосферой.",
    accent: "#4d3135",
    panel: "#ece1e1",
    deck: "Документальная история для войн, кризисов, битв и переломных событий.",
    inspirations: [
      {
        label: "Imperial War Museums",
        url: "https://www.iwm.org.uk/history",
        takeaway: "Полноэкранные документальные герои, сильный контраст и подача как у военной онлайн-экспозиции.",
      },
      {
        label: "Library of Congress Exhibitions",
        url: "https://www.loc.gov/exhibitions/",
        takeaway: "Архивный нарратив и связка исторического текста с документальными визуальными источниками.",
      },
    ],
  },
  reform: {
    name: "Реформы",
    description: "Светлая журнальная подача с сеткой реформ, законов и фигур перемен, без ощущения скучного учебника.",
    accent: "#2a6958",
    panel: "#e2efe9",
    deck: "Современная историческая редактура для тем модернизации, законов и общественных изменений.",
    inspirations: [
      {
        label: "Library of Congress Exhibitions",
        url: "https://www.loc.gov/exhibitions/",
        takeaway: "Чистые выставочные панели и грамотное сочетание документов, пояснений и навигационных блоков.",
      },
      {
        label: "The Met Timeline",
        url: "https://www.metmuseum.org/toah/",
        takeaway: "Структурная ясность: большая мысль сверху, затем секции с понятным ритмом и визуальными якорями.",
      },
    ],
  },
  archive: {
    name: "Архив",
    description: "Холодный музейно-архивный режим с витринной сеткой, подписями к объектам и документальной дистанцией.",
    accent: "#1f4d5c",
    panel: "#e1edf0",
    deck: "Архивная экспозиция для документов, источников, хроник и исследовательских тем.",
    inspirations: [
      {
        label: "Library of Congress Exhibitions",
        url: "https://www.loc.gov/exhibitions/",
        takeaway: "Архивные панели, подписи к источникам и ощущение настоящей выставки документов.",
      },
      {
        label: "British Museum Collection",
        url: "https://www.britishmuseum.org/collection",
        takeaway: "Витринный подход к предметам и спокойная музейная подача без визуального шума.",
      },
    ],
  },
};

export const EMPTY_FORM = (): LessonForm => ({
  title: "",
  topic: "",
  heroSubtitle: "",
  visualMode: "chronicle",
  lessonLayout: null,
  lessonHtml: "",
  quiz: [
    {
      prompt: "Вопрос 1",
      options: ["Вариант 1", "Вариант 2", "Вариант 3", "Вариант 4"],
      correctOptionIndex: 0,
      explanation: "Краткое пояснение к правильному ответу.",
    },
    {
      prompt: "Вопрос 2",
      options: ["Вариант 1", "Вариант 2", "Вариант 3", "Вариант 4"],
      correctOptionIndex: 1,
      explanation: "Краткое пояснение к правильному ответу.",
    },
    {
      prompt: "Вопрос 3",
      options: ["Вариант 1", "Вариант 2", "Вариант 3", "Вариант 4"],
      correctOptionIndex: 2,
      explanation: "Краткое пояснение к правильному ответу.",
    },
  ],
});
