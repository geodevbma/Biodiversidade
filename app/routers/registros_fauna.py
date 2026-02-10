import json
import shutil
import uuid
from datetime import datetime
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from fastapi import APIRouter, Depends, UploadFile, File, Form, Request, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.orm import Session, joinedload

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

EXPORT_COLUNAS = [
    ("ID", "id"),
    ("ID Dispositivo", "id_dispositivo"),
    ("Animal", "animal_number"),
    ("Nome cientifico", "nome_cientifico"),
    ("Data captura", "data_captura"),
    ("Biologo responsavel", "biologo_responsavel"),
    ("Municipio", "municipio"),
    ("Local captura", "local_captura"),
    ("Periodo resgate", "periodo_resgate"),
    ("Estado saude", "estado_saude"),
    ("Destino", "destino"),
    ("Observacoes", "observacoes"),
    ("Latitude", "latitude"),
    ("Longitude", "longitude"),
    ("Status", "status"),
    ("Colaborador", "colaborador_nome"),
]


def _parse_ids_param(ids_raw: str | None) -> list[int] | None:
    if ids_raw is None:
        return None

    cleaned = ids_raw.strip()
    if not cleaned:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Parametro ids vazio.",
        )

    parsed: list[int] = []
    for token in cleaned.split(","):
        token = token.strip()
        if not token:
            continue
        if not token.isdigit():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"ID invalido: {token}",
            )
        parsed.append(int(token))

    if not parsed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Informe ao menos um ID valido.",
        )

    return sorted(set(parsed))


def _format_value(value) -> str:
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "Sim" if value else "Nao"
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y %H:%M:%S")
    if isinstance(value, float):
        return f"{value:.6f}"
    text = str(value).strip()
    return text or "-"


def _registro_to_export_dict(registro: RegistroFauna) -> dict[str, str]:
    return {
        "id": _format_value(registro.id),
        "id_dispositivo": _format_value(registro.id_dispositivo),
        "animal_number": _format_value(registro.animal_number),
        "nome_cientifico": _format_value(registro.nome_cientifico),
        "data_captura": _format_value(registro.data_captura),
        "biologo_responsavel": _format_value(registro.biologo_responsavel),
        "municipio": _format_value(registro.municipio),
        "local_captura": _format_value(registro.local_captura),
        "periodo_resgate": _format_value(registro.periodo_resgate),
        "estado_saude": _format_value(registro.estado_saude),
        "destino": _format_value(registro.destino),
        "observacoes": _format_value(registro.observacoes),
        "latitude": _format_value(registro.latitude),
        "longitude": _format_value(registro.longitude),
        "status": _format_value(registro.status),
        "colaborador_nome": _format_value(
            registro.colaborador.nome if getattr(registro, "colaborador", None) else None
        ),
    }


def _buscar_registros_para_exportacao(db: Session, ids: list[int] | None) -> list[RegistroFauna]:
    query = db.query(RegistroFauna).options(joinedload(RegistroFauna.colaborador))
    if ids:
        query = query.filter(RegistroFauna.id.in_(ids))
    registros = query.order_by(RegistroFauna.id.desc()).all()

    if not registros:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhum registro encontrado para exportacao.",
        )

    return registros


def _gerar_nome_arquivo(base: str, ext: str, ids: list[int] | None) -> str:
    sufixo = "selecionados" if ids else "todos"
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{base}_{sufixo}_{stamp}.{ext}"


def _gerar_excel_registros(registros: list[RegistroFauna]) -> BytesIO:
    wb = Workbook()
    ws = wb.active
    ws.title = "Registros Fauna"

    headers = [coluna[0] for coluna in EXPORT_COLUNAS]
    ws.append(headers)

    for r in registros:
        export_data = _registro_to_export_dict(r)
        ws.append([export_data.get(coluna[1], "-") for coluna in EXPORT_COLUNAS])

    ws.freeze_panes = "A2"

    for idx, header in enumerate(headers, start=1):
        col_letter = ws.cell(row=1, column=idx).column_letter
        largura_base = max(len(header) + 2, 14)
        ws.column_dimensions[col_letter].width = min(largura_base + 8, 52)

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output


def _gerar_pdf_registros(registros: list[RegistroFauna]) -> BytesIO:
    output = BytesIO()
    doc = SimpleDocTemplate(
        output,
        pagesize=A4,
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title="Registros de Fauna",
    )

    styles = getSampleStyleSheet()
    body_style = styles["BodyText"]
    story = []

    for idx, r in enumerate(registros):
        export_data = _registro_to_export_dict(r)
        story.append(Paragraph(f"<b>Registro de Fauna #{escape(export_data['id'])}</b>", styles["Heading3"]))
        story.append(
            Paragraph(
                f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
                body_style,
            )
        )
        story.append(Spacer(1, 6))

        table_data = [[Paragraph("<b>Campo</b>", body_style), Paragraph("<b>Valor</b>", body_style)]]
        for titulo, key in EXPORT_COLUNAS:
            valor = escape(export_data.get(key, "-"))
            table_data.append([Paragraph(escape(titulo), body_style), Paragraph(valor, body_style)])

        table = Table(table_data, colWidths=[52 * mm, 124 * mm], repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E2E8F0")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E1")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        story.append(table)

        if idx < len(registros) - 1:
            story.append(PageBreak())

    doc.build(story)
    output.seek(0)
    return output


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


@router.get("/admin/export/pdf", dependencies=[Depends(require_admin)])
def exportar_registros_fauna_pdf(
    ids: str | None = Query(default=None, description="Lista de IDs separados por virgula."),
    db: Session = Depends(get_db),
):
    ids_parsed = _parse_ids_param(ids)
    registros = _buscar_registros_para_exportacao(db, ids_parsed)
    pdf_bytes = _gerar_pdf_registros(registros)
    file_name = _gerar_nome_arquivo("registros_fauna", "pdf", ids_parsed)

    return StreamingResponse(
        pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )


@router.get("/admin/export/excel", dependencies=[Depends(require_admin)])
def exportar_registros_fauna_excel(
    ids: str | None = Query(default=None, description="Lista de IDs separados por virgula."),
    db: Session = Depends(get_db),
):
    ids_parsed = _parse_ids_param(ids)
    registros = _buscar_registros_para_exportacao(db, ids_parsed)
    excel_bytes = _gerar_excel_registros(registros)
    file_name = _gerar_nome_arquivo("registros_fauna", "xlsx", ids_parsed)

    return StreamingResponse(
        excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )


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
