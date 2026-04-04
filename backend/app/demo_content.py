from __future__ import annotations

from .media import build_demo_asset
from .theme_logic import infer_visual_mode


def build_demo_lesson(topic: str) -> dict:
    normalized_topic = topic.strip() or "История"
    visual_mode = infer_visual_mode(normalized_topic)
    image_slots = [
        {
            "slotId": "hero-main",
            "label": f"{normalized_topic} hero",
            "searchQueries": [
                f"{normalized_topic} историческая живопись",
                f"{normalized_topic} реконструкция",
                f"{normalized_topic} архитектура",
            ],
            "role": "hero",
        },
        {
            "slotId": "narrative-1",
            "label": f"{normalized_topic} историческая сцена",
            "searchQueries": [normalized_topic, f"историческая сцена {normalized_topic}", f"жизнь {normalized_topic}"],
            "role": "section",
        },
        {
            "slotId": "timeline-1",
            "label": f"{normalized_topic} хронология",
            "searchQueries": [f"{normalized_topic} карта", f"{normalized_topic} chronology", f"{normalized_topic} схема"],
            "role": "timeline",
        },
        {
            "slotId": "person-1",
            "label": f"Правители: {normalized_topic}",
            "searchQueries": [f"{normalized_topic} портрет правителя", f"{normalized_topic} князь", f"{normalized_topic} правитель"],
            "role": "person",
        },
        {
            "slotId": "artifact-1",
            "label": f"Артефакты: {normalized_topic}",
            "searchQueries": [f"{normalized_topic} артефакт", f"{normalized_topic} архитектура", f"{normalized_topic} предметы культуры"],
            "role": "artifact",
        },
        {
            "slotId": "quote-1",
            "label": f"Документ: {normalized_topic}",
            "searchQueries": [f"{normalized_topic} летопись", f"{normalized_topic} рукопись", f"{normalized_topic} исторический документ"],
            "role": "quote",
        },
    ]

    for slot in image_slots:
        demo_asset = build_demo_asset(slot["label"], visual_mode, slot["slotId"])
        slot["selectedAsset"] = demo_asset.model_dump()
        slot["candidateAssets"] = [demo_asset.model_dump()]

    return {
        "title": f"{normalized_topic}: визуальный урок",
        "topic": normalized_topic,
        "heroSubtitle": "Исторический лендинг с крупными образами, секциями, персонажами и мини-тестом.",
        "visualMode": visual_mode,
        "lessonLayout": {
            "visualMode": visual_mode,
            "hero": {
                "eyebrow": "Урок истории",
                "intro": "Разберём причины, события, личности и культурный образ эпохи в формате визуального школьного проекта.",
                "slotId": "hero-main",
            },
            "sections": [
                {
                    "id": "overview",
                    "blockType": "narrative",
                    "title": "Исторический фон",
                    "lead": "Сначала важно увидеть, в какой среде возникает тема и почему она становится переломной.",
                    "body": [
                        f"{normalized_topic} удобно объяснять через общий политический фон, интересы правителей и влияние соседних государств.",
                        "Для школьного урока лучше связывать события в одну линию: предпосылки, ключевой момент, последствия для общества.",
                    ],
                    "slotId": "narrative-1",
                    "visible": True,
                },
                {
                    "id": "timeline",
                    "blockType": "timeline",
                    "title": "Ключевые события",
                    "lead": "Ниже краткая хронология, которая помогает быстро понять развитие темы.",
                    "timelineItems": [
                        {
                            "year": "1 этап",
                            "title": "Предпосылки",
                            "description": "Формируются условия, из-за которых историческое изменение становится возможным.",
                        },
                        {
                            "year": "2 этап",
                            "title": "Переломный момент",
                            "description": "Происходит событие, вокруг которого строится основная линия урока.",
                        },
                        {
                            "year": "3 этап",
                            "title": "Последствия",
                            "description": "Новые порядки и изменения закрепляются и влияют на дальнейшую историю.",
                        },
                    ],
                    "slotId": "timeline-1",
                    "visible": True,
                },
                {
                    "id": "people",
                    "blockType": "person_card_grid",
                    "title": "Личности эпохи",
                    "lead": "Через конкретных людей тема становится понятнее и живее.",
                    "personCards": [
                        {
                            "name": "Ключевая фигура",
                            "role": "Правитель / лидер",
                            "summary": "Показывает, как личные решения влияют на ход истории.",
                            "slotId": "person-1",
                        }
                    ],
                    "visible": True,
                },
                {
                    "id": "artifacts",
                    "blockType": "artifact_gallery",
                    "title": "Материальные следы эпохи",
                    "lead": "Артефакты и изображения помогают почувствовать реальную культуру времени.",
                    "artifactCards": [
                        {
                            "title": "Знак эпохи",
                            "summary": "Любой предмет, документ или художественный образ, который символизирует период.",
                            "slotId": "artifact-1",
                        }
                    ],
                    "visible": True,
                },
                {
                    "id": "quote",
                    "blockType": "quote_callout",
                    "title": "Исторический акцент",
                    "quoteText": "История сильнее запоминается, когда событие можно увидеть не только в тексте, но и в образах эпохи.",
                    "quoteCaption": "Подходит для устной защиты проекта.",
                    "slotId": "quote-1",
                    "visible": True,
                },
            ],
            "imageSlots": image_slots,
        },
        "quiz": [
            {
                "prompt": f"С чего лучше начинать объяснение темы «{normalized_topic}»?",
                "options": [
                    "С исторического фона и причин",
                    "Случайно с любого факта",
                    "Только с дат без объяснения",
                    "Только с биографии правителя",
                ],
                "correctOptionIndex": 0,
                "explanation": "Историческую тему лучше раскрывать через причины и общий контекст.",
            },
            {
                "prompt": "Зачем включать в урок визуальные образы эпохи?",
                "options": [
                    "Чтобы просто занять место",
                    "Чтобы связать текст с культурой и атмосферой времени",
                    "Чтобы заменить весь учебный материал",
                    "Чтобы не делать выводы",
                ],
                "correctOptionIndex": 1,
                "explanation": "Изображения помогают лучше представить эпоху и удержать внимание.",
            },
            {
                "prompt": "Что делает урок более понятным для школьника?",
                "options": [
                    "Одна длинная цитата без структуры",
                    "Набор несвязанных дат",
                    "Причинно-следственная логика и понятные блоки",
                    "Только список имён",
                ],
                "correctOptionIndex": 2,
                "explanation": "Структура и логика делают материал доступным для восприятия.",
            },
        ],
    }
