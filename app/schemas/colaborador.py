from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class ColaboradorBase(BaseModel):
    nome: str
    email: Optional[EmailStr] = None
    telefone: Optional[str] = None
    documento: Optional[str] = None
    ativo: bool = True
    expira_em: Optional[datetime] = None


class ColaboradorCreate(ColaboradorBase):
    senha: str


class ColaboradorUpdate(BaseModel):
    nome: Optional[str] = None
    email: Optional[EmailStr] = None
    telefone: Optional[str] = None
    documento: Optional[str] = None
    ativo: Optional[bool] = None
    senha: Optional[str] = None
    expira_em: Optional[datetime] = None


class ColaboradorOut(ColaboradorBase):
    id: int

    class Config:
        from_attributes = True
