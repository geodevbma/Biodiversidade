from fastapi import APIRouter, Depends
from app.deps import get_current_user
from app.models.user import UsuarioSistema

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/dashboard")
def dashboard(current_user: UsuarioSistema = Depends(get_current_user)):
    # Aqui depois você devolve HTML ou JSON, conforme for integrar com frontend
    return {
        "msg": f"Bem-vindo, {current_user.nome}!",
        "email": current_user.email,
        "role": current_user.role,
    }
