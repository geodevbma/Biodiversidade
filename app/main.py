from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.routers import auth, colaboradores, registros, registros_fauna  # e outros routers que você tiver
from app.deps import get_current_user_optional, get_current_user, require_admin
from app.models.user import UsuarioSistema
from app.db.session import get_db
from app.db.init_db import init_db



app = FastAPI(title="Sistema Biodiversidade - Web")

templates = Jinja2Templates(directory="app/templates")

media_dir = Path(__file__).resolve().parent / "media"
media_dir.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(media_dir)), name="media")

app.include_router(auth.router)
app.include_router(colaboradores.router)
app.include_router(registros.router)
app.include_router(registros_fauna.router)


@app.on_event("startup")
def on_startup() -> None:
    init_db()

@app.get("/", response_class=HTMLResponse)
def root(
    request: Request,
    current_user: UsuarioSistema | None = Depends(get_current_user_optional),
):
    if current_user is not None:
        return RedirectResponse(url="/admin/dashboard", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/admin/dashboard",
         response_class=HTMLResponse,
         dependencies=[Depends(require_admin)])
def pagina_dashboard(
    request: Request,
    current_user: UsuarioSistema = Depends(get_current_user),
):
    # se quiser passar lista de projetos para o filtro:
    projetos = []  # depois você popula a partir do BD
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": current_user,
            "active_menu": "dashboard",
            "projetos": projetos,
        },
    )



@app.get("/admin/colaboradores", response_class=HTMLResponse, dependencies=[Depends(require_admin)])
def pagina_colaboradores(request: Request, current_user: UsuarioSistema = Depends(get_current_user)):
    return templates.TemplateResponse(
        "colaboradores.html",
        {"request": request, "user": current_user, "active_menu": "colaboradores"},
    )


@app.get("/admin/registros", response_class=HTMLResponse, dependencies=[Depends(require_admin)])
def pagina_registros(
    request: Request,
    current_user: UsuarioSistema = Depends(get_current_user),
    db=Depends(get_db),
):
    """Página administrativa de visualização dos registros coletados."""
    # Lista de projetos para o filtro (gera a partir do banco)
    try:
        from sqlalchemy import distinct
        from app.models.registros import Registro

        projetos = [
            p[0]
            for p in db.query(distinct(Registro.projeto)).order_by(Registro.projeto).all()
            if p and p[0]
        ]
    except Exception:
        projetos = []

    return templates.TemplateResponse(
        "registros.html",
        {
            "request": request,
            "user": current_user,
            "active_menu": "registros",
            "projetos": projetos,
        },
    )


@app.get("/admin/registros-fauna", response_class=HTMLResponse, dependencies=[Depends(require_admin)])
def pagina_registros_fauna(
    request: Request,
    current_user: UsuarioSistema = Depends(get_current_user),
    db=Depends(get_db),
):
    try:
        from sqlalchemy import distinct
        from app.models.registro_fauna import RegistroFauna

        municipios = [
            m[0]
            for m in db.query(distinct(RegistroFauna.municipio))
            .order_by(RegistroFauna.municipio)
            .all()
            if m and m[0]
        ]
    except Exception:
        municipios = []

    return templates.TemplateResponse(
        "registros_fauna.html",
        {
            "request": request,
            "user": current_user,
            "active_menu": "registros_fauna",
            "municipios": municipios,
        },
    )


@app.get("/admin/configuracoes", response_class=HTMLResponse, dependencies=[Depends(require_admin)])
def pagina_configuracoes(
    request: Request,
    current_user: UsuarioSistema = Depends(get_current_user),
):
    return templates.TemplateResponse(
        "configuracoes.html",
        {
            "request": request,
            "user": current_user,
            "active_menu": "configuracoes",
        },
    )

#
