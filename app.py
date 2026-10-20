from datetime import datetime

import mysql.connector
from flask import Flask, g, jsonify, render_template, request
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

from auth import gerar_token, papel_exigido, token_obrigatorio, verificar_senha
from config import Config
from db import transacao
from exceptions import AppError, Conflito, DadosInvalidos, NaoAutenticado, NaoEncontrado

app = Flask(__name__)
CORS(app, origins=Config.CORS_ORIGENS)


# ------------------------------------------------------------------ utilitários
def serializar(obj):
    """Converte datetime em texto ISO para o JSON."""
    if isinstance(obj, list):
        return [serializar(o) for o in obj]
    if isinstance(obj, dict):
        return {k: serializar(v) for k, v in obj.items()}
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj


def resposta(dados, status=200):
    return jsonify(serializar(dados)), status


def corpo_json():
    dados = request.get_json(silent=True)
    if not isinstance(dados, dict):
        raise DadosInvalidos("O corpo da requisição deve ser um JSON válido.")
    return dados


def texto_obrigatorio(dados, campo, rotulo):
    valor = str(dados.get(campo) or "").strip()
    if not valor:
        raise DadosInvalidos(f"O campo '{rotulo}' é obrigatório.")
    return valor


SQL_EMPRESTIMO = """
    SELECT e.id, e.status, e.data_solicitacao, e.data_decisao,
           e.data_devolucao, e.observacao,
           q.id AS equipamento_id, q.nome AS equipamento_nome,
           q.codigo_patrimonio,
           u.id AS usuario_id, u.nome AS usuario_nome
      FROM emprestimos e
      JOIN equipamentos q ON q.id = e.equipamento_id
      JOIN usuarios u ON u.id = e.usuario_id
"""


def buscar_emprestimo(cur, emprestimo_id):
    cur.execute(SQL_EMPRESTIMO + " WHERE e.id = %s", (emprestimo_id,))
    return cur.fetchone()


# ------------------------------------------------------------------ páginas (templates/)
# As páginas são públicas: quem protege os dados é a API (token + papel).
@app.get("/")
def pagina_login():
    return render_template("index.html")


@app.get("/painel")
def pagina_painel():
    return render_template("painel.html")


# ------------------------------------------------------------------ autenticação
@app.post("/auth/login")
def login():
    dados = corpo_json()
    email = str(dados.get("email") or "").strip().lower()
    senha = str(dados.get("senha") or "")
    if not email or not senha:
        raise DadosInvalidos("Informe e-mail e senha.")

    with transacao() as cur:
        cur.execute(
            "SELECT id, nome, email, senha_hash, papel FROM usuarios WHERE email = %s",
            (email,),
        )
        usuario = cur.fetchone()

    # Mesma mensagem para e-mail inexistente e senha errada (não revela qual falhou).
    if usuario is None or not verificar_senha(senha, usuario["senha_hash"]):
        raise NaoAutenticado("E-mail ou senha inválidos.")

    return resposta(
        {
            "token": gerar_token(usuario),
            "usuario": {
                "id": usuario["id"],
                "nome": usuario["nome"],
                "email": usuario["email"],
                "papel": usuario["papel"],
            },
        }
    )


@app.get("/auth/me")
@token_obrigatorio
def me():
    return resposta(g.usuario)


# ------------------------------------------------------------------ equipamentos
@app.get("/equipamentos")
@token_obrigatorio
def listar_equipamentos():
    with transacao() as cur:
        cur.execute(
            "SELECT id, nome, codigo_patrimonio, descricao, status "
            "FROM equipamentos ORDER BY nome"
        )
        return resposta(cur.fetchall())


@app.post("/equipamentos")
@papel_exigido("admin")
def cadastrar_equipamento():
    dados = corpo_json()
    nome = texto_obrigatorio(dados, "nome", "nome")
    patrimonio = texto_obrigatorio(dados, "codigo_patrimonio", "código de patrimônio")
    descricao = str(dados.get("descricao") or "").strip() or None

    with transacao() as cur:
        cur.execute(
            "INSERT INTO equipamentos (nome, codigo_patrimonio, descricao, cadastrado_por) "
            "VALUES (%s, %s, %s, %s)",
            (nome, patrimonio, descricao, g.usuario["id"]),
        )
        novo_id = cur.lastrowid
        cur.execute(
            "SELECT id, nome, codigo_patrimonio, descricao, status "
            "FROM equipamentos WHERE id = %s",
            (novo_id,),
        )
        return resposta(cur.fetchone(), 201)


# ------------------------------------------------------------------ empréstimos
@app.get("/emprestimos")
@token_obrigatorio
def listar_emprestimos():
    """Usuário comum vê só os seus. Gestor e admin veem todos.

    Filtro opcional: /emprestimos?status=solicitado
    """
    sql = SQL_EMPRESTIMO
    filtros, params = [], []

    if g.usuario["papel"] == "comum":
        filtros.append("e.usuario_id = %s")
        params.append(g.usuario["id"])

    status = request.args.get("status")
    if status:
        if status not in ("solicitado", "aprovado", "recusado", "devolvido"):
            raise DadosInvalidos("Status inválido para o filtro.")
        filtros.append("e.status = %s")
        params.append(status)

    if filtros:
        sql += " WHERE " + " AND ".join(filtros)
    sql += " ORDER BY e.id DESC"

    with transacao() as cur:
        cur.execute(sql, params)
        return resposta(cur.fetchall())


