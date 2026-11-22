"""Motor de respostas do assistente (regras simples, sem IA externa).

1. Normaliza o texto (minúsculas, sem acentos, sem pontuação).
2. Reconhece intenções curtas: cumprimento, agradecimento, pedido de atendente.
3. Pontua cada artigo: expressão-chave inteira encontrada vale 3, palavra-chave
   isolada vale 2 e palavra do título vale 1.
4. Com 3 pontos ou mais, responde com o artigo. Abaixo disso, sugere os mais
   próximos e orienta a abrir um chamado.
"""
import re
import unicodedata
from dataclasses import dataclass, field

STOPWORDS = set("a o e de da do das dos em no na nos nas um uma uns umas para pra por com sem que se meu minha "
                "meus minhas esta este isso esse essa ta to tem ter estou esta estao foi ser nao sim ja mais muito "
                "como qual quando onde porque eu voce ele ela ao aos as os me mim pelo pela".split())
# "nao" é stopword ao comparar palavras soltas, mas continua valendo dentro de expressões ("nao imprime")

LIMIAR_RESPOSTA = 3
CUMPRIMENTOS = {"oi", "ola", "bom dia", "boa tarde", "boa noite", "hello", "e ai"}
AGRADECIMENTOS = ("obrigad", "valeu", "agradeco", "resolveu", "funcionou")
ATENDENTE = ("abrir chamado", "falar com", "atendente", "tecnico", "humano", "suporte presencial")


def normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", sem_acento)).strip()


def radical(palavra: str) -> str:
    """Radical bem simples: ignora plural e algumas terminações comuns."""
    for fim in ("ando", "endo", "indo", "mente", "coes", "cao", "s"):
        if len(palavra) > len(fim) + 3 and palavra.endswith(fim):
            return palavra[: -len(fim)]
    return palavra


def palavras(texto: str) -> set[str]:
    return {radical(p) for p in normalizar(texto).split() if p not in STOPWORDS and len(p) > 1}


@dataclass
class Resultado:
    tipo: str                         # "resposta" | "sugestoes" | "sem_resposta" | "cumprimento" | "agradecimento" | "atendente"
    artigo: object | None = None
    pontos: int = 0
    sugestoes: list = field(default_factory=list)


def pontuar(texto_normal: str, tokens: set[str], artigo) -> int:
    pontos = 0
    for chave in (c.strip() for c in artigo.palavras_chave.split(",")):
        chave_normal = normalizar(chave)
        if not chave_normal:
            continue
        if " " in chave_normal:
            if re.search(rf"\b{re.escape(chave_normal)}\b", texto_normal):
                pontos += 3
        elif radical(chave_normal) in tokens:
            pontos += 2
    pontos += len(palavras(artigo.titulo) & tokens)
    return pontos


def responder(texto: str, artigos: list) -> Resultado:
    normal = normalizar(texto)
    if normal in CUMPRIMENTOS or (len(normal.split()) <= 2 and any(normal.startswith(c) for c in CUMPRIMENTOS)):
        return Resultado("cumprimento")
    if len(normal.split()) <= 4 and any(a in normal for a in AGRADECIMENTOS):
        return Resultado("agradecimento")
    if any(a in normal for a in ATENDENTE) and len(normal.split()) <= 6:
        return Resultado("atendente")

    tokens = palavras(texto)
    ranking = sorted(((pontuar(normal, tokens, a), a) for a in artigos), key=lambda par: -par[0])
    ranking = [(p, a) for p, a in ranking if p > 0]
    if ranking and ranking[0][0] >= LIMIAR_RESPOSTA:
        return Resultado("resposta", ranking[0][1], ranking[0][0], [a for _, a in ranking[1:3]])
    if ranking:
        return Resultado("sugestoes", None, ranking[0][0], [a for _, a in ranking[:3]])
    return Resultado("sem_resposta")
