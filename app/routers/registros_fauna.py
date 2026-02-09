import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import get_current_colaborador, require_admin
from app.models.colaborador import ColaboradorCampo
from app.models.registro_fauna import RegistroFauna
from app.schemas.registro_fauna import RegistroFaunaIn, RegistroFaunaOut

router = APIRouter(
    prefix="/api/registros-fauna",
    tags=["Registros Fauna"],
)

@router.get("/admin", response_model=list[RegistroFaunaOut], dependencies=[Depends(require_admin)])
def listar_registros_fauna_admin(db: Session = Depends(get_db)):
    registros = (
        db.query(RegistroFauna)
        .outerjoin(ColaboradorCampo, RegistroFauna.colaborador_id == ColaboradorCampo.id)
        .all()
    )

    result: list[dict] = []
    for r in registros:
        data = RegistroFaunaOut.model_validate(r, from_attributes=True).model_dump()
        if getattr(r, "colaborador", None):
            data["colaborador_nome"] = r.colaborador.nome
        result.append(data)

    return result


@router.post("", response_model=RegistroFaunaOut)
@router.post("/", response_model=RegistroFaunaOut)
def criar_ou_atualizar(
    payload: RegistroFaunaIn,
    db: Session = Depends(get_db),
    colaborador: ColaboradorCampo = Depends(get_current_colaborador),
):
    data = payload.model_dump()
    payload_json = data.pop("payload_json", None)
    if payload_json is not None:
        data["payload_json"] = json.dumps(payload_json, ensure_ascii=False)

    existing = (
        db.query(RegistroFauna)
        .filter(
            RegistroFauna.id_dispositivo == payload.id_dispositivo,
            RegistroFauna.colaborador_id == colaborador.id,
        )
        .first()
    )

    if existing:
        for key, value in data.items():
            setattr(existing, key, value)
        existing.colaborador_id = colaborador.id
        existing.status = "SINCRONIZADO"
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing

    novo = RegistroFauna(
        **data,
        colaborador_id=colaborador.id,
        status="SINCRONIZADO",
    )
    db.add(novo)
    db.commit()
    db.refresh(novo)
    return novo
