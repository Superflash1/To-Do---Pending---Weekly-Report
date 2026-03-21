from datetime import datetime, timedelta

from jose import jwt
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
BCRYPT_MAX_PASSWORD_BYTES = 72


def _validate_password_for_bcrypt(password: str) -> None:
    if len(password.encode("utf-8")) > BCRYPT_MAX_PASSWORD_BYTES:
        raise ValueError("Password too long (max 72 bytes for bcrypt).")


def hash_password(password: str) -> str:
    _validate_password_for_bcrypt(password)
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        _validate_password_for_bcrypt(plain_password)
    except ValueError:
        return False
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
