from pathlib import Path

import pytest

WEB = Path(__file__).parent.parent / "app" / "web"


@pytest.mark.parametrize("rota,servico", [
    ("/auth/login", "usuarios"), ("/usuarios/3", "usuarios"), ("/ativos", "inventario-fora"),
    ("/chamados/painel", "chamados"), ("/notificacoes", "notificacoes"), ("/assistente/perguntar", "assistente"),
])
def test_cada_rota_vai_para_o_servico_certo(cliente, rota, servico):
    r = cliente.get(rota)
    if servico == "inventario-fora":
        assert r.status_code == 503
    else:
        assert r.json()["servico"] == servico and r.json()["caminho"] == rota


def test_repassa_token_corpo_consulta_e_request_id(cliente):
    r = cliente.post("/chamados?x=1", headers={"Authorization": "Bearer abc", "Cookie": "sessao=1"}, json={"titulo": "oi"})
    dados = r.json()
    assert dados["authorization"] == "Bearer abc" and dados["consulta"] == "x=1" and '"titulo"' in dados["corpo"]
    assert dados["request_id"] and dados["request_id"] == r.headers["x-request-id"]
    assert dados["cookie"] is None             # cabeçalhos desnecessários não seguem para os serviços
    assert dados["encaminhado_para"]           # IP real do cliente vai em X-Forwarded-For
    assert "x-interno" not in r.headers        # nem voltam dos serviços


def test_servico_fora_do_ar_responde_503_claro_e_o_resto_continua(cliente):
    r = cliente.get("/ativos")
    assert r.status_code == 503 and r.json()["detail"] == "O serviço de Inventário está indisponível no momento."
    assert cliente.get("/chamados").status_code == 200
    assert cliente.get("/usuarios").status_code == 200


def test_saude_mostra_quem_esta_no_ar(cliente):
    r = cliente.get("/saude").json()
    assert r["status"] == "degradado" and r["servicos"]["inventario"]["status"] == "fora do ar"
    assert r["servicos"]["chamados"]["status"] == "ok"


def test_rota_desconhecida(cliente):
    assert cliente.get("/admin/segredo").status_code == 404


def test_tela_servida_com_csp(cliente):
    r = cliente.get("/")
    assert r.status_code == 200 and "HelpDesk Pro" in r.text
    assert "script-src 'self'" in r.headers["content-security-policy"]
    assert r.headers["x-frame-options"] == "DENY" and r.headers["x-content-type-options"] == "nosniff"
    assert cliente.get("/static/js/app.js").status_code == 200
    assert cliente.get("/static/estilo.css").status_code == 200


def test_requisicao_grande_demais(cliente):
    r = cliente.post("/chamados", content=b"x" * 70000, headers={"Content-Type": "application/json"})
    assert r.status_code == 413


def test_tela_escapa_o_html_e_nao_usa_scripts_embutidos():
    util = (WEB / "js" / "util.js").read_text()
    assert "export const esc =" in util
    codigo = "\n".join(p.read_text() for p in (WEB / "js").rglob("*.js"))
    html = (WEB / "index.html").read_text()
    for proibido in ("onclick", "onload", "eval(", "new Function", "document.write"):
        assert proibido not in codigo and proibido not in html, proibido
    assert "<script>" not in html and "style=" not in html and "style=" not in codigo


def test_token_nunca_vai_na_url():
    api = (WEB / "js" / "api.js").read_text()
    assert "Authorization" in api and "?token=" not in api
