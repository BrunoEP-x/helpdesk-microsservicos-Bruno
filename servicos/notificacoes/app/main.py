"""Serviço de Notificações do HelpDesk Pro (bônus: notificações por evento)."""
from app import config, consumidor
from app.banco import MIGRACOES, banco
from app.rotas import router
from helpdesk_comum.aplicacao import criar_aplicacao
from helpdesk_comum.banco import migrar


def iniciar() -> None:
    migrar(banco.engine, MIGRACOES)
    if config.CONSUMIDOR_ATIVO:
        consumidor.iniciar()


def saude() -> dict:
    return {"fila": {"conectada": consumidor.estado["ativo"], "processados": consumidor.estado["processados"],
                     "email": bool(config.SMTP_HOST)}}


app = criar_aplicacao("notificacoes", "HelpDesk Pro · Serviço de Notificações", [router],
                      ao_iniciar=iniciar, ao_parar=consumidor.parar, saude=saude)
