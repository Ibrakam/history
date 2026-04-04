from __future__ import annotations


def infer_visual_mode(topic: str) -> str:
    normalized = topic.lower()
    if any(token in normalized for token in ["битв", "войн", "фронт", "наполеон", "вторая мировая", "первая мировая"]):
        return "warfront"
    if any(token in normalized for token in ["реформ", "петр", "александр ii", "перестройка", "модернизац"]):
        return "reform"
    if any(token in normalized for token in ["егип", "рим", "визант", "осман", "импери", "фараон"]):
        return "empire"
    if any(token in normalized for token in ["архив", "документ", "летопис", "источник", "музей"]):
        return "archive"
    return "chronicle"

