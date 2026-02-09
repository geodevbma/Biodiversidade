from datetime import datetime
from pydantic import BaseModel


class RegistroFaunaIn(BaseModel):
    id_dispositivo: str
    animal_number: str | None = None
    nome_cientifico: str | None = None
    data_captura: datetime | None = None
    biologo_responsavel: str | None = None
    gps_manual: bool | None = None
    latitude: float | None = None
    longitude: float | None = None
    gps_accuracy: float | None = None
    gps_timestamp: datetime | None = None
    manual_latitude: str | None = None
    manual_longitude: str | None = None
    municipio: str | None = None
    local_captura: str | None = None
    periodo_resgate: str | None = None
    estado_saude: str | None = None
    destino: str | None = None
    observacoes: str | None = None
    foto_animal_path: str | None = None
    foto_local_path: str | None = None
    assinatura_usuario: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    payload_json: dict | None = None


class RegistroFaunaOut(BaseModel):
    id: int
    id_dispositivo: str
    colaborador_id: int
    status: str | None = None

    animal_number: str | None = None
    nome_cientifico: str | None = None
    data_captura: datetime | None = None
    biologo_responsavel: str | None = None

    gps_manual: bool | None = None
    latitude: float | None = None
    longitude: float | None = None
    gps_accuracy: float | None = None
    gps_timestamp: datetime | None = None
    manual_latitude: str | None = None
    manual_longitude: str | None = None

    municipio: str | None = None
    local_captura: str | None = None
    periodo_resgate: str | None = None
    estado_saude: str | None = None
    destino: str | None = None
    observacoes: str | None = None
    foto_animal_path: str | None = None
    foto_local_path: str | None = None
    assinatura_usuario: str | None = None

    created_at: datetime | None = None
    updated_at: datetime | None = None
    colaborador_nome: str | None = None

    class Config:
        from_attributes = True
