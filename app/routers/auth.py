from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import UsuarioSistema
from app.models.colaborador import ColaboradorCampo
from app.schemas.auth import (
    LoginInput,
    UsuarioSistemaOut,
    ColaboradorLoginInput,
    ColaboradorLoginOut,
)
from app.schemas.colaborador import ColaboradorOut
from app.core.security import verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from app.deps import get_current_user, get_current_colaborador

router = APIRouter(prefix="/auth", tags=["Auth Web"])


@router.post("/login", response_model=UsuarioSistemaOut)
def login(
    data: LoginInput,
    response: Response,
    db: Session = Depends(get_db),
):
    user: UsuarioSistema | None = (
        db.query(UsuarioSistema)
        .filter(UsuarioSistema.email == data.email)
        .first()
    )

    if not user or not verify_password(data.senha, user.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas",
        )

    if not user.ativo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário inativo",
        )

    expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id), "kind": "admin"},
        expires_delta=expires_delta,
    )

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=False,  # Em produção, com HTTPS: True
        max_age=int(expires_delta.total_seconds()),
    )

    return user


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("access_token")
    return {"detail": "Logout efetuado com sucesso."}


@router.get("/me", response_model=UsuarioSistemaOut)
def me(current_user: UsuarioSistema = Depends(get_current_user)):
    return current_user


@router.post("/colaborador/login", response_model=ColaboradorLoginOut, tags=["Auth App"])
def login_colaborador(
    data: ColaboradorLoginInput,
    db: Session = Depends(get_db),
):
    usuario = (data.usuario or data.email or "").strip()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais invalidas",
        )

    colab: ColaboradorCampo | None = (
        db.query(ColaboradorCampo)
        .filter(ColaboradorCampo.email == usuario)
        .first()
    )

    if not colab or not colab.senha_hash or not verify_password(data.senha, colab.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais invalidas",
        )

    if not colab.ativo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Colaborador inativo",
        )

    if colab.expira_em is not None:
        expira_em = colab.expira_em
        if expira_em.tzinfo is None:
            expira_em = expira_em.replace(tzinfo=timezone.utc)
        if expira_em <= datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Colaborador expirado",
            )

    expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    expires_at = datetime.now(timezone.utc) + expires_delta
    access_token = create_access_token(
        data={"sub": str(colab.id), "kind": "colaborador"},
        expires_delta=expires_delta,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_at": expires_at,
        "expires_in": int(expires_delta.total_seconds()),
        "colaborador": colab,
    }


@router.get("/colaborador/me", response_model=ColaboradorOut, tags=["Auth App"])
def me_colaborador(
    current_colaborador: ColaboradorCampo = Depends(get_current_colaborador),
):
    return current_colaborador
