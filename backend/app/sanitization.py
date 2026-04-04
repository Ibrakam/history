import bleach


ALLOWED_TAGS = [
    "h1",
    "h2",
    "h3",
    "p",
    "ul",
    "ol",
    "li",
    "strong",
    "em",
    "blockquote",
    "table",
    "thead",
    "tbody",
    "tr",
    "th",
    "td",
    "hr",
    "br",
    "img",
]

ALLOWED_ATTRIBUTES = {
    "img": ["src", "alt", "title"],
    "th": ["colspan", "rowspan"],
    "td": ["colspan", "rowspan"],
}

ALLOWED_PROTOCOLS = ["http", "https"]


def sanitize_lesson_html(value: str) -> str:
    cleaned = bleach.clean(
        value,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )
    return bleach.linkify(cleaned)

