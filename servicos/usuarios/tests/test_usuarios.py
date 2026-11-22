from helpdesk_comum import tokens


def test_admin_cria_usuario(cliente, contas):
    r = cliente.post("/usuarios", headers=contas["admin"]["headers"],
                     json={"nome": "Davi", "email": "davi@x.com", "perfil": "tecnico", "senha": "Forte1234"})
    assert r.status_code == 201
    assert "senha" not in r.json() and "senha_hash" not in r.json()


def test_email_repetido_e_recusado(cliente, contas):
    dados = {"nome": "Ana 2", "email": "ANA@x.com", "perfil": "solicitante", "senha": "Forte1234"}
    assert cliente.post("/usuarios", headers=contas["admin"]["headers"], json=dados).status_code == 422


def test_usuario_inexistente(cliente, contas):
    assert cliente.get("/usuarios/99", headers=contas["ana"]["headers"]).status_code == 404


def test_lista_publica_nao_mostra_email(cliente, contas):
    lista = cliente.get("/usuarios", headers=contas["ana"]["headers"]).json()
    assert lista and all("email" not in u for u in lista)


def test_lista_filtra_por_perfil_e_ids(cliente, contas):
    h = contas["ana"]["headers"]
    assert [u["nome"] for u in cliente.get("/usuarios", params={"perfil": "tecnico"}, headers=h).json()] == ["Carla"]
    ids = [contas["ana"]["id"], contas["bia"]["id"]]
    assert len(cliente.get("/usuarios", params={"ids": ids}, headers=h).json()) == 2


def test_login_leva_o_nome_no_token(cliente, contas):
    token = contas["carla"]["headers"]["Authorization"].split()[1]
    assert tokens.ler(token).nome == "Carla"


def test_admin_desativa_usuario_e_ele_perde_o_acesso(cliente, contas):
    h = contas["admin"]["headers"]
    r = cliente.patch(f"/usuarios/{contas['bia']['id']}", headers=h, json={"ativo": False})
    assert r.status_code == 200 and r.json()["ativo"] is False
    assert cliente.get("/auth/eu", headers=contas["bia"]["headers"]).status_code == 401
    assert cliente.post("/auth/login", json={"email": "bia@x.com", "senha": "Senha123"}).status_code == 401


def test_admin_nao_remove_o_proprio_acesso(cliente, contas):
    r = cliente.patch(f"/usuarios/{contas['admin']['id']}", headers=contas["admin"]["headers"], json={"perfil": "tecnico"})
    assert r.status_code == 422


def test_admin_promove_a_tecnico(cliente, contas):
    r = cliente.patch(f"/usuarios/{contas['ana']['id']}", headers=contas["admin"]["headers"], json={"perfil": "tecnico"})
    assert r.json()["perfil"] == "tecnico"


def test_detalhes_so_para_admin(cliente, contas):
    assert cliente.get("/usuarios/detalhes", headers=contas["carla"]["headers"]).status_code == 403
    lista = cliente.get("/usuarios/detalhes", headers=contas["admin"]["headers"]).json()
    assert {"email", "ultimo_login"} <= set(lista[0])


def test_admin_redefine_senha(cliente, contas):
    r = cliente.put(f"/usuarios/{contas['ana']['id']}/senha", headers=contas["admin"]["headers"], json={"senha": "Nova12345"})
    assert r.status_code == 204
    assert cliente.post("/auth/login", json={"email": "ana@x.com", "senha": "Nova12345"}).status_code == 200


def test_usuario_troca_a_propria_senha(cliente, contas):
    h = contas["ana"]["headers"]
    assert cliente.post("/auth/senha", headers=h, json={"senha_atual": "errada", "nova_senha": "Nova12345"}).status_code == 422
    assert cliente.post("/auth/senha", headers=h, json={"senha_atual": "Senha123", "nova_senha": "Nova12345"}).status_code == 204


def test_contato_so_para_admin_e_servicos(cliente, contas):
    rota = f"/usuarios/{contas['ana']['id']}/contato"
    assert cliente.get(rota, headers=contas["carla"]["headers"]).status_code == 403
    servico = {"Authorization": f"Bearer {tokens.criar_de_servico('notificacoes')}"}
    assert cliente.get(rota, headers=servico).json()["email"] == "ana@x.com"


def test_token_de_servico_nao_acessa_rotas_de_pessoa(cliente, contas):
    servico = {"Authorization": f"Bearer {tokens.criar_de_servico('notificacoes')}"}
    assert cliente.get("/auth/eu", headers=servico).status_code == 403
    assert cliente.post("/usuarios", headers=servico, json={}).status_code == 403


def test_migracoes_registradas(cliente, sessao):
    from sqlalchemy import text
    with sessao() as db:
        assert db.execute(text("SELECT versao FROM _migracoes")).scalars().all() == [1]
