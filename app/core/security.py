from datetime import datetime, timedelta
from typing import Optional

import base64
import hashlib
from jose import jwt
from passlib.context import CryptContext

# TROCAR por algo forte e vindo de variável de ambiente em produção
SECRET_KEY = "mude-esta-chave-para-uma-bem-grande-e-secreta"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# argon2 primeiro => novos hashes serão argon2 (sem limite de 72 bytes)
# bcrypt fica para verificar hashes antigos, se existirem
pwd_context = CryptContext(
    schemes=["argon2", "bcrypt"],
    deprecated="auto",
)

_BCRYPT_PREFIXES = ("$2a$", "$2b$", "$2y$")


def _bcrypt_safe_secret(password: str) -> bytes:
    """
    bcrypt só aceita até 72 bytes.
    Se passar disso, fazemos pre-hash (SHA-256) e codificamos em base64 urlsafe
    para ficar bem abaixo de 72 bytes, evitando ValueError.
    """
    raw = (password or "").encode("utf-8")
    if len(raw) <= 72:
        return raw
    digest = hashlib.sha256(raw).digest()
    return base64.urlsafe_b64encode(digest)  # 44 bytes


def get_password_hash(password: str) -> str:
    # Vai gerar argon2 por padrão
    return pwd_context.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    try:
        # Se o hash armazenado for bcrypt, use segredo "safe" (bytes)
        if hashed_password.startswith(_BCRYPT_PREFIXES):
            secret = _bcrypt_safe_secret(password)
            return pwd_context.verify(secret, hashed_password)

        # Para argon2 (e outros futuros), pode verificar direto
        return pwd_context.verify(password, hashed_password)

    except ValueError:
        # Evita 500 (ex.: senha > 72 bytes no bcrypt)
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
