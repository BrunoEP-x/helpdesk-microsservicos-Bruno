"""Indicadores do painel e relatórios.

As consultas buscam só as colunas necessárias (não carregam descrições,
comentários etc.) e usam os índices de status/prazo/técnico.
"""
import csv
import io
import os
from collections import Counter, defaultdict
from datetime import timedelta
from statistics import mean

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modelos import ABERTOS, ENCERRADOS, Avaliacao, Chamado
from helpdesk_comum.banco import agora
from helpdesk_comum.tokens import UsuarioToken

# Fuso usado para agrupar a série por dia (os dados ficam em UTC no banco)
FUSO = timedelta(hours=int(os.getenv("FUSO_HORAS", "-3")))
DIAS_SERIE = 14


def _horas(inicio, fim) -> float:
    return (fim - inicio).total_seconds() / 3600


def _media(valores: list[float]) -> float | None:
    return round(mean(valores), 1) if valores else None


def _escopo(consulta, usuario: UsuarioToken, apenas_meus: bool):
    if not usuario.eh_equipe:
        return consulta.where(Chamado.solicitante_id == usuario.id)
    if apenas_meus and usuario.perfil == "tecnico":
        return consulta.where(Chamado.tecnico_id == usuario.id)
    return consulta


def painel(db: Session, usuario: UsuarioToken, apenas_meus: bool = False) -> dict:
    colunas = select(Chamado.id, Chamado.status, Chamado.prioridade, Chamado.categoria, Chamado.tecnico_id,
                     Chamado.tecnico_nome, Chamado.criado_em, Chamado.atribuido_em, Chamado.resolvido_em,
                     Chamado.prazo_sla, Chamado.sla_alerta_em, Chamado.sla_violado)
    linhas = db.execute(_escopo(colunas, usuario, apenas_meus)).all()
    ids = [l.id for l in linhas]
    notas = db.execute(select(Avaliacao.chamado_id, Avaliacao.nota, Avaliacao.tecnico_id)
                       .where(Avaliacao.chamado_id.in_(ids))).all() if ids else []
    momento = agora()

    por_status = Counter(l.status for l in linhas)
    encerrados = [l for l in linhas if l.status in ENCERRADOS and l.resolvido_em]
    abertos = [l for l in linhas if l.status in ABERTOS]
    cumpridos = [l for l in encerrados if not l.sla_violado]

    # série diária: abertos x resolvidos nos últimos 14 dias
    hoje = (momento + FUSO).date()
    dias = [hoje - timedelta(days=i) for i in range(DIAS_SERIE - 1, -1, -1)]
    abertos_dia = Counter((l.criado_em + FUSO).date() for l in linhas)
    resolvidos_dia = Counter((l.resolvido_em + FUSO).date() for l in encerrados)
    serie = [{"dia": d.isoformat(), "abertos": abertos_dia[d], "resolvidos": resolvidos_dia[d]} for d in dias]

    return {
        "total": len(linhas),
        "por_status": dict(por_status),
        "atrasados": sum(1 for l in abertos if l.prazo_sla < momento),
        "abertos": por_status["aberto"],
        "em_andamento": por_status["em_atendimento"],
        "concluidos": por_status["resolvido"] + por_status["fechado"],
        "por_prioridade": dict(Counter(l.prioridade for l in linhas)),
        "por_categoria": dict(Counter(l.categoria for l in linhas)),
        "tempo_medio_atendimento_horas": _media([_horas(l.criado_em, l.resolvido_em) for l in encerrados]),
        "tempo_medio_primeira_resposta_horas": _media(
            [_horas(l.criado_em, l.atribuido_em) for l in linhas if l.atribuido_em]),
        "sla_cumprido_percentual": round(100 * len(cumpridos) / len(encerrados), 1) if encerrados else None,
        "violacoes_sla": sum(1 for l in linhas if l.sla_violado),
        "em_alerta": sum(1 for l in abertos if l.sla_alerta_em <= momento <= l.prazo_sla),
        "satisfacao_media": _media([n.nota for n in notas]),
        "serie": serie,
        "desempenho_tecnicos": _desempenho(linhas, notas, usuario),
        "gerado_em": momento,
    }


