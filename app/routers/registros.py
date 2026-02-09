from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.registros import Registro
from app.models.registro_fauna import RegistroFauna
from app.models.colaborador import ColaboradorCampo
from app.schemas.registro import RegistroOut
from app.deps import require_admin

router = APIRouter(
    prefix="/api/registros",
    tags=["Registros"],
    dependencies=[Depends(require_admin)],
)

@router.get("/", response_model=list[RegistroOut])
def listar_registros(db: Session = Depends(get_db)):
    # Aqui você pode depois aplicar filtros (data, projeto, etc.) via query params
    registros = (
        db.query(Registro)
        .outerjoin(ColaboradorCampo, Registro.colaborador_id == ColaboradorCampo.id)
        .all()
    )

    fauna = (
        db.query(RegistroFauna)
        .outerjoin(ColaboradorCampo, RegistroFauna.colaborador_id == ColaboradorCampo.id)
        .all()
    )

    # Se quiser já “injetar” colaborador_nome:
    result: list[dict] = []
    for r in registros:
        data = RegistroOut.model_validate(r, from_attributes=True).model_dump()
        if getattr(r, "colaborador", None):
            data["colaborador_nome"] = r.colaborador.nome
        result.append(data)

    for f in fauna:
        data = RegistroOut(
            id=f.id,
            projeto="Fauna",
            tipo="fauna",
            especie=f.nome_cientifico,
            identificacao=f.animal_number,
            data_registro=f.data_captura or f.created_at,
            latitude=f.latitude,
            longitude=f.longitude,
            status=f.status,
            colaborador_nome=f.colaborador.nome if getattr(f, "colaborador", None) else None,
        ).model_dump()
        result.append(data)

    result.sort(
        key=lambda item: item.get("data_registro") or "",
        reverse=True,
    )

    return result
