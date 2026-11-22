"""Priorização automática, SLA, histórico, avaliação e indicadores."""
from datetime import timedelta

from app import sla
from app.modelos import Chamado
from app.prioridade import sugerir
from helpdesk_comum.banco import agora


def abrir(cliente, h, **dados):
    base = {"titulo": "Teste", "descricao": "Teste"}
    return cliente.post("/chamados", headers=h, json={**base, **dados})


def fluxo_ate_fechar(cliente, contas, cid):
    tec = contas["carla"]["headers"]
    cliente.patch(f"/chamados/{cid}/atribuir", headers=tec, json={"tecnico_id": 4})
    cliente.patch(f"/chamados/{cid}/status", headers=tec, json={"status": "resolvido", "solucao": "Ajustado."})
    cliente.patch(f"/chamados/{cid}/status", headers=contas["ana"]["headers"], json={"status": "fechado"})


# ---------- priorização ----------

def test_regras_de_prioridade():
    assert sugerir("Servidor fora do ar", "Ninguém consegue acessar o ERP", "empresa").prioridade == "critica"
    assert sugerir("Computador não liga", "Apertei o botão e nada acontece").prioridade == "alta"
    assert sugerir("Impressora atolando", "Atola papel", "individual").prioridade == "media"
    assert sugerir("Dúvida", "Como faço para mudar o papel de parede? Sem pressa").prioridade == "baixa"
    assert sugerir("E-mail estranho", "Recebi um phishing", categoria="seguranca").prioridade == "critica"


def test_sem_prioridade_usa_a_sugerida(cliente, contas):
    c = abrir(cliente, contas["ana"]["headers"], titulo="Sistema fora do ar", descricao="Todos do setor parados",
              impacto="setor").json()
    assert c["prioridade"] == c["prioridade_sugerida"] == "critica" and c["prioridade_origem"] == "automatica"


def test_prioridade_informada_fica_registrada(cliente, contas):
    c = abrir(cliente, contas["ana"]["headers"], prioridade="alta").json()
    assert c["prioridade"] == "alta" and c["prioridade_sugerida"] == "baixa" and c["prioridade_origem"] == "informada"


def test_rota_de_sugestao(cliente, contas):
    r = cliente.post("/chamados/sugerir-prioridade", headers=contas["ana"]["headers"],
                     json={"titulo": "Sem internet", "descricao": "Não conecta", "impacto": "setor"}).json()
    assert r["prioridade"] == "alta" and r["prazo_horas"] == 8 and r["motivos"]


def test_tecnico_ajusta_prioridade_e_sla_e_recalculado(cliente, contas, eventos):
    c = abrir(cliente, contas["ana"]["headers"], prioridade="baixa").json()
    r = cliente.patch(f"/chamados/{c['id']}/prioridade", headers=contas["carla"]["headers"],
                      json={"prioridade": "critica", "motivo": "Diretoria parada"})
    assert r.status_code == 200 and r.json()["prioridade_origem"] == "ajuste_manual"
    from datetime import datetime
    horas = (datetime.fromisoformat(r.json()["prazo_sla"]) - datetime.fromisoformat(c["criado_em"])).total_seconds() / 3600
    assert round(horas) == 4
    hist = cliente.get(f"/chamados/{c['id']}/historico", headers=contas["ana"]["headers"]).json()
    assert any(h["acao"] == "prioridade" and h["valor_anterior"] == "baixa" and h["valor_novo"] == "critica"
               and h["autor_nome"] == "Carla" for h in hist)
    assert eventos("PrioridadeAlterada")[0]["dados"]["para"] == "critica"


def test_solicitante_nao_ajusta_prioridade(cliente, contas):
    c = abrir(cliente, contas["ana"]["headers"]).json()
    r = cliente.patch(f"/chamados/{c['id']}/prioridade", headers=contas["ana"]["headers"], json={"prioridade": "critica"})
    assert r.status_code == 403


# ---------- SLA ----------

def test_admin_configura_sla(cliente, contas):
    h = contas["admin"]["headers"]
    r = cliente.put("/chamados/sla", headers=h, json=[{"prioridade": "critica", "horas": 2, "alerta_percentual": 50}])
    assert r.status_code == 200
    c = abrir(cliente, contas["ana"]["headers"], prioridade="critica").json()
    from datetime import datetime
    assert round((datetime.fromisoformat(c["prazo_sla"]) - datetime.fromisoformat(c["criado_em"])).total_seconds() / 3600) == 2


