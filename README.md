<div align="center">
  <h1>Sistema Biodiversidade</h1>
  <p>Plataforma integrada para coleta de dados de biodiversidade em campo e administracao web.</p>

  <p>
    <img src="https://img.shields.io/badge/Backend-FastAPI-0b7285?style=for-the-badge" alt="Backend FastAPI" />
    <img src="https://img.shields.io/badge/Mobile-Flutter-1971c2?style=for-the-badge" alt="Mobile Flutter" />
    <img src="https://img.shields.io/badge/Database-PostgreSQL-2f9e44?style=for-the-badge" alt="Database PostgreSQL" />
  </p>
</div>

---

## Visao geral
Sistema para coleta, gestao e sincronizacao de registros de biodiversidade. Une um **backend FastAPI** com interface web administrativa e um **app Flutter** para colaboradores de campo, mantendo dados consistentes e auditaveis.

## Destaques
- Autenticacao separada para administradores (web) e colaboradores (app)
- Controle de acesso por perfil (ADMIN)
- CRUD completo de colaboradores de campo
- Registros gerais e modulo especifico de fauna
- Captura de GPS, fotos e dados de resgate no app
- Sincronizacao automatica e manual de registros

## Componentes do sistema
| Camada | Local | Funcao |
| --- | --- | --- |
| Backend e Web | `app/` | APIs, templates HTML e regras de negocio |
| App Mobile | `biodiversidade/` | Coleta em campo e sincronizacao |
| Scripts | `scripts/` | Ajustes de schema e manutencao |
| Utilitarios | `create_admin.py`, `teste_sistema.py` | Criacao de admin e testes |

## Arquitetura (fluxo resumido)
1. Admin autentica na web e gerencia colaboradores
2. Colaborador autentica no app e registra dados localmente
3. Registros sao sincronizados para a API quando ha internet
4. Admin visualiza tudo no painel web

## Modulos e modelos principais
- `UsuarioSistema` (admin)
- `ColaboradorCampo` (usuario do app)
- `Registro` (biodiversidade geral)
- `RegistroFauna` (fauna, com GPS, fotos e detalhes)

## Autenticacao e autorizacao
- Admin: `POST /auth/login` (cookie `access_token`)
- Colaborador: `POST /auth/colaborador/login` (token bearer)
- Rotas administrativas exigem `role = ADMIN`

## Rotas web (HTML)
- `GET /` pagina de login
- `GET /admin/dashboard` painel principal
- `GET /admin/colaboradores` gestao de colaboradores
- `GET /admin/registros` registros agregados
- `GET /admin/registros-fauna` registros de fauna
- `GET /admin/configuracoes` configuracoes do sistema

## API (JSON)
### Autenticacao
- `POST /auth/login`
- `POST /auth/logout`
- `GET /auth/me`
- `POST /auth/colaborador/login`
- `GET /auth/colaborador/me`

### Colaboradores
- `GET /api/colaboradores`
- `POST /api/colaboradores`
- `GET /api/colaboradores/{id}`
- `PUT /api/colaboradores/{id}`
- `DELETE /api/colaboradores/{id}`

### Registros
- `GET /api/registros` (unifica `Registro` + `RegistroFauna`)
- `GET /api/registros-fauna/admin`
- `POST /api/registros-fauna` (create/update por `id_dispositivo`)

## App mobile (Flutter)
- Login de colaborador e sessao local
- Menus para Biodiversidade, Fauna e Flora
- Armazenamento local em SQLite (`biodiversidade.db`)
- Sincronizacao automatica a cada 5 minutos
- Sincronizacao manual por registro
- Tela de historico com status Enviado/Pendente

## Configuracao essencial
- `DATABASE_URL` (conexao com o banco)
- `SECRET_KEY` e `ACCESS_TOKEN_EXPIRE_MINUTES` em `app/core/security.py`
- `apiBaseUrl` no app: `biodiversidade/lib/services/api_config.dart`

## Como executar (backend)
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Como executar (app)
```bash
cd biodiversidade
flutter pub get
flutter run
```

## Criacao de admin
```bash
python create_admin.py
```

## Manutencao e scripts
- `scripts/ensure_colaborador_senha_hash.py`
- `scripts/ensure_registros_table.py`

## Teste automatizado
```bash
python teste_sistema.py
```

---

### Estrutura do repositorio
```
APP_Bio/
  app/
  biodiversidade/
  scripts/
  create_admin.py
  teste_sistema.py
```
