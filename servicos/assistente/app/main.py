"""Serviço Assistente (chatbot de suporte) do HelpDesk Pro."""
from app.banco import MIGRACOES, banco
from app.rotas import router
from helpdesk_comum.aplicacao import criar_aplicacao
from helpdesk_comum.banco import migrar

app = criar_aplicacao("assistente", "HelpDesk Pro · Assistente de Suporte", [router],
                      ao_iniciar=lambda: migrar(banco.engine, MIGRACOES))
