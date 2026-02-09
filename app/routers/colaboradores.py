from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.db.session import get_db
from app.models.colaborador import ColaboradorCampo
from app.models.user import UsuarioSistema
from app.schemas.colaborador import (
    ColaboradorCreate,
    ColaboradorUpdate,
    ColaboradorOut,
)
from app.deps import get_current_user, require_admin

router = APIRouter(
    prefix="/api/colaboradores",
    tags=["Colaboradores de Campo"],
    dependencies=[Depends(require_admin)],  # so ADMIN pode gerenciar
)


@router.get("/", response_model=List[ColaboradorOut])
def listar_colaboradores(
    db: Session = Depends(get_db),
):
    return db.query(ColaboradorCampo).order_by(ColaboradorCampo.nome).all()


@router.post("/", response_model=ColaboradorOut, status_code=status.HTTP_201_CREATED)
def criar_colaborador(
    data: ColaboradorCreate,
    db: Session = Depends(get_db),
    current_user: UsuarioSistema = Depends(get_current_user),
):
    if not data.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="E-mail e obrigatorio para login no app.",
        )

    email_exists = (
        db.query(ColaboradorCampo)
        .filter(ColaboradorCampo.email == data.email)
        .first()
    )
    if email_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ja existe um colaborador com este e-mail.",
        )

    if not data.senha or not data.senha.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Senha e obrigatoria para login no app.",
        )

    colaborador = ColaboradorCampo(
        nome=data.nome,
        email=data.email,
        telefone=data.telefone,
        documento=data.documento,
        senha_hash=get_password_hash(data.senha),
        ativo=data.ativo,
        expira_em=data.expira_em,
        criado_por=current_user.id,
    )
    db.add(colaborador)
    db.commit()
    db.refresh(colaborador)
    return colaborador


@router.get("/{colaborador_id}", response_model=ColaboradorOut)
def obter_colaborador(
    colaborador_id: int,
    db: Session = Depends(get_db),
):
    colab = db.query(ColaboradorCampo).get(colaborador_id)
    if not colab:
        raise HTTPException(status_code=404, detail="Colaborador nao encontrado.")
    return colab


@router.put("/{colaborador_id}", response_model=ColaboradorOut)
def atualizar_colaborador(
    colaborador_id: int,
    data: ColaboradorUpdate,
    db: Session = Depends(get_db),
):
    colab = db.query(ColaboradorCampo).get(colaborador_id)
    if not colab:
        raise HTTPException(status_code=404, detail="Colaborador nao encontrado.")

    update_data = data.dict(exclude_unset=True)

    novo_email = update_data.get("email")
    if novo_email and novo_email != colab.email:
        exists = (
            db.query(ColaboradorCampo)
            .filter(ColaboradorCampo.email == novo_email)
            .first()
        )
        if exists:
            raise HTTPException(
                status_code=400,
                detail="Ja existe um colaborador com este e-mail.",
            )

    nova_senha = update_data.pop("senha", None)
    if nova_senha and nova_senha.strip():
        colab.senha_hash = get_password_hash(nova_senha)

    for field, value in update_data.items():
        setattr(colab, field, value)

    db.commit()
    db.refresh(colab)
    return colab


@router.delete("/{colaborador_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_colaborador(
    colaborador_id: int,
    db: Session = Depends(get_db),
):
    colab = db.query(ColaboradorCampo).get(colaborador_id)
    if not colab:
        raise HTTPException(status_code=404, detail="Colaborador nao encontrado.")

    db.delete(colab)
    db.commit()
    return None
