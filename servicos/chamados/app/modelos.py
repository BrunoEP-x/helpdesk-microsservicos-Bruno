"""Tabelas do serviço de Chamados.

Não há chaves estrangeiras para usuários ou equipamentos: eles moram nos bancos
de outros serviços. Guardamos o id e uma cópia do nome (snapshot) para que as
telas de chamados continuem funcionando mesmo se Usuários ou Inventário caírem.
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.banco import Base
from helpdesk_comum.banco import agora

ABERTOS = ("aberto", "em_atendimento")
ENCERRADOS = ("resolvido", "fechado")


class Chamado(Base):
    __tablename__ = "chamados"
    __table_args__ = (
        Index("ix_chamados_status_prazo", "status", "prazo_sla"),
        Index("ix_chamados_solicitante", "solicitante_id"),
        Index("ix_chamados_tecnico", "tecnico_id"),
        Index("ix_chamados_criado_em", "criado_em"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    titulo: Mapped[str] = mapped_column(String(120))
    descricao: Mapped[str] = mapped_column(Text)
    categoria: Mapped[str] = mapped_column(String(20), default="outro")
    impacto: Mapped[str] = mapped_column(String(20), default="individual")
    prioridade: Mapped[str] = mapped_column(String(10))
    prioridade_sugerida: Mapped[str] = mapped_column(String(10))
    prioridade_origem: Mapped[str] = mapped_column(String(20), default="automatica")  # automatica | informada | ajuste_manual
    status: Mapped[str] = mapped_column(String(20), default="aberto")

    solicitante_id: Mapped[int]
    solicitante_nome: Mapped[str] = mapped_column(String(120), default="")
    tecnico_id: Mapped[int | None] = mapped_column(nullable=True)
    tecnico_nome: Mapped[str | None] = mapped_column(String(120), nullable=True)
    ativo_id: Mapped[int | None] = mapped_column(nullable=True)
    ativo_descricao: Mapped[str | None] = mapped_column(String(240), nullable=True)

    criado_em: Mapped[datetime] = mapped_column(DateTime)
    atribuido_em: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    resolvido_em: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    fechado_em: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    solucao: Mapped[str | None] = mapped_column(Text, nullable=True)

    # SLA
    prazo_sla: Mapped[datetime] = mapped_column(DateTime)
    sla_alerta_em: Mapped[datetime] = mapped_column(DateTime)
    sla_alerta_enviado: Mapped[bool] = mapped_column(Boolean, default=False)
    sla_violado: Mapped[bool] = mapped_column(Boolean, default=False)
    sla_violado_em: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    comentarios: Mapped[list["Comentario"]] = relationship(
        back_populates="chamado", order_by="Comentario.id", cascade="all, delete-orphan"
    )
    avaliacao: Mapped["Avaliacao | None"] = relationship(back_populates="chamado", uselist=False)

    # ---- valores calculados (aparecem na API) ----
    @property
    def sla_situacao(self) -> str:
        if self.status in ENCERRADOS:
            return "violado" if self.sla_violado else "cumprido"
        momento = agora()
        if momento > self.prazo_sla:
            return "vencido"
        if momento >= self.sla_alerta_em:
            return "alerta"
        return "no_prazo"

    @property
    def sla_restante_minutos(self) -> int | None:
        if self.status in ENCERRADOS:
            return None
        return int((self.prazo_sla - agora()).total_seconds() // 60)

    @property
    def avaliacao_nota(self) -> int | None:
        return self.avaliacao.nota if self.avaliacao else None


class Comentario(Base):
    __tablename__ = "comentarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    chamado_id: Mapped[int] = mapped_column(ForeignKey("chamados.id"), index=True)
    autor_id: Mapped[int]
    autor_nome: Mapped[str] = mapped_column(String(120), default="")
    texto: Mapped[str] = mapped_column(Text)
    interno: Mapped[bool] = mapped_column(Boolean, default=False)  # nota só para a equipe técnica
    criado_em: Mapped[datetime] = mapped_column(DateTime)

    chamado: Mapped[Chamado] = relationship(back_populates="comentarios")


class Historico(Base):
    """Auditoria: cada mudança em um chamado vira uma linha, nunca é apagada."""
    __tablename__ = "historico"

    id: Mapped[int] = mapped_column(primary_key=True)
    chamado_id: Mapped[int] = mapped_column(ForeignKey("chamados.id"), index=True)
    acao: Mapped[str] = mapped_column(String(40))
    campo: Mapped[str | None] = mapped_column(String(40), nullable=True)
    valor_anterior: Mapped[str | None] = mapped_column(String(240), nullable=True)
    valor_novo: Mapped[str | None] = mapped_column(String(240), nullable=True)
    detalhe: Mapped[str | None] = mapped_column(String(500), nullable=True)
    autor_id: Mapped[int | None] = mapped_column(nullable=True)  # None = o próprio sistema (ex.: SLA)
    autor_nome: Mapped[str] = mapped_column(String(120), default="Sistema")
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora)


class Avaliacao(Base):
    __tablename__ = "avaliacoes"

    id: Mapped[int] = mapped_column(primary_key=True)
    chamado_id: Mapped[int] = mapped_column(ForeignKey("chamados.id"), unique=True)
    nota: Mapped[int] = mapped_column(Integer)
    comentario: Mapped[str | None] = mapped_column(Text, nullable=True)
    tecnico_id: Mapped[int | None] = mapped_column(nullable=True, index=True)
    tecnico_nome: Mapped[str | None] = mapped_column(String(120), nullable=True)
    autor_id: Mapped[int]
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora)

    chamado: Mapped[Chamado] = relationship(back_populates="avaliacao")


class ConfiguracaoSla(Base):
    """Prazos por prioridade, configuráveis pelo administrador."""
    __tablename__ = "configuracao_sla"

    prioridade: Mapped[str] = mapped_column(String(10), primary_key=True)
    horas: Mapped[int] = mapped_column(Integer)
    alerta_percentual: Mapped[int] = mapped_column(Integer)  # % do prazo consumido que dispara o alerta
    atualizado_em: Mapped[datetime] = mapped_column(DateTime, default=agora, onupdate=agora)


class EventoPendente(Base):
    """Tabela de saída (padrão Outbox).

    O evento é gravado na MESMA transação da mudança do chamado. Uma tarefa em
    segundo plano publica na fila depois. Assim, se a fila ou o serviço de
    Notificações estiverem fora do ar, o chamado é aberto do mesmo jeito e
    nenhum aviso se perde.
    """
    __tablename__ = "eventos_pendentes"
    __table_args__ = (Index("ix_eventos_publicado", "publicado_em"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tipo: Mapped[str] = mapped_column(String(40))
    conteudo: Mapped[str] = mapped_column(Text)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora)
    publicado_em: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    tentativas: Mapped[int] = mapped_column(Integer, default=0)
