"""Serviço de Usuários do HelpDesk Pro."""
from app import config, dados_exemplo
from app.banco import MIGRACOES, banco
from app.rotas_auth import router as auth_router
from app.rotas_usuarios import router as usuarios_router
from helpdesk_comum.aplicacao import criar_aplicacao
from helpdesk_comum.banco import migrar


def iniciar() -> None:
    migrar(banco.engine, MIGRACOES)
    with banco.Sessao() as db:
        if config.DADOS_EXEMPLO:
            dados_exemplo.carregar(db)
        else:
            dados_exemplo.criar_admin_inicial(db)


app = criar_aplicacao("usuarios", "HelpDesk Pro · Serviço de Usuários", [auth_router, usuarios_router],
                      ao_iniciar=iniciar)
