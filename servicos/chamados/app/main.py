"""Serviço de Chamados do HelpDesk Pro."""
from app import config, dados_exemplo, tarefas
from app.banco import MIGRACOES, banco
from app.rotas import router
from helpdesk_comum.aplicacao import criar_aplicacao
from helpdesk_comum.banco import migrar


def iniciar() -> None:
    migrar(banco.engine, MIGRACOES)
    if config.DADOS_EXEMPLO:
        with banco.Sessao() as db:
            dados_exemplo.carregar(db)
    if config.TAREFAS_ATIVAS:
        tarefas.iniciar()


app = criar_aplicacao("chamados", "HelpDesk Pro · Serviço de Chamados", [router],
                      ao_iniciar=iniciar, ao_parar=tarefas.parar)
