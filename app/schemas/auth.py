from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.schemas.colaborador import ColaboradorOut


class LoginInput(BaseModel):
    email: EmailStr
    senha: str


class UsuarioSistemaOut(BaseModel):
    id: int
    nome: str
    email: EmailStr
    role: str

    class Config:
        from_attributes = True  # Pydantic v2


class ColaboradorLoginInput(BaseModel):
    usuario: str
    email: EmailStr | None = None
    senha: str


class ColaboradorLoginOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    expires_in: int
    colaborador: ColaboradorOut
