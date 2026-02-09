"""Teste automatizado do sistema (FastAPI).

Objetivo
- Exercitar rotas públicas e protegidas (admin)
- Verificar endpoints de API (colaboradores, registros)
- Gerar um log detalhado com PASS/FAIL

Como rodar
    python teste_sistema.py

Notas
- O script usa um banco SQLite local (arquivo) e NÃO toca no Postgres.
- Credenciais do admin de teste (padrão):
    email: admin@example.com
    senha: Admin@123
- Se quiser, sobrescreva via variáveis de ambiente:
    TEST_ADMIN_EMAIL, TEST_ADMIN_PASSWORD
"""

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path as _Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.session import get_db
from app.core.security import get_password_hash

# Importar modelos para registrar as tabelas no Base.metadata
from app.models import user as _user_model  # noqa: F401
from app.models import colaborador as _colab_model  # noqa: F401
from app.models import registros as _reg_model  # noqa: F401

from app.main import app
from app.models.user import UsuarioSistema
from app.models.colaborador import ColaboradorCampo
from app.models.registros import Registro


ROOT = _Path(__file__).resolve().parent
LOG_PATH = ROOT / "teste_sistema.log"
DB_PATH = ROOT / "teste_sistema.sqlite3"


def setup_logger() -> logging.Logger:
    logger = logging.getLogger("teste_sistema")
    logger.setLevel(logging.INFO)

    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)

    fh = logging.FileHandler(LOG_PATH, encoding="utf-8")
    fh.setFormatter(fmt)

    logger.handlers = []
    logger.addHandler(sh)
    logger.addHandler(fh)
    return logger


