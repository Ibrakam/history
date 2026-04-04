# History AI

Школьный full-stack проект: учитель вводит тему урока истории, система генерирует визуальный лендинг-урок с тематическими блоками, изображениями и тестом, после чего урок можно отредактировать и опубликовать для учеников.

## Что умеет

- вход в админку по одному логину и паролю
- генерация структурированного урока по теме через OpenAI API
- автоматический подбор исторических изображений из Wikimedia Commons
- AI hero fallback для верхнего баннера, если хорошие реальные изображения не найдены
- fallback на demo-режим без API
- ручное редактирование блоков, изображений и тестов
- публикация урока по ссылке
- прохождение теста без регистрации
- мгновенная проверка результата без сохранения ответов учеников

## Стек

- Backend: FastAPI + SQLAlchemy + SQLite
- Frontend: React + Vite + TypeScript
- AI: OpenAI Responses API + OpenAI Images API для hero fallback

## Быстрый запуск

### 1. Настройка переменных окружения

```bash
cp .env.example .env
```

Заполните минимум:

```env
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
SESSION_SECRET=change-me
OPENAI_API_KEY=
USE_DEMO_AI=true
```

Для защиты проекта можно начать с `USE_DEMO_AI=true`, а затем переключиться на реальный API.

Примечание: приложение читает ключи из корневого `.env` с приоритетом над глобальными переменными окружения. После смены `OPENAI_API_KEY` нужно полностью перезапустить backend.

### 2. Backend

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload
```

Backend стартует на `http://127.0.0.1:8000`.

### 3. Frontend

Во втором терминале:

```bash
cd frontend
npm install
npm run dev
```

Frontend стартует на `http://127.0.0.1:5173`.

## API

- `POST /api/admin/login`
- `GET /api/admin/me`
- `GET /api/admin/lessons`
- `GET /api/admin/lessons/{id}`
- `POST /api/admin/lessons/generate`
- `POST /api/admin/lessons`
- `PUT /api/admin/lessons/{id}`
- `POST /api/admin/lessons/{id}/refresh-slot-images`
- `POST /api/admin/lessons/{id}/publish`
- `POST /api/admin/lessons/{id}/unpublish`
- `GET /api/public/lessons/{slug}`
- `POST /api/public/lessons/{slug}/submit-quiz`

## Тесты

```bash
source .venv/bin/activate
pytest backend/tests
```

## OpenAI

Интеграция сделана через `POST /v1/responses` и JSON Schema-формат ответа. Для hero fallback используется OpenAI image generation. Основные источники по реализации:

- [OpenAI Responses API](https://platform.openai.com/docs/api-reference/responses)
- [Structured Outputs](https://platform.openai.com/docs/guides/structured-outputs)
- [Image Generation](https://platform.openai.com/docs/guides/image-generation)
