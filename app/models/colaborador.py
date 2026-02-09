from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.db.base import Base


class ColaboradorCampo(Base):
    __tablename__ = "colaborador_campo"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    email = Column(String, nullable=True)
    telefone = Column(String, nullable=True)
    documento = Column(String, nullable=True)
    senha_hash = Column(String, nullable=True)
    ativo = Column(Boolean, nullable=False, default=True)
    expira_em = Column(DateTime(timezone=True), nullable=True)

    criado_por = Column(Integer, ForeignKey("usuario_sistema.id"), nullable=True)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())
    atualizado_em = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    criado_por_usuario = relationship("UsuarioSistema", back_populates="colaboradores_criados")

    # Registros coletados em campo vinculados a este colaborador
    registros = relationship("Registro", back_populates="colaborador")
    registros_fauna = relationship("RegistroFauna", back_populates="colaborador")
