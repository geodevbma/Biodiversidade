from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship

from app.db.base import Base

class Registro(Base):
    __tablename__ = "registros"

    id = Column(Integer, primary_key=True, index=True)
    projeto = Column(String, index=True)
    tipo = Column(String, index=True)
    especie = Column(String)
    identificacao = Column(String)
    data_registro = Column(DateTime, index=True)
    latitude = Column(Float)
    longitude = Column(Float)
    status = Column(String, default="PENDENTE")

    # Colaborador de campo (tabela: colaborador_campo)
    colaborador_id = Column(Integer, ForeignKey("colaborador_campo.id"), nullable=True)
    colaborador = relationship("ColaboradorCampo", back_populates="registros")
