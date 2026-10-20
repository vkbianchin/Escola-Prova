"""Cria usuários e equipamentos de teste.

Uso (depois de rodar database/schema.sql e configurar o .env):
    python seed.py

Pode rodar mais de uma vez: só insere o que ainda não existe.
"""

from auth import gerar_hash
from db import transacao

USUARIOS = [
    ("Administrador", "admin@senac.com", "Admin@123", "admin"),
    ("Gestor do Almoxarifado", "gestor@senac.com", "Gestor@123", "gestor"),
    ("Usuário Comum", "comum@senac.com", "Comum@123", "comum"),
]

EQUIPAMENTOS = [
    ("Notebook Dell Latitude", "PAT-0001", "Notebook para uso em sala"),
    ("Projetor Epson", "PAT-0002", "Projetor com cabo HDMI"),
    ("Kit Arduino Uno", "PAT-0003", "Placa, protoboard e jumpers"),
]


def main():
    with transacao() as cur:
        for nome, email, senha, papel in USUARIOS:
            cur.execute("SELECT id FROM usuarios WHERE email = %s", (email,))
            if cur.fetchone():
                print(f"= {email} já existe")
                continue
            cur.execute(
                "INSERT INTO usuarios (nome, email, senha_hash, papel) "
                "VALUES (%s, %s, %s, %s)",
                (nome, email, gerar_hash(senha), papel),
            )
            print(f"+ {email} ({papel}) criado")

        cur.execute("SELECT id FROM usuarios WHERE email = %s", ("admin@senac.com",))
        admin_id = cur.fetchone()["id"]

        for nome, patrimonio, descricao in EQUIPAMENTOS:
            cur.execute(
                "SELECT id FROM equipamentos WHERE codigo_patrimonio = %s", (patrimonio,)
            )
            if cur.fetchone():
                print(f"= {patrimonio} já existe")
                continue
            cur.execute(
                "INSERT INTO equipamentos (nome, codigo_patrimonio, descricao, cadastrado_por) "
                "VALUES (%s, %s, %s, %s)",
                (nome, patrimonio, descricao, admin_id),
            )
            print(f"+ {patrimonio} ({nome}) criado")


if __name__ == "__main__":
    main()
