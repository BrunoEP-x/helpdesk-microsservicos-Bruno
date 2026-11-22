"""Priorização automática de chamados.

Um sistema de pontos simples e explicável (sem IA paga):
- o IMPACTO informado (só eu / meu setor / a empresa toda) dá a base;
- palavras e expressões do título e da descrição somam ou subtraem pontos;
- a categoria e o tipo de equipamento ajustam o resultado.

A soma vira uma prioridade (baixa, média, alta ou crítica) e a lista de motivos
é devolvida para quem abre o chamado entender a sugestão. Técnicos e
administradores podem ajustar a prioridade depois.
"""
import re
import unicodedata
from dataclasses import dataclass, field

# (expressão, pontos, motivo). As expressões são comparadas sem acentos e em minúsculas.
REGRAS: list[tuple[str, int, str]] = [
    # indícios de incidente grave
    (r"fora do ar|caiu|derrubou|indisponivel", 4, "sistema ou serviço fora do ar"),
    (r"servidor|banco de dados|sistema principal|erp|producao", 3, "afeta servidor ou sistema central"),
    (r"todos|toda a empresa|ninguem consegue|varios usuarios|setor inteiro", 3, "várias pessoas afetadas"),
    (r"virus|ransomware|invasao|hacker|vazamento|phishing|malware", 5, "possível incidente de segurança"),
    (r"parad[oa]|nao consigo trabalhar|impedid[oa]|bloqueia o trabalho", 3, "trabalho parado"),
    (r"urgente|emergencia|imediato", 2, "marcado como urgente"),
    (r"cliente|venda|caixa|pagamento|folha de pagamento", 2, "impacto em clientes ou pagamentos"),
    # problemas que impedem o uso
    (r"nao liga|nao funciona|nao abre|nao inicia|tela azul|queimou", 3, "equipamento ou sistema não funciona"),
    (r"sem internet|sem rede|sem acesso|nao conecta|nao acessa|sem conexao", 2, "sem acesso à rede ou sistema"),
    (r"senha|bloquead[oa]|login|nao consigo entrar", 1, "problema de acesso"),
    # problemas que atrapalham
    (r"lent[oa]|travando|trava|demora", 1, "lentidão"),
    (r"erro|falha|defeito|atolando|atola|ruido", 1, "erro ou falha"),
    # pedidos sem urgência
    (r"duvida|como faco|como fazer|orientacao", -2, "dúvida ou orientação"),
    (r"solicitacao|solicito|instalar|instalacao|novo usuario|criar acesso|acesso para", -1, "solicitação de serviço"),
    (r"quando possivel|sem pressa|nao e urgente|sugestao|melhoria", -3, "sem urgência informada"),
]

BASE_IMPACTO = {"individual": 0, "setor": 2, "empresa": 4}
AJUSTE_CATEGORIA = {"seguranca": 3, "rede": 1, "acesso": 0, "hardware": 0, "impressora": 0, "software": 0, "outro": 0}
AJUSTE_ATIVO = {"rede": 1}  # equipamento de rede costuma afetar várias pessoas

# pontuação mínima de cada prioridade
LIMIARES = [(7, "critica"), (3, "alta"), (1, "media")]


@dataclass
class Sugestao:
    prioridade: str
    pontos: int
    motivos: list[str] = field(default_factory=list)


def normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", sem_acento.lower())


def sugerir(titulo: str, descricao: str, impacto: str = "individual", categoria: str = "outro",
            tipo_ativo: str | None = None) -> Sugestao:
    texto = normalizar(f"{titulo} {descricao}")
    pontos = BASE_IMPACTO.get(impacto, 0)
    motivos = []
    if impacto == "setor":
        motivos.append("afeta o setor (+2)")
    elif impacto == "empresa":
        motivos.append("afeta a empresa toda (+4)")

    for expressao, valor, motivo in REGRAS:
        if re.search(rf"\b(?:{expressao})", texto):
            pontos += valor
            motivos.append(f"{motivo} ({valor:+d})")

    if AJUSTE_CATEGORIA.get(categoria):
        pontos += AJUSTE_CATEGORIA[categoria]
        motivos.append(f"categoria {categoria} ({AJUSTE_CATEGORIA[categoria]:+d})")
    if tipo_ativo and AJUSTE_ATIVO.get(tipo_ativo):
        pontos += AJUSTE_ATIVO[tipo_ativo]
        motivos.append(f"equipamento de {tipo_ativo} ({AJUSTE_ATIVO[tipo_ativo]:+d})")

    prioridade = next((nome for minimo, nome in LIMIARES if pontos >= minimo), "baixa")
    if not motivos:
        motivos.append("nenhum indício de urgência encontrado")
    return Sugestao(prioridade, pontos, motivos)