def _desempenho(linhas, notas, usuario: UsuarioToken) -> list[dict]:
    if not usuario.eh_equipe:
        return []
    grupos: dict[int, list] = defaultdict(list)
    for l in linhas:
        if l.tecnico_id:
            grupos[l.tecnico_id].append(l)
    notas_por_tecnico: dict[int, list[int]] = defaultdict(list)
    for n in notas:
        if n.tecnico_id:
            notas_por_tecnico[n.tecnico_id].append(n.nota)
    resultado = []
    for tecnico_id, itens in grupos.items():
        if usuario.perfil == "tecnico" and tecnico_id != usuario.id:
            continue  # o técnico vê os próprios indicadores
        feitos = [l for l in itens if l.status in ENCERRADOS and l.resolvido_em]
        resultado.append({
            "tecnico_id": tecnico_id,
            "tecnico_nome": itens[-1].tecnico_nome or f"Técnico {tecnico_id}",
            "atribuidos": len(itens),
            "em_aberto": sum(1 for l in itens if l.status in ABERTOS),
            "resolvidos": len(feitos),
            "tempo_medio_horas": _media([_horas(l.criado_em, l.resolvido_em) for l in feitos]),
            "violacoes_sla": sum(1 for l in itens if l.sla_violado),
            "avaliacao_media": _media(notas_por_tecnico[tecnico_id]),
            "avaliacoes": len(notas_por_tecnico[tecnico_id]),
        })
    return sorted(resultado, key=lambda d: (-d["resolvidos"], d["tecnico_nome"]))


def satisfacao(db: Session, usuario: UsuarioToken) -> dict:
    consulta = select(Avaliacao).order_by(Avaliacao.id.desc())
    if usuario.perfil == "tecnico":
        consulta = consulta.where(Avaliacao.tecnico_id == usuario.id)
    avaliacoes = list(db.scalars(consulta))
    distribuicao = Counter(a.nota for a in avaliacoes)
    por_tecnico: dict[int, list] = defaultdict(list)
    for a in avaliacoes:
        if a.tecnico_id:
            por_tecnico[a.tecnico_id].append(a)
    return {
        "media": _media([a.nota for a in avaliacoes]),
        "total": len(avaliacoes),
        "distribuicao": {str(n): distribuicao[n] for n in range(1, 6)},
        "por_tecnico": sorted(({"tecnico_id": t, "tecnico_nome": lista[0].tecnico_nome, "media": _media([a.nota for a in lista]),
                                "total": len(lista)} for t, lista in por_tecnico.items()), key=lambda d: -(d["media"] or 0)),
        "recentes": avaliacoes[:20],
    }


def _celula(valor) -> str:
    """Evita injeção de fórmulas ao abrir o CSV no Excel/LibreOffice."""
    texto = "" if valor is None else str(valor)
    return "'" + texto if texto[:1] in ("=", "+", "-", "@", "\t", "\r") else texto


def exportar_csv(db: Session) -> str:
    saida = io.StringIO()
    escritor = csv.writer(saida, delimiter=";")
    escritor.writerow(["id", "titulo", "categoria", "prioridade", "status", "solicitante", "tecnico", "aberto_em_utc",
                       "resolvido_em_utc", "prazo_sla_utc", "sla_violado", "nota"])
    consulta = select(Chamado.id, Chamado.titulo, Chamado.categoria, Chamado.prioridade, Chamado.status,
                      Chamado.solicitante_nome, Chamado.tecnico_nome, Chamado.criado_em, Chamado.resolvido_em,
                      Chamado.prazo_sla, Chamado.sla_violado, Avaliacao.nota
                      ).outerjoin(Avaliacao, Avaliacao.chamado_id == Chamado.id).order_by(Chamado.id)
    for linha in db.execute(consulta):
        escritor.writerow([_celula(v) for v in linha])
    return saida.getvalue()
