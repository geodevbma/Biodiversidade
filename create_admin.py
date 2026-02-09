import getpass

from app.db.session import SessionLocal
from app.models.user import UsuarioSistema
from app.core.security import get_password_hash


def main():
    db = SessionLocal()
    try:
        print("=== Criar usuário administrador do sistema web ===")
        email = input("E-mail: ").strip()
        nome = input("Nome completo: ").strip()
        senha = getpass.getpass("Senha: ")
        senha2 = getpass.getpass("Confirme a senha: ")

        if senha != senha2:
            print("As senhas não conferem.")
            return

        # Verificar se já existe
        existing = db.query(UsuarioSistema).filter(UsuarioSistema.email == email).first()
        if existing:
            print("Já existe um usuário com este e-mail.")
            return

        user = UsuarioSistema(
            nome=nome,
            email=email,
            senha_hash=get_password_hash(senha),
            role="ADMIN",
            ativo=True,
        )
        db.add(user)
        db.commit()
        print(f"Usuário admin criado com sucesso. ID = {user.id}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
