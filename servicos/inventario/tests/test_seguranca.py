def test_rotas_exigem_login(cliente):
    for metodo, rota in [("get", "/ativos"), ("get", "/ativos/1"), ("post", "/ativos"), ("patch", "/ativos/1")]:
        assert getattr(cliente, metodo)(rota).status_code == 401, rota


def test_token_falso(cliente):
    assert cliente.get("/ativos", headers={"Authorization": "Bearer abc.def.ghi"}).status_code == 401


def test_solicitante_nao_cadastra_nem_altera_ativo(cliente, contas):
    r = cliente.post("/ativos", headers=contas["ana"], json={"patrimonio": "PAT-9", "tipo": "outro", "descricao": "X", "setor": "TI"})
    assert r.status_code == 403
    assert cliente.patch("/ativos/1", headers=contas["ana"], json={"situacao": "descartado"}).status_code == 403
    assert cliente.get("/ativos/resumo", headers=contas["ana"]).status_code == 403


def test_campos_extras_e_patrimonio_invalido(cliente, contas):
    base = {"patrimonio": "PAT-9", "tipo": "outro", "descricao": "X1", "setor": "TI"}
    assert cliente.post("/ativos", headers=contas["carla"], json={**base, "id": 5}).status_code == 422
    assert cliente.post("/ativos", headers=contas["carla"], json={**base, "patrimonio": "<b>"}).status_code == 422
