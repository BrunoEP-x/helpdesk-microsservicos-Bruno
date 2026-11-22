"""Serviço de Inventário do HelpDesk Pro."""
from app import config, dados_exemplo
from app.banco import MIGRACOES, banco
from app.rotas import router
from helpdesk_comum.aplicacao import criar_aplicacao
from helpdesk_comum.banco import migrar


def iniciar() -> None:
    migrar(banco.engine, MIGRACOES)
    if config.DADOS_EXEMPLO:
        with banco.Sessao() as db:
            dados_exemplo.carregar(db)


app = criar_aplicacao("inventario", "HelpDesk Pro · Serviço de Inventário", [router], ao_iniciar=iniciar)
