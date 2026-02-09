import sys
from pathlib import Path

from sqlalchemy import inspect, text

# Garante import local do pacote app quando rodado via "python scripts/..."
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db.session import engine


def column_exists(table_name: str, column_name: str) -> bool:
    inspector = inspect(engine)
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns


def main() -> None:
    if not column_exists("colaborador_campo", "senha_hash"):
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE colaborador_campo ADD COLUMN senha_hash VARCHAR"))
        print("OK: coluna senha_hash adicionada em colaborador_campo")
    else:
        print("OK: coluna senha_hash ja existe")


if __name__ == "__main__":
    main()
