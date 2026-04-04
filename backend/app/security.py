from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from .config import get_settings


TOKEN_MAX_AGE_SECONDS = 60 * 60 * 12


def _serializer() -> URLSafeTimedSerializer:
    settings = get_settings()
    return URLSafeTimedSerializer(settings.session_secret, salt="history-admin")


def verify_admin_credentials(username: str, password: str) -> bool:
    settings = get_settings()
    return username == settings.admin_username and password == settings.admin_password


def create_access_token() -> str:
    return _serializer().dumps({"sub": "admin"})


def decode_access_token(token: str) -> dict | None:
    try:
        return _serializer().loads(token, max_age=TOKEN_MAX_AGE_SECONDS)
    except (BadSignature, SignatureExpired):
        return None

