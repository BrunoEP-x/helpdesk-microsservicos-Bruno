"""Teste ponta a ponta, pelo API Gateway, com todos os serviços no ar.

Uso:  python scripts/teste_ponta_a_ponta.py [http://localhost:8000]
Precisa dos dados de exemplo (DADOS_EXEMPLO=1) e da senha padrão (SENHA_EXEMPLO).
Só usa a biblioteca padrão do Python.

Percorre o fluxo do DESAFIO: login, abrir, atribuir, resolver, fechar e avaliar;
confere segurança (401 sem token, solicitante sem ver chamado alheio), SLA,
histórico, assistente e a chegada das notificações pelo serviço de eventos.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else os.getenv("GATEWAY", "http://localhost:8000")).rstrip("/")
SENHA = os.getenv("SENHA_EXEMPLO", "Helpdesk2026")
falhas = 0


def chamar(metodo, caminho, token=None, corpo=None):
    dados = json.dumps(corpo).encode() if corpo is not None else None
    req = urllib.request.Request(BASE + caminho, data=dados, method=metodo, headers={"Content-Type": "application/json"})
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            texto = r.read().decode()
            return r.status, (json.loads(texto) if texto and r.headers.get_content_type() == "application/json" else texto)
    except urllib.error.HTTPError as erro:
        texto = erro.read().decode()
        try:
            return erro.code, json.loads(texto)
        except ValueError:
            return erro.code, texto


def conferir(descricao, condicao, detalhe=""):
    global falhas
    print(("  OK   " if condicao else "  FALHOU ") + descricao + ("" if condicao else f"  -> {detalhe}"))
    falhas += 0 if condicao else 1


def entrar(email):
    status, r = chamar("POST", "/auth/login", corpo={"email": email, "senha": SENHA})
    if status != 200:
        sys.exit(f"Não consegui entrar como {email} ({status}: {r}). Os dados de exemplo estão ligados?")
    return r["access_token"], r["usuario"]


print(f"HelpDesk Pro · teste ponta a ponta em {BASE}\n")

print("Saúde")
status, saude = chamar("GET", "/saude")
conferir("gateway responde /saude", status == 200, saude)
for nome, info in saude.get("servicos", {}).items():
    conferir(f"serviço {nome} no ar", info["status"] == "ok", info)

print("\nSegurança")
conferir("sem token recebe 401", chamar("GET", "/chamados")[0] == 401)
conferir("token falso recebe 401", chamar("GET", "/chamados", token="abc.def.ghi")[0] == 401)
conferir("senha errada recebe 401", chamar("POST", "/auth/login", corpo={"email": "ana@empresa.com", "senha": "errada123"})[0] == 401)

carla, eu_carla = entrar("carla@empresa.com")
ana, eu_ana = entrar("ana@empresa.com")
bruno, _ = entrar("bruno@empresa.com")
admin, _ = entrar("admin@empresa.com")

print("\nFluxo completo do chamado")
status, sugestao = chamar("POST", "/chamados/sugerir-prioridade", ana,
                          {"titulo": "Sem internet", "descricao": "Ninguém do setor consegue navegar", "impacto": "setor"})
conferir("prioridade sugerida automaticamente", status == 200 and sugestao["prioridade"] in ("alta", "critica"), sugestao)

status, ativos = chamar("GET", "/ativos", ana)
ativo_id = ativos[0]["id"] if status == 200 and ativos else None
status, chamado = chamar("POST", "/chamados", ana, {"titulo": "Sem internet no financeiro",
                         "descricao": "Ninguém do setor consegue navegar desde as 9h", "categoria": "rede",
                         "impacto": "setor", "ativo_id": ativo_id})
conferir("solicitante abre chamado (com equipamento validado no Inventário)", status == 201, chamado)
cid = chamado["id"]
conferir("prioridade definida pela sugestão", chamado["prioridade_origem"] == "automatica", chamado.get("prioridade_origem"))
conferir("prazo de SLA calculado", chamado["sla_situacao"] == "no_prazo" and chamado["sla_restante_minutos"] > 0)

conferir("outro solicitante NÃO vê o chamado (404)", chamar("GET", f"/chamados/{cid}", bruno)[0] == 404)
conferir("solicitante NÃO atribui (403)", chamar("PATCH", f"/chamados/{cid}/atribuir", ana, {"tecnico_id": eu_carla["id"]})[0] == 403)

status, r = chamar("PATCH", f"/chamados/{cid}/atribuir", carla, {"tecnico_id": eu_carla["id"]})
conferir("técnica atribui (Usuários consultado por HTTP)", status == 200 and r["status"] == "em_atendimento", r)
status, r = chamar("PATCH", f"/chamados/{cid}/prioridade", carla, {"prioridade": "critica", "motivo": "Setor inteiro parado"})
conferir("técnica ajusta a prioridade", status == 200 and r["prioridade"] == "critica", r)
status, r = chamar("POST", f"/chamados/{cid}/comentarios", carla, {"texto": "Reiniciando o switch do setor."})
conferir("técnica comenta", status == 201, r)
status, r = chamar("PATCH", f"/chamados/{cid}/status", carla, {"status": "resolvido", "solucao": "Switch reiniciado e cabo trocado."})
conferir("técnica resolve com a solução registrada", status == 200 and r["status"] == "resolvido", r)
status, r = chamar("PATCH", f"/chamados/{cid}/status", ana, {"status": "fechado"})
conferir("solicitante confirma e encerra", status == 200 and r["status"] == "fechado", r)
status, r = chamar("POST", f"/chamados/{cid}/avaliacao", ana, {"nota": 5, "comentario": "Resolveram rápido!"})
conferir("solicitante avalia com 5 estrelas", status == 201, r)

status, hist = chamar("GET", f"/chamados/{cid}/historico", ana)
acoes = [h["acao"] for h in hist] if status == 200 else []
conferir("histórico registra todas as etapas",
         {"abertura", "atribuicao", "prioridade", "status", "solucao", "encerramento", "avaliacao"} <= set(acoes), acoes)

print("\nPainel, relatórios e configurações")
status, painel = chamar("GET", "/chamados/painel", admin)
conferir("painel com indicadores", status == 200 and painel["total"] >= 1 and painel["desempenho_tecnicos"], painel.get("total"))
status, rel = chamar("GET", "/chamados/relatorios/satisfacao", admin)
conferir("relatório de satisfação", status == 200 and rel["total"] >= 1, rel)
conferir("solicitante não vê relatórios (403)", chamar("GET", "/chamados/relatorios/satisfacao", ana)[0] == 403)
status, sla = chamar("GET", "/chamados/sla", admin)
conferir("prazos de SLA configuráveis", status == 200 and len(sla) == 4, sla)
status, csv = chamar("GET", "/chamados/relatorios/chamados.csv", admin)
conferir("exportação CSV", status == 200 and "titulo" in csv, str(csv)[:80])

print("\nAssistente")
status, r = chamar("POST", "/assistente/perguntar", ana, {"texto": "a impressora não imprime"})
conferir("assistente responde problema comum", status == 200 and r["tipo"] == "resposta", r)
status, r = chamar("POST", "/assistente/perguntar", ana, {"texto": "o projetor da sala de reunião está sem imagem"})
conferir("sem resposta, orienta abrir chamado", status == 200 and r["abrir_chamado"], r)

print("\nNotificações por evento (Chamados -> fila -> Notificações)")
tipos = set()
for _ in range(15):
    status, avisos = chamar("GET", "/notificacoes", ana)
    tipos = {a["tipo"] for a in avisos if a["chamado_id"] == cid} if status == 200 else set()
    if {"ChamadoAberto", "ChamadoResolvido", "ChamadoFechado"} <= tipos:
        break
    time.sleep(1)
conferir("solicitante recebeu aberto/resolvido/encerrado", {"ChamadoAberto", "ChamadoResolvido", "ChamadoFechado"} <= tipos, tipos)
status, avisos = chamar("GET", "/notificacoes", carla)
conferir("técnica recebeu a atribuição", status == 200 and any(a["tipo"] == "ChamadoAtribuido" and a["chamado_id"] == cid for a in avisos))
status, avisos = chamar("GET", "/notificacoes", bruno)
conferir("outro solicitante não recebe avisos alheios", status == 200 and all(a["chamado_id"] != cid for a in avisos))

print(f"\n{'Tudo certo!' if not falhas else f'{falhas} verificação(ões) falharam.'}")
sys.exit(1 if falhas else 0)
