import pytest

PERGUNTAS = [
    ("Estou sem internet desde cedo", "Sem conexão com a internet"),
    ("o wifi não conecta", "Sem conexão com a internet"),
    ("A impressora não imprime nada", "Impressora não funciona"),
    ("papel atolado na impressora", "Impressora não funciona"),
    ("meu computador está muito lento e travando", "Computador lento"),
    ("esqueci minha senha e não consigo entrar", "Problemas de login ou senha"),
    ("não tenho acesso ao sistema do financeiro", "Sem acesso a um sistema"),
    ("recebi um email de phishing com link suspeito", "Suspeita de vírus ou e-mail falso"),
]


@pytest.mark.parametrize("texto,titulo", PERGUNTAS)
def test_responde_os_problemas_comuns(cliente, cab, texto, titulo):
    r = cliente.post("/assistente/perguntar", headers=cab(2), json={"texto": texto}).json()
    assert r["tipo"] == "resposta" and r["artigo"]["titulo"] == titulo and len(r["passos"]) >= 3


def test_sem_resposta_orienta_abrir_chamado(cliente, cab):
    r = cliente.post("/assistente/perguntar", headers=cab(2), json={"texto": "a cadeira quebrou o encosto"}).json()
    assert r["tipo"] == "sem_resposta" and r["abrir_chamado"] is True
    assert r["chamado_sugerido"]["descricao"] == "a cadeira quebrou o encosto"


def test_cumprimento_e_atendente(cliente, cab):
    assert cliente.post("/assistente/perguntar", headers=cab(2), json={"texto": "Olá!"}).json()["tipo"] == "cumprimento"
    r = cliente.post("/assistente/perguntar", headers=cab(2), json={"texto": "quero falar com um técnico"}).json()
    assert r["tipo"] == "atendente" and r["abrir_chamado"]


def test_feedback_conta_no_artigo(cliente, cab):
    r = cliente.post("/assistente/perguntar", headers=cab(2), json={"texto": "sem internet"}).json()
    assert cliente.post(f"/assistente/perguntas/{r['pergunta_id']}/feedback", headers=cab(2), json={"util": False}).status_code == 204
    artigo = next(a for a in cliente.get("/assistente/artigos", headers=cab(2)).json() if a["id"] == r["artigo"]["id"])
    assert artigo["util_nao"] == 1 and artigo["consultas"] == 1
    # outra pessoa não dá feedback na pergunta dos outros
    assert cliente.post(f"/assistente/perguntas/{r['pergunta_id']}/feedback", headers=cab(3), json={"util": True}).status_code == 404


def test_admin_cadastra_artigo_e_o_assistente_passa_a_responder(cliente, cab):
    novo = {"titulo": "Cadeira quebrada", "categoria": "outro", "palavras_chave": "cadeira, encosto, mobília",
            "resposta": "Peça uma cadeira reserva ao setor de patrimônio.\nAbra um chamado para troca."}
    assert cliente.post("/assistente/artigos", headers=cab(3), json=novo).status_code == 403
    assert cliente.post("/assistente/artigos", headers=cab(1, "admin"), json=novo).status_code == 201
    r = cliente.post("/assistente/perguntar", headers=cab(2), json={"texto": "a cadeira quebrou o encosto"}).json()
    assert r["tipo"] == "resposta" and r["artigo"]["titulo"] == "Cadeira quebrada"


def test_artigo_desativado_some(cliente, cab):
    artigo = cliente.get("/assistente/artigos", headers=cab(1, "admin")).json()[0]
    dados = {k: artigo[k] for k in ("titulo", "categoria", "palavras_chave", "resposta")}
    cliente.put(f"/assistente/artigos/{artigo['id']}", headers=cab(1, "admin"), json={**dados, "ativo": False})
    assert all(a["id"] != artigo["id"] for a in cliente.get("/assistente/artigos", headers=cab(2)).json())


def test_estatisticas(cliente, cab):
    cliente.post("/assistente/perguntar", headers=cab(2), json={"texto": "sem internet"})
    cliente.post("/assistente/perguntar", headers=cab(2), json={"texto": "a cadeira quebrou"})
    e = cliente.get("/assistente/estatisticas", headers=cab(1, "admin")).json()
    assert e["perguntas"] == 2 and e["respondidas"] == 1 and e["sem_resposta_recentes"] == ["a cadeira quebrou"]
    assert cliente.get("/assistente/estatisticas", headers=cab(2)).status_code == 403


def test_exige_login(cliente):
    assert cliente.post("/assistente/perguntar", json={"texto": "oi"}).status_code == 401
