from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class RegistroFauna(Base):
    __tablename__ = "registros_fauna"

    id = Column(Integer, primary_key=True, index=True)
    id_dispositivo = Column(String, index=True, nullable=False)

    colaborador_id = Column(Integer, ForeignKey("colaborador_campo.id"), nullable=False)
    colaborador = relationship("ColaboradorCampo", back_populates="registros_fauna")

    criado_em = Column(DateTime(timezone=True), server_default=func.now())
    atualizado_em = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    created_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)
    data_captura = Column(DateTime(timezone=True), nullable=True)

    animal_number = Column(String, nullable=True)
    nome_cientifico = Column(String, nullable=True)
    biologo_responsavel = Column(String, nullable=True)

    gps_manual = Column(Boolean, default=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    gps_accuracy = Column(Float, nullable=True)
    gps_timestamp = Column(DateTime(timezone=True), nullable=True)
    manual_latitude = Column(String, nullable=True)
    manual_longitude = Column(String, nullable=True)

    municipio = Column(String, nullable=True)
    local_captura = Column(String, nullable=True)
    periodo_resgate = Column(String, nullable=True)
    estado_saude = Column(String, nullable=True)
    destino = Column(String, nullable=True)
    observacoes = Column(String, nullable=True)

    foto_animal_path = Column(String, nullable=True)
    foto_local_path = Column(String, nullable=True)
    assinatura_usuario = Column(String, nullable=True)

    payload_json = Column(String, nullable=True)

    status = Column(String, default="SINCRONIZADO")
