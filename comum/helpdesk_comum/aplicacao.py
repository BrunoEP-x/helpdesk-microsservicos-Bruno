"""Fábrica de aplicações: todo serviço nasce com a mesma base
(segurança, tratamento de erros, logs e rota de saúde)."""
from contextlib import asynccontextmanager
from typing import Callable

from fastapi import APIRouter, FastAPI

from helpdesk_comum import config, logs
from helpdesk_comum.erros import registrar_tratadores
from helpdesk_comum.http import CabecalhosDeSeguranca


def criar_aplicacao(nome: str, titulo: str, rotas: list[APIRouter],
                    ao_iniciar: Callable[[], None] | None = None,
                    ao_parar: Callable[[], None] | None = None,
                    saude: Callable[[], dict] | None = None) -> FastAPI:
    logs.configurar(nome)

    @asynccontextmanager
    async def ciclo_de_vida(app: FastAPI):
        config.jwt_segredo()  # falha cedo, com mensagem clara, se o segredo não foi configurado
        if ao_iniciar:
            ao_iniciar()
        yield
        if ao_parar:
            ao_parar()

    app = FastAPI(
        title=titulo, version="3.0.0", lifespan=ciclo_de_vida,
        docs_url="/docs" if config.DOCS_ATIVA else None, redoc_url=None,
        openapi_url="/openapi.json" if config.DOCS_ATIVA else None,
    )
    app.add_middleware(CabecalhosDeSeguranca)
    registrar_tratadores(app)
    for rota in rotas:
        app.include_router(rota)

    @app.get("/saude", tags=["Saúde"])
    def rota_saude():
        return {"status": "ok", "servico": nome, **(saude() if saude else {})}

    return app
