from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .config import ROOT_DIR, get_settings


MATERIALS_DIR = ROOT_DIR / "backend" / "materials"
INDEX_DIR = MATERIALS_DIR / ".index"
INDEX_PATH = INDEX_DIR / "material_chunks.json"
SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md"}
MOJIBAKE_CHARS = set("ÐÑÂÃÄÅÆÇÈÉÊËÌÍÎÏÒÓÔÕÖ×ØÙÚÛÜÝÞßàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ")
COLLECTION_LABELS = {
    "uzbekistan_history": "История Узбекистана",
    "history": "Всемирная история",
}
STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "что",
    "как",
    "или",
    "это",
    "его",
    "для",
    "при",
    "над",
    "под",
    "был",
    "были",
    "была",
    "они",
    "она",
    "оно",
    "ўз",
    "ва",
    "бу",
    "ҳам",
    "эди",
    "эса",
    "учун",
    "билан",
}
ORDINAL_TOKENS = {
    "первая",
    "первой",
    "первую",
    "первого",
    "вторая",
    "второй",
    "вторую",
    "второго",
}


@dataclass(frozen=True)
class SourceChunk:
    id: str
    collection: str
    collectionLabel: str
    sourceTitle: str
    sourcePath: str
    pageStart: int | None
    pageEnd: int | None
    text: str
    score: float = 0.0

    def to_prompt_block(self, index: int, max_chars: int = 1400) -> str:
        page = ""
        if self.pageStart:
            page = f", стр. {self.pageStart}" if self.pageStart == self.pageEnd else f", стр. {self.pageStart}-{self.pageEnd}"
        text = self.text.strip()
        if len(text) > max_chars:
            text = f"{text[:max_chars].rsplit(' ', 1)[0]}..."
        return (
            f"[Источник {index}: {self.collectionLabel}; {self.sourceTitle}{page}]\n"
            f"{text}"
        )


def _normalize_text(text: str) -> str:
    text = _repair_mojibake(text)
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _repair_mojibake(text: str) -> str:
    if not text:
        return text
    sample = text[:4000]
    mojibake_count = sum(1 for char in sample if char in MOJIBAKE_CHARS)
    cyrillic_count = len(re.findall(r"[А-Яа-яЁёЎўҚқҒғҲҳІі]", sample))
    if mojibake_count < 20 or mojibake_count <= cyrillic_count:
        return text
    try:
        repaired = text.encode("latin1", errors="ignore").decode("cp1251", errors="ignore")
    except Exception:
        return text
    if len(re.findall(r"[А-Яа-яЁё]", repaired)) > cyrillic_count:
        return repaired
    return text


