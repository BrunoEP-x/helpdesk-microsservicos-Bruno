"""Erros de negócio e tratamento centralizado de exceções.

As regras de negócio lançam exceções do domínio (sem saber nada de HTTP) e
`registrar_tratadores` traduz cada uma para o código HTTP certo, sempre no
mesmo formato: {"detail": "mensagem"}.
"""
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

log = logging.getLogger("helpdesk.erros")


class ErroDeNegocio(Exception):
    status_code = 400


class NaoEncontrado(ErroDeNegocio):
    """O recurso não existe (ou o usuário não pode vê-lo)."""
    status_code = 404


class RegraDeNegocio(ErroDeNegocio):
    """A operação viola uma regra do sistema."""
    status_code = 422


class SemPermissao(ErroDeNegocio):
    """O usuário está logado, mas não pode fazer esta operação."""
    status_code = 403


class Conflito(ErroDeNegocio):
    status_code = 409


class ServicoIndisponivel(ErroDeNegocio):
    """Outro serviço necessário não respondeu a tempo."""
    status_code = 503


def registrar_tratadores(app: FastAPI) -> None:
    @app.exception_handler(ErroDeNegocio)
    async def tratar_negocio(request: Request, erro: ErroDeNegocio):
        if erro.status_code >= 500:
            log.warning("falha de dependência em %s %s: %s", request.method, request.url.path, erro)
        return JSONResponse(status_code=erro.status_code, content={"detail": str(erro)})

    @app.exception_handler(IntegrityError)
    async def tratar_conflito(request: Request, erro: IntegrityError):
        # Não expõe detalhes do banco na resposta
        return JSONResponse(status_code=409, content={"detail": "O registro conflita com outro já existente."})

    @app.exception_handler(Exception)
    async def tratar_inesperado(request: Request, erro: Exception):
        log.exception("erro inesperado em %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content={"detail": "Erro interno. Tente novamente."})
