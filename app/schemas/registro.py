from datetime import datetime
from pydantic import BaseModel

class RegistroOut(BaseModel):
    id: int
    projeto: str | None = None
    tipo: str | None = None
    especie: str | None = None
    identificacao: str | None = None
    data_registro: datetime | None = None
    latitude: float | None = None
    longitude: float | None = None
    status: str | None = None
    colaborador_nome: str | None = None
    foto_animal_path: str | None = None
    foto_local_path: str | None = None
    assinatura_usuario: str | None = None

    class Config:
        from_attributes = True  # Pydantic v2
