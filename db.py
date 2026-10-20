from contextlib import contextmanager

from mysql.connector import pooling

from config import Config

_pool = None


def _obter_pool():
    global _pool
    if _pool is None:
        _pool = pooling.MySQLConnectionPool(
            pool_name="cade_pool",
            pool_size=5,
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            charset="utf8mb4",
        )
    return _pool


@contextmanager
def transacao():
    """Entrega um cursor (linhas como dict) dentro de uma transação.

    Se tudo der certo, faz commit. Se qualquer exceção acontecer (inclusive
    as de regra de negócio, como SemPermissao ou Conflito), faz rollback e
    repassa a exceção para ser tratada em app.py.
    """
    conexao = _obter_pool().get_connection()
    cursor = conexao.cursor(dictionary=True)
    try:
        yield cursor
        conexao.commit()
    except Exception:
        conexao.rollback()
        raise
    finally:
        cursor.close()
        conexao.close()
