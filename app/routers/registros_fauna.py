import json
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile, File, Form, Request, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import get_current_colaborador, require_admin
from app.models.colaborador import ColaboradorCampo
from app.models.registro_fauna import RegistroFauna
from app.schemas.registro_fauna import (
    RegistroFaunaIn,
    RegistroFaunaOut,
    RegistroFaunaUpdate,
)

router = APIRouter(
    prefix="/api/registros-fauna",
    tags=["Registros Fauna"],
)

MEDIA_ROOT = Path(__file__).resolve().parents[1] / "media"
FAUNA_ROOT = MEDIA_ROOT / "fauna"

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


@router.put("/admin/{registro_id}", response_model=RegistroFaunaOut, dependencies=[Depends(require_admin)])
def atualizar_registro_fauna_admin(
    registro_id: int,
    data: RegistroFaunaUpdate,
    db: Session = Depends(get_db),
):
    registro = db.query(RegistroFauna).get(registro_id)
    if not registro:
        raise HTTPException(status_code=404, detail="Registro nao encontrado.")

    update_data = data.dict(exclude_unset=True)
    payload_json = update_data.pop("payload_json", None)
    if payload_json is not None:
        update_data["payload_json"] = json.dumps(payload_json, ensure_ascii=False)

    for field, value in update_data.items():
        setattr(registro, field, value)

    db.commit()
    db.refresh(registro)

    result = RegistroFaunaOut.model_validate(registro, from_attributes=True).model_dump()
    if getattr(registro, "colaborador", None):
        result["colaborador_nome"] = registro.colaborador.nome
    return result


@router.delete("/admin/{registro_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_admin)])
def excluir_registro_fauna_admin(
    registro_id: int,
    db: Session = Depends(get_db),
):
    registro = db.query(RegistroFauna).get(registro_id)
    if not registro:
        raise HTTPException(status_code=404, detail="Registro nao encontrado.")

    db.delete(registro)
    db.commit()
    return None


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


def _save_upload(file: UploadFile, dest_dir: Path, prefix: str) -> Path:
    suffix = Path(file.filename or "").suffix or ".jpg"
    filename = f"{prefix}_{uuid.uuid4().hex}{suffix}"
    dest = dest_dir / filename
    with dest.open("wb") as target:
        shutil.copyfileobj(file.file, target)
    return dest


@router.post("/upload")
def upload_fotos(
    request: Request,
    id_dispositivo: str = Form(...),
    foto_animal: UploadFile | None = File(default=None),
    foto_local: UploadFile | None = File(default=None),
    colaborador: ColaboradorCampo = Depends(get_current_colaborador),
):
    if foto_animal is None and foto_local is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Envie pelo menos um arquivo.",
        )

    target_dir = FAUNA_ROOT / str(colaborador.id) / id_dispositivo
    target_dir.mkdir(parents=True, exist_ok=True)

    result: dict[str, str | None] = {
        "foto_animal_url": None,
        "foto_local_url": None,
    }

    base_url = str(request.base_url).rstrip("/")

    if foto_animal is not None:
        saved = _save_upload(foto_animal, target_dir, "animal")
        rel = saved.relative_to(MEDIA_ROOT).as_posix()
        result["foto_animal_url"] = f"{base_url}/media/{rel}"

    if foto_local is not None:
        saved = _save_upload(foto_local, target_dir, "local")
        rel = saved.relative_to(MEDIA_ROOT).as_posix()
        result["foto_local_url"] = f"{base_url}/media/{rel}"

    return result
