import pytest

from app import servico
from helpdesk_comum.erros import ServicoIndisponivel
from helpdesk_comum.eventos import Evento
from tests.conftest import DiretorioFalso


def evento(tipo="ChamadoAberto", destinatarios=(2,), equipe=False, id="e1", **dados):
    return Evento(id=id, tipo=tipo, chamado_id=7, titulo="PC não liga", destinatarios=list(destinatarios),
                  avisar_equipe=equipe, dados={"prioridade": "alta", **dados})


def test_evento_vira_aviso_para_o_solicitante_e_a_equipe(cliente, sessao, cab):
    with sessao() as db:
        criados = servico.processar(db, evento(equipe=True, solicitante="Ana"), DiretorioFalso())
    assert sorted(n.destinatario_id for n in criados) == [1, 2, 4]
    ana = cliente.get("/notificacoes", headers=cab(2)).json()
    assert ana[0]["tipo"] == "ChamadoAberto" and ana[0]["titulo"] == "Chamado #7 aberto"
    carla = cliente.get("/notificacoes", headers=cab(4, "tecnico")).json()
    assert carla[0]["titulo"] == "Novo chamado #7" and "Ana" in carla[0]["mensagem"]


def test_evento_repetido_nao_duplica(sessao):
    with sessao() as db:
        servico.processar(db, evento(), DiretorioFalso())
        assert servico.processar(db, evento(), DiretorioFalso()) == []
        assert len(servico.listar(db, 2)) == 1


def test_mensagem_de_atribuicao_depende_de_quem_recebe(cliente, sessao, cab):
    with sessao() as db:
        servico.processar(db, evento("ChamadoAtribuido", (2, 4), tecnico="Carla", tecnico_id=4), DiretorioFalso())
    assert cliente.get("/notificacoes", headers=cab(4)).json()[0]["titulo"] == "Chamado #7 atribuído a você"
    assert "Carla está cuidando" in cliente.get("/notificacoes", headers=cab(2)).json()[0]["mensagem"]


def test_usuarios_fora_do_ar_mantem_o_evento_pendente(sessao):
    """O consumidor não confirma o evento; ele será reprocessado depois."""
    with sessao() as db:
        with pytest.raises(ServicoIndisponivel):
            servico.processar(db, evento(equipe=True), DiretorioFalso(falhar=True))
        assert servico.listar(db, 2) == []
        servico.processar(db, evento(equipe=True), DiretorioFalso())
        assert len(servico.listar(db, 2)) == 1


def test_todos_os_tipos_tem_mensagem(sessao):
    from helpdesk_comum.eventos import TIPOS
    with sessao() as db:
        for i, tipo in enumerate(TIPOS):
            n = servico.processar(db, evento(tipo, id=f"t{i}", de="baixa", para="alta", minutos_restantes=30), DiretorioFalso())
            assert n and "#7" in n[0].titulo, tipo


def test_marcar_como_lida_e_contagem(cliente, sessao, cab):
    with sessao() as db:
        servico.processar(db, evento(id="a"), DiretorioFalso())
        servico.processar(db, evento(id="b"), DiretorioFalso())
    h = cab(2)
    assert cliente.get("/notificacoes/contagem", headers=h).json() == {"nao_lidas": 2}
    nid = cliente.get("/notificacoes", headers=h).json()[0]["id"]
    assert cliente.patch(f"/notificacoes/{nid}/lida", headers=h).json()["lida"] is True
    assert cliente.post("/notificacoes/lidas", headers=h).json() == {"marcadas": 1}
    assert cliente.get("/notificacoes", params={"nao_lidas": True}, headers=h).json() == []


def test_email_desligado_sem_smtp(sessao):
    from app.email import CanalEmail
    assert CanalEmail(DiretorioFalso()).enviar(2, "t", "m") is False


def test_consumidor_com_redis_de_verdade(sessao, monkeypatch):
    """Usa o redis-server local, se existir; senão, o teste é pulado."""
    import shutil
    import subprocess
    import time
    if not shutil.which("redis-server"):
        pytest.skip("redis-server não instalado")
    redis = pytest.importorskip("redis")
    proc = subprocess.Popen(["redis-server", "--port", "6390", "--save", "", "--appendonly", "no"],
                            stdout=subprocess.DEVNULL)
    try:
        time.sleep(0.5)
        r = redis.Redis(port=6390)
        from app import consumidor
        from helpdesk_comum import eventos as ev
        consumidor._garantir_grupo(r)
        r.xadd(ev.STREAM, {"evento": evento(id="redis-1").para_json()})
        msgs = r.xreadgroup(ev.GRUPO_NOTIFICACOES, "teste", {ev.STREAM: ">"}, count=10)
        consumidor._tratar(r, msgs, DiretorioFalso(), None)
        assert r.xpending(ev.STREAM, ev.GRUPO_NOTIFICACOES)["pending"] == 0
        with sessao() as db:
            assert servico.listar(db, 2)[0].evento_id == "redis-1"
    finally:
        proc.terminate()