def _tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[A-Za-zА-Яа-яЁёЎўҚқҒғҲҳІіʼ'’-]{3,}|\d{3,4}", text.lower().replace("ё", "е"))
    normalized = []
    for token in tokens:
        token = _stem_token(token.strip("'’ʼ-"))
        if token and token not in STOPWORDS:
            normalized.append(token)
    return normalized


def _stem_token(token: str) -> str:
    if token in {"русь", "руси", "русью"}:
        return "рус"
    if token.startswith("киевск"):
        return "киевск"
    if token.startswith("русск"):
        return "русск"
    if token.startswith("росси"):
        return "росси"
    if token.isdigit():
        return token
    for suffix in (
        "иями",
        "ями",
        "ами",
        "ого",
        "ему",
        "ыми",
        "ими",
        "ая",
        "яя",
        "ую",
        "юю",
        "ые",
        "ие",
        "ый",
        "ий",
        "ой",
        "ых",
        "их",
        "ого",
        "его",
        "ам",
        "ям",
        "ах",
        "ях",
        "ом",
        "ем",
        "а",
        "я",
        "ы",
        "и",
        "е",
        "у",
        "ю",
    ):
        if len(token) - len(suffix) >= 4 and token.endswith(suffix):
            return token[: -len(suffix)]
    return token


def _query_tokens(topic: str) -> list[str]:
    tokens = _tokenize(topic)
    token_set = set(tokens)
    if "рус" in token_set or "русск" in token_set or "росси" in token_set:
        tokens.extend(["рус", "русск", "росси", "киевск", "москв", "рюрик", "иван"])
    ordered: list[str] = []
    for token in tokens:
        if token and token not in ordered:
            ordered.append(token)
    return ordered


def _sentence_split(text: str) -> list[str]:
    prepared = re.sub(r"([A-Za-zА-Яа-яЁёЎўҚқҒғҲҳІі])- +([A-Za-zА-Яа-яЁёЎўҚқҒғҲҳІі])", r"\1\2", text)
    prepared = re.sub(r"\s+", " ", prepared)
    sentences = re.split(r"(?<=[.!?])\s+", prepared)
    cleaned = []
    for sentence in sentences:
        sentence = re.sub(r"^\d{1,3}\s+", "", sentence.strip(" .;:"))
        sentence = re.sub(r"\s+", " ", sentence)
        if 45 <= len(sentence) <= 260:
            cleaned.append(sentence)
    return cleaned


def _source_statement_candidates(chunks: list[SourceChunk], topic: str, limit: int = 12) -> list[str]:
    query_tokens = set(_query_tokens(topic))
    query_ordinals = query_tokens & ORDINAL_TOKENS
    statements: list[str] = []
    seen: set[str] = set()
    for chunk in chunks:
        for sentence in _sentence_split(chunk.text):
            if re.search(r"\b(ЗАДАНИЕ|ЗA ДАНИЕ|ТВОРЧЕСКОЙ|Расскажите|Какие|Чем)\b", sentence, flags=re.IGNORECASE):
                continue
            cause_index = sentence.find("Причиной")
            if cause_index > 0:
                sentence = sentence[cause_index:]
            sentence_tokens = set(_tokenize(sentence))
            sentence_ordinals = sentence_tokens & ORDINAL_TOKENS
            if query_ordinals and sentence_ordinals and not (query_ordinals & sentence_ordinals):
                continue
            has_topic_word = bool(query_tokens & sentence_tokens)
            has_date = bool(re.search(r"\b\d{3,4}\b", sentence))
            if not has_topic_word and not has_date:
                continue
            normalized = sentence.lower()
            if normalized in seen:
                continue
            seen.add(normalized)
            statements.append(sentence)
            if len(statements) >= limit:
                return statements
    return statements


def source_statement_candidates(chunks: list[SourceChunk], topic: str, limit: int = 12) -> list[str]:
    return _source_statement_candidates(chunks, topic, limit=limit)


def _year_distractors(year: int) -> list[str]:
    offsets = [-4, 3, 9, 12, -11]
    values = [str(year + offset) for offset in offsets if year + offset > 0]
    return values[:3]


def _quiz_options(correct: str, distractors: list[str]) -> tuple[list[str], int]:
    unique: list[str] = []
    for option in [correct, *distractors]:
        option = option.strip()
        if option and option not in unique:
            unique.append(option)
    while len(unique) < 4:
        unique.append(f"Неточный вариант {len(unique)}")
    options = unique[:4]
    return options, options.index(correct)


def build_source_quiz(topic: str, chunks: list[SourceChunk], min_questions: int = 5) -> list[dict]:
    statements = _source_statement_candidates(chunks, topic, limit=18)
    questions: list[dict] = []

    for statement in statements:
        year_match = re.search(r"\b(1\d{3}|20\d{2})\b", statement)
        if not year_match:
            continue
        year = int(year_match.group(1))
        fact = re.sub(r"\b\d{3,4}\b(?:\s*г(?:ода|оду|\.)?)?", "____", statement, count=1)
        options, correct_index = _quiz_options(str(year), _year_distractors(year))
        questions.append(
            {
                "prompt": f"Какой год пропущен в факте из учебника по теме «{topic}»: «{fact}»?",
                "options": options,
                "correctOptionIndex": correct_index,
                "explanation": f"В учебном материале указан год {year}: {statement}",
            }
        )
        if len(questions) >= 2:
            break

    for statement in statements:
        lowered = statement.lower()
        if "причин" not in lowered and "послуж" not in lowered:
            continue
        options, correct_index = _quiz_options(
            statement,
            [
                "только культурные изменения без политических причин",
                "случайное событие без связи с международной обстановкой",
                "реформа школьного образования",
            ],
        )
        questions.append(
            {
                "prompt": f"Какой факт о причинах относится к теме «{topic}» согласно учебнику?",
                "options": options,
                "correctOptionIndex": correct_index,
                "explanation": statement,
            }
        )
        break

    for statement in statements:
        if len(questions) >= min_questions:
            break
        if any(statement in question["explanation"] for question in questions):
            continue
        options, correct_index = _quiz_options(
            statement,
            [
                f"Учебник утверждает, что тема «{topic}» не связана с историческими событиями.",
                "Главным содержанием темы является только описание современных технологий.",
                "Материал сводит тему к художественному вымыслу без фактов.",
            ],
        )
        questions.append(
            {
                "prompt": f"Какое утверждение подтверждается учебником по теме «{topic}»?",
                "options": options,
                "correctOptionIndex": correct_index,
                "explanation": statement,
            }
        )

    return questions[:max(min_questions, 3)]


def _file_signature(path: Path) -> dict:
    stat = path.stat()
    return {
        "path": str(path.relative_to(MATERIALS_DIR)),
        "mtime": stat.st_mtime,
        "size": stat.st_size,
    }


def _discover_material_files() -> list[Path]:
    if not MATERIALS_DIR.exists():
        return []
    return sorted(
        path
        for path in MATERIALS_DIR.rglob("*")
        if path.is_file()
        and path.suffix.lower() in SUPPORTED_EXTENSIONS
        and ".index" not in path.parts
        and not path.name.startswith(".")
    )


def _read_text_file(path: Path) -> list[tuple[int | None, str]]:
    return [(None, _normalize_text(path.read_text(encoding="utf-8", errors="ignore")))]


def _read_pdf_with_pypdf(path: Path) -> list[tuple[int | None, str]]:
    try:
        from pypdf import PdfReader
    except Exception as exc:
        raise RuntimeError("pypdf is not installed") from exc

    reader = PdfReader(str(path))
    pages: list[tuple[int | None, str]] = []
    for index, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        pages.append((index, _normalize_text(text)))
    return pages


def _read_pdf_with_pdftotext(path: Path) -> list[tuple[int | None, str]]:
    result = subprocess.run(
        ["pdftotext", "-layout", str(path), "-"],
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )
    pages = result.stdout.split("\f")
    return [(index, _normalize_text(page)) for index, page in enumerate(pages, start=1) if page.strip()]


def _read_pdf(path: Path) -> list[tuple[int | None, str]]:
    try:
        pages = _read_pdf_with_pypdf(path)
        if any(text for _, text in pages):
            return pages
    except Exception:
        pass
    return _read_pdf_with_pdftotext(path)


def _collection_for_path(path: Path) -> str:
    relative = path.relative_to(MATERIALS_DIR)
    return relative.parts[0] if len(relative.parts) > 1 else "history"


def _source_title(path: Path) -> str:
    return path.stem.replace("_", " ").replace("-", " ").strip()


def _chunk_page_text(page: int | None, text: str, max_chars: int = 1800) -> list[dict]:
    paragraphs = [paragraph.strip() for paragraph in re.split(r"\n\s*\n", text) if paragraph.strip()]
    chunks: list[dict] = []
    current: list[str] = []
    current_len = 0

    def flush() -> None:
        nonlocal current, current_len
        joined = _normalize_text("\n\n".join(current))
        if len(joined) >= 120:
            chunks.append({"pageStart": page, "pageEnd": page, "text": joined})
        current = []
        current_len = 0

    for paragraph in paragraphs:
        if len(paragraph) > max_chars:
            flush()
            sentences = re.split(r"(?<=[.!?])\s+", paragraph)
            for sentence in sentences:
                if not sentence.strip():
                    continue
                if current_len + len(sentence) > max_chars:
                    flush()
                current.append(sentence.strip())
                current_len += len(sentence) + 1
            continue

        if current_len + len(paragraph) > max_chars:
            flush()
        current.append(paragraph)
        current_len += len(paragraph) + 2

    flush()
    return chunks


def _build_chunks_for_file(path: Path) -> list[dict]:
    collection = _collection_for_path(path)
    source_title = _source_title(path)
    relative_path = str(path.relative_to(ROOT_DIR))
    if path.suffix.lower() == ".pdf":
        pages = _read_pdf(path)
    else:
        pages = _read_text_file(path)

    chunks: list[dict] = []
    for page, text in pages:
        for chunk in _chunk_page_text(page, text):
            if not _tokenize(chunk["text"]):
                continue
            chunk_index = len(chunks) + 1
            chunks.append(
                {
                    "id": f"{collection}:{path.stem}:{page or 0}:{chunk_index}",
                    "collection": collection,
                    "collectionLabel": COLLECTION_LABELS.get(collection, collection),
                    "sourceTitle": source_title,
                    "sourcePath": relative_path,
                    "pageStart": chunk["pageStart"],
                    "pageEnd": chunk["pageEnd"],
                    "text": chunk["text"],
                }
            )
    return chunks


def _load_index() -> dict | None:
    if not INDEX_PATH.exists():
        return None
    try:
        return json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None


def _index_is_current(index: dict, files: list[Path]) -> bool:
    return index.get("version") == 1 and index.get("files") == [_file_signature(path) for path in files]


def build_material_index(force: bool = False) -> dict:
    files = _discover_material_files()
    existing = _load_index()
    if existing and not force and _index_is_current(existing, files):
        return existing

    chunks: list[dict] = []
    errors: list[dict] = []
    for path in files:
        try:
            chunks.extend(_build_chunks_for_file(path))
        except Exception as exc:
            errors.append({"path": str(path.relative_to(ROOT_DIR)), "error": str(exc)})

    index = {
        "version": 1,
        "files": [_file_signature(path) for path in files],
        "chunks": chunks,
        "errors": errors,
    }
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    return index


def _score_chunk(chunk: dict, query_tokens: list[str], collection: str | None, strict_rus: bool = False) -> float:
    searchable_text = f"{chunk.get('sourceTitle', '')} {chunk.get('text', '')}"
    text_tokens = _tokenize(searchable_text)
    if not text_tokens or not query_tokens:
        return 0.0
    text_token_set = set(text_tokens)
    if strict_rus and not ({"рус", "киевск"} & text_token_set):
        return 0.0
    exact_matches = sum(1 for token in query_tokens if token in text_token_set)
    if exact_matches == 0:
        return 0.0
    if len(query_tokens) >= 2 and exact_matches / len(query_tokens) < 0.5:
        return 0.0
    query_ordinals = set(query_tokens) & ORDINAL_TOKENS
    if query_ordinals and not query_ordinals & text_token_set:
        return 0.0

    token_counts: dict[str, int] = {}
    for token in text_tokens:
        token_counts[token] = token_counts.get(token, 0) + 1

    score = 0.0
    for token in query_tokens:
        score += min(token_counts.get(token, 0), 6)
        if any(text_token.startswith(token) or token.startswith(text_token) for text_token in text_tokens):
            score += 0.35
    normalized_query = " ".join(query_tokens)
    normalized_text = " ".join(text_tokens)
    if normalized_query and normalized_query in normalized_text:
        score += 8.0
    if collection and chunk.get("collection") == collection:
        score *= 1.35
    if "lecture" in chunk.get("sourcePath", "").lower():
        score *= 1.12
    return score


def search_materials(topic: str, collection: str | None = None, limit: int | None = None) -> list[SourceChunk]:
    settings = get_settings()
    if not settings.enable_source_materials:
        return []

    original_query_tokens = _tokenize(topic)
    query_tokens = _query_tokens(topic)
    strict_rus = "рус" in original_query_tokens
    if not query_tokens:
        return []

    index = build_material_index()
    limit = limit or settings.source_material_limit
    min_score = settings.source_material_min_score
    scored: list[SourceChunk] = []
    seen_source_pages: set[tuple[str, int | None]] = set()

    for chunk in index.get("chunks", []):
        if collection and chunk.get("collection") != collection:
            continue
        score = _score_chunk(chunk, query_tokens, collection, strict_rus)
        if score < min_score:
            continue
        source_page_key = (chunk.get("sourcePath", ""), chunk.get("pageStart"))
        if source_page_key in seen_source_pages and score < 3:
            continue
        seen_source_pages.add(source_page_key)
        scored.append(
            SourceChunk(
                id=chunk["id"],
                collection=chunk["collection"],
                collectionLabel=chunk["collectionLabel"],
                sourceTitle=chunk["sourceTitle"],
                sourcePath=chunk["sourcePath"],
                pageStart=chunk.get("pageStart"),
                pageEnd=chunk.get("pageEnd"),
                text=chunk["text"],
                score=score,
            )
        )

    scored.sort(key=lambda item: item.score, reverse=True)
    return scored[:limit]


def format_source_context(chunks: list[SourceChunk], max_chars: int = 1400) -> str:
    return "\n\n".join(chunk.to_prompt_block(index, max_chars=max_chars) for index, chunk in enumerate(chunks, start=1))
