from datetime import datetime, timedelta, timezone
from functools import wraps

import bcrypt
import jwt
from flask import g, request

from config import Config
from db import transacao
from exceptions import NaoAutenticado, SemPermissao

ALGORITMO = "HS256"


# ---------------------------------------------------------------- senhas
def gerar_hash(senha: str) -> str:
    return bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verificar_senha(senha: str, senha_hash: str) -> bool:
    try:
        return bcrypt.checkpw(senha.encode("utf-8"), senha_hash.encode("utf-8"))
    except ValueError:
        return False


# ---------------------------------------------------------------- tokens
def gerar_token(usuario: dict) -> str:
    agora = datetime.now(timezone.utc)
    payload = {
        "sub": str(usuario["id"]),
        "papel": usuario["papel"],
        "iat": agora,
        "exp": agora + timedelta(minutes=Config.JWT_EXPIRA_MINUTOS),
    }
    return jwt.encode(payload, Config.JWT_SECRET, algorithm=ALGORITMO)


# ---------------------------------------------------------------- decoradores
def token_obrigatorio(f):
    """Exige um token válido. Coloca o usuário (lido do banco) em g.usuario.

    O papel é lido do banco a cada requisição, e não só do token, para que
    uma mudança de papel passe a valer imediatamente.
    """

    @wraps(f)
    def wrapper(*args, **kwargs):
        partes = request.headers.get("Authorization", "").split()
        if len(partes) != 2 or partes[0].lower() != "bearer":
            raise NaoAutenticado(
                "Token ausente ou mal formatado. Use: Authorization: Bearer <token>"
            )

        try:
            payload = jwt.decode(partes[1], Config.JWT_SECRET, algorithms=[ALGORITMO])
            usuario_id = int(payload["sub"])
        except jwt.ExpiredSignatureError:
            raise NaoAutenticado("Token expirado. Faça login novamente.")
        except (jwt.InvalidTokenError, KeyError, ValueError):
            raise NaoAutenticado("Token inválido.")

        with transacao() as cur:
            cur.execute(
                "SELECT id, nome, email, papel FROM usuarios WHERE id = %s",
                (usuario_id,),
            )
            usuario = cur.fetchone()

        if usuario is None:
            raise NaoAutenticado("Usuário do token não existe mais.")

        g.usuario = usuario
        return f(*args, **kwargs)

    return wrapper


def papel_exigido(*papeis):
    """Exige login E que o papel do usuário esteja entre `papeis`.

    Sem token válido -> 401. Com token, mas papel errado -> 403.
    """

    def decorador(f):
        @wraps(f)
        @token_obrigatorio
        def wrapper(*args, **kwargs):
            if g.usuario["papel"] not in papeis:
                raise SemPermissao(
                    "Esta ação exige o papel: " + " ou ".join(papeis) + "."
                )
            return f(*args, **kwargs)

        return wrapper

    return decorador
