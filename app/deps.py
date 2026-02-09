from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request, status, Header
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import UsuarioSistema
from app.models.colaborador import ColaboradorCampo


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> UsuarioSistema:
    """Obtém o usuário autenticado via cookie access_token (JWT)."""
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Não autenticado.",
        )

    try:
        payload = decode_token(token)
        token_kind = payload.get("kind")
        if token_kind and token_kind != "admin":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido.",
            )
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido.",
        )

    user = (
        db.query(UsuarioSistema)
        .filter(UsuarioSistema.id == user_id, UsuarioSistema.ativo.is_(True))
        .first()
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado ou inativo.",
        )

    return user


def get_current_user_optional(
    request: Request,
    db: Session = Depends(get_db),
) -> UsuarioSistema | None:
    """Versão que não levanta 401 se não tiver token (tela de login)."""
    token = request.cookies.get("access_token")
    if not token:
        return None

    try:
        payload = decode_token(token)
        token_kind = payload.get("kind")
        if token_kind and token_kind != "admin":
            return None
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError, TypeError):
        return None

    return (
        db.query(UsuarioSistema)
        .filter(UsuarioSistema.id == user_id, UsuarioSistema.ativo.is_(True))
        .first()
    )


def require_admin(
    current_user: UsuarioSistema = Depends(get_current_user),
) -> UsuarioSistema:
    """Dependência para restringir rotas a usuários ADMIN."""
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores podem acessar.",
        )
    return current_user


def _is_expirado(expira_em: datetime | None) -> bool:
    if expira_em is None:
        return False
    if expira_em.tzinfo is None:
        expira_em = expira_em.replace(tzinfo=timezone.utc)
    return expira_em <= datetime.now(timezone.utc)


def get_current_colaborador(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> ColaboradorCampo:
    """Obtém colaborador autenticado via header Authorization: Bearer <token>."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Não autenticado.",
        )

    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido.",
        )

    try:
        payload = decode_token(token)
        token_kind = payload.get("kind")
        if token_kind != "colaborador":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido.",
            )
        colab_id = int(payload.get("sub"))
    except (JWTError, ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido.",
        )

    colab = (
        db.query(ColaboradorCampo)
        .filter(ColaboradorCampo.id == colab_id, ColaboradorCampo.ativo.is_(True))
        .first()
    )
    if not colab:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Colaborador não encontrado ou inativo.",
        )

    if _is_expirado(colab.expira_em):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Colaborador expirado.",
        )

    return colab