def make_sqlite_session():
    if DB_PATH.exists():
        DB_PATH.unlink()

    engine = create_engine(
        f"sqlite:///{DB_PATH}",
        connect_args={"check_same_thread": False},
        future=True,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    return engine, TestingSessionLocal


def override_db(TestingSessionLocal):
    def _get_db_override():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _get_db_override


def seed_admin(db, email: str, password: str) -> UsuarioSistema:
    existing = db.query(UsuarioSistema).filter(UsuarioSistema.email == email).first()
    if existing:
        return existing

    u = UsuarioSistema(
        nome="Admin Teste",
        email=email,
        senha_hash=get_password_hash(password),
        role="ADMIN",
        ativo=True,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


class Result:
    def __init__(self):
        self.ok = 0
        self.fail = 0
        self.skipped = 0


def check(logger: logging.Logger, results: Result, name: str, fn):
    try:
        fn()
        results.ok += 1
        logger.info(f"PASS | {name}")
    except AssertionError as e:
        results.fail += 1
        logger.error(f"FAIL | {name} | {e}")
    except Exception as e:
        results.fail += 1
        logger.exception(f"FAIL | {name} | Exception: {e}")


def main() -> int:
    logger = setup_logger()
    logger.info("=== Iniciando teste_sistema.py ===")

    admin_email = os.getenv("TEST_ADMIN_EMAIL", "admin@example.com")
    admin_password = os.getenv("TEST_ADMIN_PASSWORD", "Admin@123")

    engine, TestingSessionLocal = make_sqlite_session()
    override_db(TestingSessionLocal)

    # Seed
    db = TestingSessionLocal()
    try:
        admin = seed_admin(db, admin_email, admin_password)

        # Seed um registro e um colaborador (para testar /api/registros)
        colab = ColaboradorCampo(
            nome="Colaborador Teste",
            email="colab@example.com",
            telefone="31999999999",
            documento="000.000.000-00",
            senha_hash=get_password_hash("Colab@123"),
            ativo=True,
            criado_por=admin.id,
        )
        db.add(colab)
        db.commit()
        db.refresh(colab)

        reg = Registro(
            projeto="Projeto Demo",
            tipo="FAUNA",
            especie="Canis lupus familiaris",
            identificacao="Registro de teste",
            data_registro=datetime.utcnow(),
            latitude=-19.000001,
            longitude=-43.000001,
            status="PENDENTE",
            colaborador_id=colab.id,
        )
        db.add(reg)
        db.commit()

    finally:
        db.close()

    client = TestClient(app)
    results = Result()

    # Testes públicos
    check(
        logger,
        results,
        "GET / (tela de login)",
        lambda: (
            (lambda r: (assert_status(r, 200), assert_in(r.text, "Login")))(client.get("/"))
        ),
    )

    # Protegidas sem auth
    check(
        logger,
        results,
        "GET /admin/dashboard sem autenticação -> 401",
        lambda: (lambda r: assert_status(r, 401))(client.get("/admin/dashboard")),
    )

    # Login
    def do_login():
        r = client.post("/auth/login", json={"email": admin_email, "senha": admin_password})
        assert_status(r, 200)
        assert "access_token" in client.cookies, "Cookie access_token não foi setado"

    check(logger, results, "POST /auth/login (admin)", do_login)

    colab_token = {"value": None}

    def do_colab_login():
        r = client.post("/auth/colaborador/login", json={"usuario": "colab@example.com", "senha": "Colab@123"})
        assert_status(r, 200)
        data = r.json()
        assert "access_token" in data
        colab_token["value"] = data["access_token"]

    check(logger, results, "POST /auth/colaborador/login", do_colab_login)

    def api_colab_me():
        token = colab_token["value"]
        assert token, "Token do colaborador nao foi gerado"
        r = client.get("/auth/colaborador/me", headers={"Authorization": f"Bearer {token}"})
        assert_status(r, 200)
        assert r.json().get("email") == "colab@example.com"

    check(logger, results, "GET /auth/colaborador/me", api_colab_me)

    # Pages admin
    check(
        logger,
        results,
        "GET /admin/dashboard (autenticado)",
        lambda: (lambda r: (assert_status(r, 200), assert_in(r.text, "Visão")))(client.get("/admin/dashboard")),
    )

    check(
        logger,
        results,
        "GET /admin/colaboradores (autenticado)",
        lambda: (lambda r: (assert_status(r, 200), assert_in(r.text, "Colaboradores")))(client.get("/admin/colaboradores")),
    )

    check(
        logger,
        results,
        "GET /admin/registros (autenticado)",
        lambda: (lambda r: (assert_status(r, 200), assert_in(r.text, "Registros")))(client.get("/admin/registros")),
    )

    # API colaboradores CRUD
    created_id = {"id": None}

    def api_create_colab():
        payload = {
            "nome": "Fulano da Silva",
            "email": "fulano@example.com",
            "telefone": "31988887777",
            "documento": "111.111.111-11",
            "senha": "Fulano@123",
            "ativo": True,
        }
        r = client.post("/api/colaboradores/", json=payload)
        assert_status(r, 201)
        data = r.json()
        created_id["id"] = data["id"]
        assert data["nome"] == payload["nome"]

    check(logger, results, "POST /api/colaboradores/", api_create_colab)

    def api_list_colab():
        r = client.get("/api/colaboradores/")
        assert_status(r, 200)
        assert isinstance(r.json(), list)

    check(logger, results, "GET /api/colaboradores/", api_list_colab)

    def api_get_colab():
        cid = created_id["id"]
        assert cid is not None, "ID do colaborador não foi criado"
        r = client.get(f"/api/colaboradores/{cid}")
        assert_status(r, 200)

    check(logger, results, "GET /api/colaboradores/{id}", api_get_colab)

    def api_update_colab():
        cid = created_id["id"]
        r = client.put(f"/api/colaboradores/{cid}", json={"telefone": "31900001111"})
        assert_status(r, 200)
        assert r.json()["telefone"] == "31900001111"

    check(logger, results, "PUT /api/colaboradores/{id}", api_update_colab)

    def api_delete_colab():
        cid = created_id["id"]
        r = client.delete(f"/api/colaboradores/{cid}")
        assert_status(r, 204)

    check(logger, results, "DELETE /api/colaboradores/{id}", api_delete_colab)

    # API registros
    def api_list_registros():
        r = client.get("/api/registros/")
        assert_status(r, 200)
        data = r.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert "colaborador_nome" in data[0]

    check(logger, results, "GET /api/registros/", api_list_registros)

    # Resumo
    logger.info("=== Resumo ===")
    logger.info(f"PASS: {results.ok}")
    logger.info(f"FAIL: {results.fail}")
    logger.info(f"LOG: {LOG_PATH}")
    logger.info(f"DB (SQLite): {DB_PATH}")

    return 0 if results.fail == 0 else 1


def assert_status(response, expected: int):
    assert response.status_code == expected, (
        f"Esperado status {expected}, veio {response.status_code}. "
        f"Body: {response.text[:200]}"
    )


def assert_in(text: str, needle: str):
    assert needle in text, f"Não encontrei '{needle}' na resposta."


if __name__ == "__main__":
    raise SystemExit(main())