@app.post("/emprestimos")
@papel_exigido("comum")
def solicitar_emprestimo():
    dados = corpo_json()
    try:
        equipamento_id = int(dados.get("equipamento_id"))
    except (TypeError, ValueError):
        raise DadosInvalidos("Informe um 'equipamento_id' numérico.")

    with transacao() as cur:
        cur.execute(
            "SELECT id, status FROM equipamentos WHERE id = %s FOR UPDATE",
            (equipamento_id,),
        )
        equipamento = cur.fetchone()
        if equipamento is None:
            raise NaoEncontrado("Equipamento não encontrado.")
        if equipamento["status"] != "disponivel":
            raise Conflito("Este equipamento não está disponível para empréstimo.")

        cur.execute(
            "SELECT id FROM emprestimos WHERE usuario_id = %s AND equipamento_id = %s "
            "AND status IN ('solicitado', 'aprovado')",
            (g.usuario["id"], equipamento_id),
        )
        if cur.fetchone():
            raise Conflito("Você já tem um pedido em aberto para este equipamento.")

        cur.execute(
            "INSERT INTO emprestimos (usuario_id, equipamento_id) VALUES (%s, %s)",
            (g.usuario["id"], equipamento_id),
        )
        return resposta(buscar_emprestimo(cur, cur.lastrowid), 201)


def _emprestimo_bloqueado(cur, emprestimo_id):
    cur.execute(
        "SELECT id, equipamento_id, status FROM emprestimos WHERE id = %s FOR UPDATE",
        (emprestimo_id,),
    )
    emprestimo = cur.fetchone()
    if emprestimo is None:
        raise NaoEncontrado("Empréstimo não encontrado.")
    return emprestimo


@app.patch("/emprestimos/<int:emprestimo_id>/aprovar")
@papel_exigido("gestor")
def aprovar_emprestimo(emprestimo_id):
    with transacao() as cur:
        emprestimo = _emprestimo_bloqueado(cur, emprestimo_id)
        if emprestimo["status"] != "solicitado":
            raise Conflito("Só é possível aprovar um empréstimo com status 'solicitado'.")

        cur.execute(
            "SELECT status FROM equipamentos WHERE id = %s FOR UPDATE",
            (emprestimo["equipamento_id"],),
        )
        if cur.fetchone()["status"] != "disponivel":
            raise Conflito("O equipamento não está mais disponível.")

        cur.execute(
            "UPDATE emprestimos SET status = 'aprovado', aprovado_por = %s, "
            "data_decisao = NOW() WHERE id = %s",
            (g.usuario["id"], emprestimo_id),
        )
        cur.execute(
            "UPDATE equipamentos SET status = 'emprestado' WHERE id = %s",
            (emprestimo["equipamento_id"],),
        )
        return resposta(buscar_emprestimo(cur, emprestimo_id))


@app.patch("/emprestimos/<int:emprestimo_id>/recusar")
@papel_exigido("gestor")
def recusar_emprestimo(emprestimo_id):
    dados = request.get_json(silent=True) or {}
    observacao = str(dados.get("observacao") or "").strip()[:255] or None

    with transacao() as cur:
        emprestimo = _emprestimo_bloqueado(cur, emprestimo_id)
        if emprestimo["status"] != "solicitado":
            raise Conflito("Só é possível recusar um empréstimo com status 'solicitado'.")

        cur.execute(
            "UPDATE emprestimos SET status = 'recusado', aprovado_por = %s, "
            "data_decisao = NOW(), observacao = %s WHERE id = %s",
            (g.usuario["id"], observacao, emprestimo_id),
        )
        return resposta(buscar_emprestimo(cur, emprestimo_id))


@app.patch("/emprestimos/<int:emprestimo_id>/devolver")
@papel_exigido("gestor")
def registrar_devolucao(emprestimo_id):
    with transacao() as cur:
        emprestimo = _emprestimo_bloqueado(cur, emprestimo_id)
        if emprestimo["status"] != "aprovado":
            raise Conflito("Só é possível devolver um empréstimo com status 'aprovado'.")

        cur.execute(
            "UPDATE emprestimos SET status = 'devolvido', devolvido_por = %s, "
            "data_devolucao = NOW() WHERE id = %s",
            (g.usuario["id"], emprestimo_id),
        )
        cur.execute(
            "UPDATE equipamentos SET status = 'disponivel' WHERE id = %s",
            (emprestimo["equipamento_id"],),
        )
        return resposta(buscar_emprestimo(cur, emprestimo_id))


# ------------------------------------------------------------------ tratamento de erros
# Toda exceção vira JSON no formato {"erro": "<codigo>", "mensagem": "<texto>"}
# com o código HTTP semântico correspondente.
@app.errorhandler(AppError)
def tratar_erro_da_aplicacao(e):
    return jsonify({"erro": e.codigo, "mensagem": e.mensagem}), e.status_code


@app.errorhandler(mysql.connector.IntegrityError)
def tratar_erro_de_integridade(e):
    if e.errno == 1062:  # valor duplicado em coluna UNIQUE
        return (
            jsonify(
                {
                    "erro": "conflito",
                    "mensagem": "Já existe um registro com esse valor único "
                    "(e-mail ou código de patrimônio).",
                }
            ),
            409,
        )
    return jsonify({"erro": "dados_invalidos", "mensagem": "Violação de integridade."}), 400


@app.errorhandler(mysql.connector.Error)
def tratar_erro_de_banco(e):
    app.logger.exception("Erro de banco de dados")
    return (
        jsonify({"erro": "erro_banco", "mensagem": "Erro ao acessar o banco de dados."}),
        503,
    )


@app.errorhandler(HTTPException)
def tratar_erro_http(e):
    return jsonify({"erro": e.name.lower().replace(" ", "_"), "mensagem": e.description}), e.code


@app.errorhandler(Exception)
def tratar_erro_inesperado(e):
    app.logger.exception("Erro inesperado")
    return jsonify({"erro": "erro_interno", "mensagem": "Erro interno do servidor."}), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
