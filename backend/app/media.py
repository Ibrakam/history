from __future__ import annotations

import asyncio
import time
from urllib.parse import quote

import httpx

from .config import get_settings
from .schemas import MediaAsset


VISUAL_ACCENTS = {
    "chronicle": "#7e5431",
    "empire": "#8f2d1d",
    "warfront": "#3f2b2d",
    "reform": "#2a6958",
    "archive": "#1f4d5c",
}

_CACHE: dict[str, tuple[float, list[MediaAsset]]] = {}
_CACHE_TTL = 300  # 5 minutes


def build_search_queries(label: str, topic: str, role: str, existing_queries: list[str] | None = None) -> list[str]:
    base_queries = [q for q in (existing_queries or []) if isinstance(q, str) and q.strip()]

    role_queries = {
        "hero": [f"{topic} историческая живопись", f"{topic} реконструкция", f"{topic} архитектура"],
        "section": [label or topic, f"историческая сцена {topic}", topic],
        "timeline": [f"{topic} карта", f"{topic} хронология", f"{topic} схема"],
        "person": [label or topic, f"{label} портрет" if label else f"{topic} исторический портрет", f"{topic} исторический портрет"],
        "artifact": [label or topic, f"{topic} артефакт", f"{topic} предметы культуры"],
        "quote": [label or topic, f"{topic} рукопись", f"{topic} исторический документ"],
    }.get(role, [label or topic, topic])

    ordered: list[str] = []
    for query in [*role_queries, *base_queries]:
        normalized = query.strip()
        if normalized and normalized not in ordered:
            ordered.append(normalized)
    return ordered[:6]


def build_demo_asset(label: str, visual_mode: str, slot_id: str) -> MediaAsset:
    accent = VISUAL_ACCENTS.get(visual_mode, VISUAL_ACCENTS["chronicle"])
    svg = f"""
    <svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1000" viewBox="0 0 1600 1000">
      <defs>
        <linearGradient id="bg" x1="0" x2="1" y1="0" y2="1">
          <stop offset="0%" stop-color="{accent}" />
          <stop offset="100%" stop-color="#111111" />
        </linearGradient>
      </defs>
      <rect width="1600" height="1000" fill="url(#bg)" />
      <circle cx="1320" cy="160" r="220" fill="rgba(255,255,255,0.08)" />
      <circle cx="280" cy="860" r="260" fill="rgba(255,255,255,0.06)" />
      <rect x="140" y="140" width="1320" height="720" rx="36" fill="rgba(255,255,255,0.08)" stroke="rgba(255,255,255,0.16)" />
      <text x="180" y="360" fill="#f5ead8" font-size="54" font-family="Georgia, serif" letter-spacing="7">History AI</text>
      <text x="180" y="470" fill="white" font-size="112" font-family="Georgia, serif">{label[:28]}</text>
      <text x="180" y="560" fill="rgba(255,255,255,0.78)" font-size="34" font-family="Arial, sans-serif">Демо-иллюстрация для визуального макета урока</text>
    </svg>
    """.strip()
    data_url = f"data:image/svg+xml;charset=utf-8,{quote(svg)}"
    return MediaAsset(
        assetId=f"demo-{slot_id}",
        title=f"{label} (демо)",
        imageUrl=data_url,
        thumbUrl=data_url,
        sourceUrl="",
        author="History AI",
        license="demo",
        provider="demo",
        alt=label,
    )


def _is_supported_image(url: str) -> bool:
    lowered = url.lower()
    return lowered.endswith((".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"))


async def _search_single_query(client: httpx.AsyncClient, query: str, limit: int) -> list[MediaAsset]:
    assets: list[MediaAsset] = []
    seen_urls: set[str] = set()

    for project in ("ru", "en"):
        if len(assets) >= limit:
            break

        try:
            response = await client.get(
                f"https://{project}.wikipedia.org/w/rest.php/v1/search/title",
                params={"q": query, "limit": str(limit)},
            )
            response.raise_for_status()
            pages = response.json().get("pages", [])
        except Exception:
            continue

        for page in pages:
            if len(assets) >= limit:
                break
            key = page.get("key")
            if not key:
                continue

            try:
                summary_response = await client.get(
                    f"https://{project}.wikipedia.org/api/rest_v1/page/summary/{key}",
                )
                summary_response.raise_for_status()
                summary = summary_response.json()
            except Exception:
                continue

            thumbnail = summary.get("thumbnail", {})
            image_url = thumbnail.get("source")
            if image_url and image_url.startswith("//"):
                image_url = f"https:{image_url}"
            if not image_url or image_url in seen_urls or not _is_supported_image(image_url):
                continue

            source_url = (
                summary.get("content_urls", {})
                .get("desktop", {})
                .get("page", f"https://{project}.wikipedia.org/wiki/{key}")
            )
            title = summary.get("title") or page.get("title") or key.replace("_", " ")
            description = summary.get("extract") or page.get("description") or title

            assets.append(
                MediaAsset(
                    assetId=f"wikimedia-{project}-{page.get('id', key)}",
                    title=title,
                    imageUrl=image_url,
                    thumbUrl=image_url,
                    sourceUrl=source_url,
                    author=f"{project}.wikipedia.org",
                    license="wikimedia",
                    provider="wikimedia",
                    alt=str(description)[:180] or title,
                )
            )
            seen_urls.add(image_url)

    return assets


async def search_wikimedia_assets(queries: list[str], limit: int = 6) -> list[MediaAsset]:
    cache_key = "|".join(queries[:4])
    now = time.monotonic()
    cached = _CACHE.get(cache_key)
    if cached and (now - cached[0]) < _CACHE_TTL:
        return cached[1][:limit]

    async with httpx.AsyncClient(
        timeout=20.0,
        headers={"User-Agent": "HistoryAI/1.0 (school-project contact: local-app)"},
    ) as client:
        tasks = [_search_single_query(client, q.strip(), limit) for q in queries if q.strip()]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    seen_urls: set[str] = set()
    assets: list[MediaAsset] = []
    for result in results:
        if isinstance(result, Exception):
            continue
        for asset in result:
            if asset.imageUrl not in seen_urls and len(assets) < limit:
                assets.append(asset)
                seen_urls.add(asset.imageUrl)

    _CACHE[cache_key] = (now, assets)
    return assets[:limit]


async def generate_ai_hero_asset(topic: str, hero_subtitle: str, visual_mode: str) -> MediaAsset | None:
    settings = get_settings()
    if not settings.openai_api_key:
        return None

    payload = {
        "model": settings.openai_image_model,
        "prompt": (
            f"Исторический cinematic hero banner для школьного урока по теме '{topic}'. "
            f"Настроение: {hero_subtitle}. Визуальный режим: {visual_mode}. "
            "Без текста, без водяных знаков, живописно, эпично, академично."
        ),
        "size": "1536x1024",
    }

    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{settings.openai_base_url.rstrip('/')}/images/generations",
                headers=headers,
                json=payload,
            )
    except Exception:
        return None

    if response.status_code >= 400:
        return None

    data = response.json().get("data", [])
    if not data:
        return None

    image = data[0]
    b64_json = image.get("b64_json")
    image_url = image.get("url")
    if b64_json:
        image_url = f"data:image/png;base64,{b64_json}"
    if not image_url:
        return None

    return MediaAsset(
        assetId=f"openai-hero-{visual_mode}",
        title=f"AI hero: {topic}",
        imageUrl=image_url,
        thumbUrl=image_url,
        sourceUrl="",
        author="OpenAI",
        license="generated",
        provider="openai",
        alt=f"Иллюстрация по теме {topic}",
    )
