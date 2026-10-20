"""Exceções de domínio da aplicação.

Cada exceção carrega o código HTTP semântico correspondente. O handler
central em app.py traduz qualquer AppError para uma resposta JSON com esse
código, então as rotas só precisam dar `raise`.
"""


class AppError(Exception):
    status_code = 500
    codigo = "erro_interno"
    mensagem_padrao = "Erro interno do servidor."

    def __init__(self, mensagem=None):
        self.mensagem = mensagem or self.mensagem_padrao
        super().__init__(self.mensagem)


class DadosInvalidos(AppError):
    """400 - o corpo ou os parâmetros da requisição estão incorretos."""

    status_code = 400
    codigo = "dados_invalidos"
    mensagem_padrao = "Dados inválidos."


class NaoAutenticado(AppError):
    """401 - sem login, token ausente, inválido ou expirado."""

    status_code = 401
    codigo = "nao_autenticado"
    mensagem_padrao = "Autenticação necessária."


class SemPermissao(AppError):
    """403 - logado, mas o papel do usuário não permite a ação."""

    status_code = 403
    codigo = "sem_permissao"
    mensagem_padrao = "Você não tem permissão para esta ação."


class NaoEncontrado(AppError):
    """404 - o recurso pedido não existe."""

    status_code = 404
    codigo = "nao_encontrado"
    mensagem_padrao = "Recurso não encontrado."


class Conflito(AppError):
    """409 - a ação conflita com o estado atual (ex.: equipamento já emprestado)."""

    status_code = 409
    codigo = "conflito"
    mensagem_padrao = "A operação conflita com o estado atual do recurso."
