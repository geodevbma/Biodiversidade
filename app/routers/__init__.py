"""Pacote de rotas (routers) do FastAPI."""

# Mantém imports explícitos para facilitar o auto-complete e evitar problemas
# com namespace packages em alguns ambientes.

from . import auth, colaboradores, registros, registros_fauna  # noqa: F401