def test_sla_precisa_ser_coerente(cliente, contas):
    r = cliente.put("/chamados/sla", headers=contas["admin"]["headers"],
                    json=[{"prioridade": "critica", "horas": 100, "alerta_percentual": 50}])
    assert r.status_code == 422


def test_so_admin_configura_sla(cliente, contas):
    r = cliente.put("/chamados/sla", headers=contas["carla"]["headers"],
                    json=[{"prioridade": "critica", "horas": 2, "alerta_percentual": 50}])
    assert r.status_code == 403


def test_verificacao_gera_alerta_e_registra_violacao(cliente, contas, sessao, eventos):
    cid = abrir(cliente, contas["ana"]["headers"], prioridade="alta").json()["id"]
    with sessao() as db:
        c = db.get(Chamado, cid)
        # 7 horas depois (alerta em 75% de 8 h = 6 h)
        assert sla.verificar(db, c.criado_em + timedelta(hours=7)) == {"alertas": 1, "violacoes": 0}
        assert sla.verificar(db, c.criado_em + timedelta(hours=7, minutes=30)) == {"alertas": 0, "violacoes": 0}
        assert sla.verificar(db, c.criado_em + timedelta(hours=9)) == {"alertas": 0, "violacoes": 1}
        assert sla.verificar(db, c.criado_em + timedelta(hours=10)) == {"alertas": 0, "violacoes": 0}
    assert eventos("SlaProximo")[0]["avisar_equipe"] is True  # sem técnico, avisa a equipe
    assert eventos("SlaVencido")
    acoes = [h["acao"] for h in cliente.get(f"/chamados/{cid}/historico", headers=contas["carla"]["headers"]).json()]
    assert "alerta_sla" in acoes and "sla_violado" in acoes


def test_chamado_vencido_aparece_como_atrasado(cliente, contas, sessao):
    cid = abrir(cliente, contas["ana"]["headers"], prioridade="critica").json()["id"]
    with sessao() as db:
        c = db.get(Chamado, cid)
        c.criado_em, c.prazo_sla, c.sla_alerta_em = agora() - timedelta(hours=5), agora() - timedelta(hours=1), agora() - timedelta(hours=3)
        db.commit()
    h = contas["carla"]["headers"]
    detalhe = cliente.get(f"/chamados/{cid}", headers=h).json()
    assert detalhe["sla_situacao"] == "vencido" and detalhe["sla_restante_minutos"] < 0
    assert cliente.get("/chamados/painel", headers=h).json()["atrasados"] == 1
    assert len(cliente.get("/chamados", params={"sla": "vencido"}, headers=h).json()) == 1


# ---------- histórico ----------

def test_historico_completo(cliente, contas):
    cid = abrir(cliente, contas["ana"]["headers"]).json()["id"]
    fluxo_ate_fechar(cliente, contas, cid)
    hist = cliente.get(f"/chamados/{cid}/historico", headers=contas["ana"]["headers"]).json()
    acoes = [h["acao"] for h in hist]
    assert acoes[0] == "abertura" and hist[0]["autor_nome"] == "Ana"
    assert {"atribuicao", "status", "solucao", "encerramento"} <= set(acoes)


def test_historico_de_outra_pessoa_nao_aparece(cliente, contas):
    cid = abrir(cliente, contas["ana"]["headers"]).json()["id"]
    assert cliente.get(f"/chamados/{cid}/historico", headers=contas["bia"]["headers"]).status_code == 404


# ---------- avaliação ----------

def test_avaliacao_so_depois_de_encerrar_e_uma_vez(cliente, contas):
    cid = abrir(cliente, contas["ana"]["headers"]).json()["id"]
    h = contas["ana"]["headers"]
    assert cliente.post(f"/chamados/{cid}/avaliacao", headers=h, json={"nota": 5}).status_code == 422
    fluxo_ate_fechar(cliente, contas, cid)
    r = cliente.post(f"/chamados/{cid}/avaliacao", headers=h, json={"nota": 4, "comentario": "Rápido"})
    assert r.status_code == 201 and r.json()["tecnico_nome"] == "Carla"
    assert cliente.post(f"/chamados/{cid}/avaliacao", headers=h, json={"nota": 5}).status_code == 422
    assert cliente.get(f"/chamados/{cid}", headers=h).json()["avaliacao_nota"] == 4


