import sys
from pathlib import Path

from sqlalchemy import inspect

# Garante import local do pacote app quando rodado via "python scripts/..."
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db.session import engine
from app.db.base import Base
from app.models.registros import Registro


def table_exists(table_name: str) -> bool:
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()


def main() -> None:
    if table_exists("registros"):
        print("OK: tabela registros ja existe")
        return

    Base.metadata.create_all(bind=engine, tables=[Registro.__table__])
    print("OK: tabela registros criada")


if __name__ == "__main__":
    main()
