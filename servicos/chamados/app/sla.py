"""Controle de SLA: prazos por prioridade, alertas de vencimento e registro de violações."""
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import eventos, historico
from app.modelos import ABERTOS, Chamado, ConfiguracaoSla
from helpdesk_comum import eventos as tipos
from helpdesk_comum.banco import agora
from helpdesk_comum.erros import RegraDeNegocio

# prioridade: (horas para resolver, % do prazo consumido que dispara o alerta)
PADRAO = {"critica": (4, 50), "alta": (8, 75), "media": (24, 75), "baixa": (72, 80)}


def configuracao(db: Session) -> dict[str, tuple[int, int]]:
    linhas = {c.prioridade: (c.horas, c.alerta_percentual) for c in db.scalars(select(ConfiguracaoSla))}
    return {p: linhas.get(p, PADRAO[p]) for p in PADRAO}


def calcular_prazos(db: Session, prioridade: str, inicio: datetime) -> tuple[datetime, datetime]:
    """Devolve (prazo final, momento do alerta)."""
    horas, alerta = configuracao(db)[prioridade]
    prazo = inicio + timedelta(hours=horas)
    return prazo, inicio + timedelta(hours=horas * alerta / 100)


def atualizar_configuracao(db: Session, itens: list[dict]) -> dict[str, tuple[int, int]]:
    """Novos prazos valem para chamados abertos a partir de agora (e para mudanças de prioridade)."""
    novos = {**configuracao(db), **{i["prioridade"]: (i["horas"], i["alerta_percentual"]) for i in itens}}
    ordem = ["critica", "alta", "media", "baixa"]
    horas = [novos[p][0] for p in ordem]
    if horas != sorted(horas):
        raise RegraDeNegocio("Prioridades mais altas precisam ter prazos menores ou iguais aos das mais baixas.")
    for prioridade, (h, alerta) in novos.items():
        linha = db.get(ConfiguracaoSla, prioridade) or ConfiguracaoSla(prioridade=prioridade)
        linha.horas, linha.alerta_percentual = h, alerta
        db.add(linha)
    db.commit()
    return configuracao(db)


def verificar(db: Session, momento: datetime | None = None) -> dict[str, int]:
    """Procura chamados perto do vencimento ou vencidos. Roda em segundo plano a cada minuto.

    Cada chamado gera no máximo um alerta e um registro de violação.
    """
    momento = momento or agora()
    alertas = violacoes = 0

    perto = db.scalars(select(Chamado).where(
        Chamado.status.in_(ABERTOS), Chamado.sla_alerta_enviado.is_(False),
        Chamado.sla_alerta_em <= momento, Chamado.prazo_sla > momento))
    for c in perto:
        c.sla_alerta_enviado = True
        restante = int((c.prazo_sla - momento).total_seconds() // 60)
        historico.registrar(db, c.id, "alerta_sla", detalhe=f"Faltam {restante} min para o prazo do SLA.")
        eventos.registrar(db, tipos.SLA_PROXIMO, c, [c.tecnico_id], avisar_equipe=c.tecnico_id is None,
                          minutos_restantes=restante)
        alertas += 1

    vencidos = db.scalars(select(Chamado).where(
        Chamado.status.in_(ABERTOS), Chamado.sla_violado.is_(False), Chamado.prazo_sla <= momento))
    for c in vencidos:
        marcar_violacao(db, c)
        violacoes += 1

    db.commit()
    return {"alertas": alertas, "violacoes": violacoes}


def marcar_violacao(db: Session, c: Chamado) -> None:
    c.sla_violado, c.sla_violado_em, c.sla_alerta_enviado = True, c.prazo_sla, True
    historico.registrar(db, c.id, "sla_violado", detalhe=f"Prazo do SLA ultrapassado ({c.prazo_sla:%d/%m %H:%M} UTC).")
    eventos.registrar(db, tipos.SLA_VENCIDO, c, [c.tecnico_id], avisar_equipe=True)
