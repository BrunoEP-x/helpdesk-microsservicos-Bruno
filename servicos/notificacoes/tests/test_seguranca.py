from helpdesk_comum import tokens


def test_rotas_exigem_login(cliente):
    for metodo, rota in [("get", "/notificacoes"), ("get", "/notificacoes/contagem"), ("post", "/notificacoes/lidas")]:
        assert getattr(cliente, metodo)(rota).status_code == 401, rota


def test_notificacoes_sao_so_do_proprio_usuario(cliente, sessao, cab):
    from app import servico
    from tests.conftest import DiretorioFalso
    from tests.test_notificacoes import evento
    with sessao() as db:
        servico.processar(db, evento(), DiretorioFalso())
    assert cliente.get("/notificacoes", headers=cab(3)).json() == []
    nid = cliente.get("/notificacoes", headers=cab(2)).json()[0]["id"]
    assert cliente.patch(f"/notificacoes/{nid}/lida", headers=cab(3)).status_code == 404


def test_token_de_servico_nao_le_avisos(cliente):
    assert cliente.get("/notificacoes", headers={"Authorization": f"Bearer {tokens.criar_de_servico('x')}"}).status_code == 403
