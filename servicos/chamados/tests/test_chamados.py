"""Fluxo principal de chamados (adaptado do monólito) e as novas regras."""
from datetime import datetime, timedelta

from tests.conftest import fora_do_ar


def abrir(cliente, contas, ativo, quem="ana", prioridade="alta", **extra):
    dados = {"titulo": "PC não liga", "descricao": "Nada acontece", "prioridade": prioridade, "ativo_id": ativo["id"], **extra}
    return cliente.post("/chamados", headers=contas[quem]["headers"], json=dados)


def test_abrir_calcula_sla_e_publica_evento(cliente, contas, ativo, eventos):
    r = abrir(cliente, contas, ativo, prioridade="critica")
    assert r.status_code == 201
    c = r.json()
    assert c["solicitante_id"] == contas["ana"]["id"] and c["solicitante_nome"] == "Ana"
    assert c["ativo_descricao"] == "PAT-1 · Desktop"
    horas = (datetime.fromisoformat(c["prazo_sla"]) - datetime.fromisoformat(c["criado_em"])).total_seconds() / 3600
    assert round(horas) == 4
    evento = eventos("ChamadoAberto")[0]
    assert evento["destinatarios"] == [contas["ana"]["id"]] and evento["avisar_equipe"] is True


def test_abrir_com_ativo_inexistente(cliente, contas, ativo):
    assert abrir(cliente, contas, ativo, ativo_id=999).status_code == 404


def test_inventario_fora_do_ar_responde_503_sem_travar(cliente, contas, ativo):
    from app.clientes import cliente_inventario
    from app.main import app
    app.dependency_overrides[cliente_inventario] = fora_do_ar("Inventário")
    r = abrir(cliente, contas, ativo)
    assert r.status_code == 503 and "Inventário" in r.json()["detail"]
    # sem equipamento, abrir chamado continua funcionando
    assert abrir(cliente, contas, ativo, ativo_id=None).status_code == 201
    assert cliente.get("/chamados", headers=contas["carla"]["headers"]).status_code == 200


def test_usuarios_fora_do_ar_responde_503_ao_atribuir(cliente, contas, ativo):
    from app.clientes import cliente_usuarios
    from app.main import app
    cid = abrir(cliente, contas, ativo).json()["id"]
    app.dependency_overrides[cliente_usuarios] = fora_do_ar("Usuários")
    r = cliente.patch(f"/chamados/{cid}/atribuir", headers=contas["carla"]["headers"], json={"tecnico_id": 4})
    assert r.status_code == 503 and "Usuários" in r.json()["detail"]


def test_atribuir_muda_status_e_avisa_tecnico(cliente, contas, ativo, eventos):
    cid = abrir(cliente, contas, ativo).json()["id"]
    r = cliente.patch(f"/chamados/{cid}/atribuir", headers=contas["carla"]["headers"], json={"tecnico_id": 4})
    assert r.json()["status"] == "em_atendimento" and r.json()["tecnico_nome"] == "Carla"
    assert eventos("ChamadoAtribuido")[0]["destinatarios"] == [2, 4]


def test_so_tecnico_pode_ser_atribuido(cliente, contas, ativo):
    cid = abrir(cliente, contas, ativo).json()["id"]
    r = cliente.patch(f"/chamados/{cid}/atribuir", headers=contas["carla"]["headers"], json={"tecnico_id": 2})
    assert r.status_code == 422


def test_fluxo_completo_de_status(cliente, contas, ativo, eventos):
    cid = abrir(cliente, contas, ativo).json()["id"]
    tec = contas["carla"]["headers"]
    cliente.patch(f"/chamados/{cid}/atribuir", headers=tec, json={"tecnico_id": 4})
    r = cliente.patch(f"/chamados/{cid}/status", headers=tec, json={"status": "resolvido", "solucao": "Troquei a fonte."})
    assert r.status_code == 200 and r.json()["solucao"] == "Troquei a fonte." and r.json()["sla_situacao"] == "cumprido"
    # o próprio solicitante confirma e fecha
    r = cliente.patch(f"/chamados/{cid}/status", headers=contas["ana"]["headers"], json={"status": "fechado"})
    assert r.json()["status"] == "fechado" and r.json()["fechado_em"]
    assert [e["tipo"] for e in eventos()] == ["ChamadoAberto", "ChamadoAtribuido", "ChamadoResolvido", "ChamadoFechado"]


def test_reabrir_avisa_o_tecnico(cliente, contas, ativo, eventos):
    cid = abrir(cliente, contas, ativo).json()["id"]
    tec = contas["carla"]["headers"]
    cliente.patch(f"/chamados/{cid}/atribuir", headers=tec, json={"tecnico_id": 4})
    cliente.patch(f"/chamados/{cid}/status", headers=tec, json={"status": "resolvido"})
    r = cliente.patch(f"/chamados/{cid}/status", headers=contas["ana"]["headers"], json={"status": "em_atendimento"})
    assert r.json()["status"] == "em_atendimento" and r.json()["resolvido_em"] is None
    assert eventos("StatusAlterado")[0]["destinatarios"] == [2, 4]


def test_transicao_invalida(cliente, contas, ativo):
    cid = abrir(cliente, contas, ativo).json()["id"]
    r = cliente.patch(f"/chamados/{cid}/status", headers=contas["carla"]["headers"], json={"status": "fechado"})
    assert r.status_code == 422


def test_iniciar_atendimento_sem_tecnico(cliente, contas, ativo):
    cid = abrir(cliente, contas, ativo).json()["id"]
    r = cliente.patch(f"/chamados/{cid}/status", headers=contas["carla"]["headers"], json={"status": "em_atendimento"})
    assert r.status_code == 422


def test_comentar_usa_o_usuario_logado(cliente, contas, ativo):
    cid = abrir(cliente, contas, ativo).json()["id"]
    r = cliente.post(f"/chamados/{cid}/comentarios", headers=contas["carla"]["headers"], json={"texto": "Verificando a fonte."})
    assert r.status_code == 201 and r.json()["autor_id"] == contas["carla"]["id"] and r.json()["autor_nome"] == "Carla"
    assert len(cliente.get(f"/chamados/{cid}", headers=contas["ana"]["headers"]).json()["comentarios"]) == 1


def test_nota_interna_nao_aparece_para_o_solicitante(cliente, contas, ativo):
    cid = abrir(cliente, contas, ativo).json()["id"]
    cliente.post(f"/chamados/{cid}/comentarios", headers=contas["carla"]["headers"], json={"texto": "Fonte queimada", "interno": True})
    assert cliente.get(f"/chamados/{cid}", headers=contas["ana"]["headers"]).json()["comentarios"] == []
    assert len(cliente.get(f"/chamados/{cid}", headers=contas["carla"]["headers"]).json()["comentarios"]) == 1
    r = cliente.post(f"/chamados/{cid}/comentarios", headers=contas["ana"]["headers"], json={"texto": "x", "interno": True})
    assert r.status_code == 403


def test_filtros_da_lista(cliente, contas, ativo):
    abrir(cliente, contas, ativo, prioridade="baixa", titulo="Mouse com defeito")
    abrir(cliente, contas, ativo, prioridade="critica")
    h = contas["carla"]["headers"]
    assert len(cliente.get("/chamados", params={"prioridade": "critica"}, headers=h).json()) == 1
    assert len(cliente.get("/chamados", params={"busca": "mouse"}, headers=h).json()) == 1
    assert len(cliente.get("/chamados", params={"ativo_id": 1}, headers=h).json()) == 2