def test_so_o_solicitante_avalia_e_nota_valida(cliente, contas):
    cid = abrir(cliente, contas["ana"]["headers"]).json()["id"]
    fluxo_ate_fechar(cliente, contas, cid)
    assert cliente.post(f"/chamados/{cid}/avaliacao", headers=contas["carla"]["headers"], json={"nota": 5}).status_code == 403
    assert cliente.post(f"/chamados/{cid}/avaliacao", headers=contas["ana"]["headers"], json={"nota": 6}).status_code == 422


def test_relatorio_de_satisfacao(cliente, contas):
    for nota in (5, 3):
        cid = abrir(cliente, contas["ana"]["headers"]).json()["id"]
        fluxo_ate_fechar(cliente, contas, cid)
        cliente.post(f"/chamados/{cid}/avaliacao", headers=contas["ana"]["headers"], json={"nota": nota})
    r = cliente.get("/chamados/relatorios/satisfacao", headers=contas["admin"]["headers"]).json()
    assert r["media"] == 4.0 and r["total"] == 2 and r["distribuicao"]["5"] == 1
    assert r["por_tecnico"][0]["tecnico_nome"] == "Carla"
    assert cliente.get("/chamados/relatorios/satisfacao", headers=contas["ana"]["headers"]).status_code == 403


# ---------- painel ----------

def test_painel(cliente, contas):
    abrir(cliente, contas["ana"]["headers"], prioridade="alta")
    abrir(cliente, contas["ana"]["headers"], prioridade="baixa")
    p = cliente.get("/chamados/painel", headers=contas["carla"]["headers"]).json()
    assert p["total"] == 2 and p["por_status"] == {"aberto": 2}
    assert p["por_prioridade"] == {"alta": 1, "baixa": 1} and len(p["serie"]) == 14


def test_painel_com_indicadores_de_desempenho(cliente, contas):
    cid = abrir(cliente, contas["ana"]["headers"]).json()["id"]
    fluxo_ate_fechar(cliente, contas, cid)
    cliente.post(f"/chamados/{cid}/avaliacao", headers=contas["ana"]["headers"], json={"nota": 5})
    p = cliente.get("/chamados/painel", headers=contas["admin"]["headers"]).json()
    assert p["concluidos"] == 1 and p["sla_cumprido_percentual"] == 100.0 and p["tempo_medio_atendimento_horas"] is not None
    tecnico = p["desempenho_tecnicos"][0]
    assert tecnico["tecnico_nome"] == "Carla" and tecnico["resolvidos"] == 1 and tecnico["avaliacao_media"] == 5.0
    assert p["serie"][-1]["abertos"] == 1 and p["serie"][-1]["resolvidos"] == 1


def test_painel_do_solicitante_so_conta_os_seus(cliente, contas):
    abrir(cliente, contas["ana"]["headers"])
    abrir(cliente, contas["bia"]["headers"])
    p = cliente.get("/chamados/painel", headers=contas["bia"]["headers"]).json()
    assert p["total"] == 1 and p["desempenho_tecnicos"] == []


def test_exportar_csv_protege_contra_formulas(cliente, contas):
    abrir(cliente, contas["ana"]["headers"], titulo="=HYPERLINK(1)")
    r = cliente.get("/chamados/relatorios/chamados.csv", headers=contas["admin"]["headers"])
    assert r.status_code == 200 and "'=HYPERLINK(1)" in r.text
    assert cliente.get("/chamados/relatorios/chamados.csv", headers=contas["carla"]["headers"]).status_code == 403


def test_outbox_publica_quando_a_fila_volta(sessao, cliente, contas):
    from app import eventos
    abrir(cliente, contas["ana"]["headers"])

    class FilaFora:
        def xadd(self, *a, **k):
            raise ConnectionError("redis fora")

    class Fila:
        recebidos = []
        def xadd(self, stream, campos, **k):
            self.recebidos.append(campos["evento"])

    with sessao() as db:
        assert eventos.publicar_pendentes(db, FilaFora()) == 0   # nada se perde
        fila = Fila()
        assert eventos.publicar_pendentes(db, fila) == 1
        assert eventos.publicar_pendentes(db, fila) == 0         # não publica duas vezes
    assert '"ChamadoAberto"' in fila.recebidos[0]
