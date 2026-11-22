NOVO = {"patrimonio": "PAT-1", "tipo": "computador", "descricao": "Dell", "setor": "TI"}


def test_tecnico_cadastra_ativo_e_filtra_por_setor(cliente, contas):
    h = contas["carla"]
    cliente.post("/ativos", headers=h, json={"patrimonio": "PAT-1", "tipo": "impressora", "descricao": "HP", "setor": "RH"})
    cliente.post("/ativos", headers=h, json={"patrimonio": "PAT-2", "tipo": "computador", "descricao": "Dell", "setor": "TI"})
    assert len(cliente.get("/ativos", params={"setor": "RH"}, headers=h).json()) == 1
    assert len(cliente.get("/ativos", params={"tipo": "computador"}, headers=h).json()) == 1


def test_novos_tipos_de_equipamento(cliente, contas):
    for i, tipo in enumerate(["monitor", "periferico", "notebook"]):
        r = cliente.post("/ativos", headers=contas["carla"], json={**NOVO, "patrimonio": f"PAT-{i}", "tipo": tipo})
        assert r.status_code == 201, r.text


def test_vincula_responsavel_consultando_usuarios_por_http(cliente, contas):
    r = cliente.post("/ativos", headers=contas["carla"], json={**NOVO, "responsavel_id": 2})
    assert r.status_code == 201 and r.json()["responsavel_nome"] == "Ana"
    assert len(cliente.get("/ativos", params={"responsavel_id": 2}, headers=contas["ana"]).json()) == 1


def test_responsavel_inexistente(cliente, contas):
    assert cliente.post("/ativos", headers=contas["carla"], json={**NOVO, "responsavel_id": 99}).status_code == 404


def test_responsavel_desativado(cliente, contas):
    assert cliente.post("/ativos", headers=contas["carla"], json={**NOVO, "responsavel_id": 5}).status_code == 422


def test_usuarios_fora_do_ar_responde_503(cliente, contas):
    from app.clientes import cliente_usuarios
    from app.main import app
    from helpdesk_comum.clientes import ClienteServico
    app.dependency_overrides[cliente_usuarios] = lambda: ClienteServico("Usuários", "http://127.0.0.1:9", timeout=0.5)
    r = cliente.post("/ativos", headers=contas["carla"], json={**NOVO, "responsavel_id": 2})
    assert r.status_code == 503 and "Usuários" in r.json()["detail"]
    # sem responsável, o cadastro não depende de Usuários e continua funcionando
    assert cliente.post("/ativos", headers=contas["carla"], json=NOVO).status_code == 201


def test_atualiza_situacao_e_responsavel(cliente, contas):
    aid = cliente.post("/ativos", headers=contas["carla"], json=NOVO).json()["id"]
    r = cliente.patch(f"/ativos/{aid}", headers=contas["carla"], json={"situacao": "manutencao", "responsavel_id": 4})
    assert r.json()["situacao"] == "manutencao" and r.json()["responsavel_nome"] == "Carla"
    r = cliente.patch(f"/ativos/{aid}", headers=contas["carla"], json={"responsavel_id": 0})
    assert r.json()["responsavel_id"] is None


def test_resumo(cliente, contas):
    cliente.post("/ativos", headers=contas["carla"], json=NOVO)
    cliente.post("/ativos", headers=contas["carla"], json={**NOVO, "patrimonio": "PAT-2", "situacao": "estoque"})
    r = cliente.get("/ativos/resumo", headers=contas["admin"]).json()
    assert r == {"total": 2, "por_tipo": {"computador": 2}, "por_situacao": {"em_uso": 1, "estoque": 1}}


def test_patrimonio_repetido(cliente, contas):
    cliente.post("/ativos", headers=contas["carla"], json=NOVO)
    assert cliente.post("/ativos", headers=contas["carla"], json=NOVO).status_code == 422


def test_busca(cliente, contas):
    cliente.post("/ativos", headers=contas["carla"], json={**NOVO, "numero_serie": "SN-XYZ"})
    assert len(cliente.get("/ativos", params={"busca": "xyz"}, headers=contas["ana"]).json()) == 1
