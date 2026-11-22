from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from helpdesk_comum.banco import DataHora

Prioridade = Literal["baixa", "media", "alta", "critica"]
Status = Literal["aberto", "em_atendimento", "resolvido", "fechado"]
Categoria = Literal["rede", "hardware", "software", "impressora", "acesso", "seguranca", "outro"]
Impacto = Literal["individual", "setor", "empresa"]
SituacaoSla = Literal["no_prazo", "alerta", "vencido", "cumprido", "violado"]

ENTRADA = ConfigDict(extra="forbid", str_strip_whitespace=True)
SAIDA = ConfigDict(from_attributes=True)


class ChamadoCriar(BaseModel):
    """O solicitante é sempre o usuário logado: não vem no corpo da requisição.

    `prioridade` é opcional: sem ela, vale a prioridade sugerida automaticamente.
    """
    model_config = ENTRADA

    titulo: str = Field(min_length=3, max_length=120)
    descricao: str = Field(min_length=3, max_length=2000)
    categoria: Categoria = "outro"
    impacto: Impacto = "individual"
    prioridade: Prioridade | None = None
    ativo_id: int | None = Field(default=None, gt=0)


class PedidoSugestao(BaseModel):
    model_config = ENTRADA

    titulo: str = Field(default="", max_length=120)
    descricao: str = Field(default="", max_length=2000)
    categoria: Categoria = "outro"
    impacto: Impacto = "individual"


class SugestaoSaida(BaseModel):
    prioridade: Prioridade
    pontos: int
    motivos: list[str]
    prazo_horas: int


class Atribuicao(BaseModel):
    model_config = ENTRADA
    tecnico_id: int = Field(gt=0)


class MudancaStatus(BaseModel):
    model_config = ENTRADA
    status: Status
    solucao: str | None = Field(default=None, min_length=3, max_length=2000)


class MudancaPrioridade(BaseModel):
    model_config = ENTRADA
    prioridade: Prioridade
    motivo: str | None = Field(default=None, max_length=300)


class ComentarioCriar(BaseModel):
    """O autor é sempre o usuário logado."""
    model_config = ENTRADA
    texto: str = Field(min_length=1, max_length=2000)
    interno: bool = False


class ComentarioSaida(BaseModel):
    model_config = SAIDA

    id: int
    autor_id: int
    autor_nome: str
    texto: str
    interno: bool
    criado_em: DataHora


class ChamadoSaida(BaseModel):
    model_config = SAIDA

    id: int
    titulo: str
    descricao: str
    categoria: Categoria
    impacto: Impacto
    prioridade: Prioridade
    prioridade_sugerida: Prioridade
    prioridade_origem: str
    status: Status
    solicitante_id: int
    solicitante_nome: str
    tecnico_id: int | None
    tecnico_nome: str | None
    ativo_id: int | None
    ativo_descricao: str | None
    criado_em: DataHora
    atribuido_em: DataHora | None
    resolvido_em: DataHora | None
    fechado_em: DataHora | None
    solucao: str | None
    prazo_sla: DataHora
    sla_situacao: SituacaoSla
    sla_restante_minutos: int | None
    sla_violado: bool
    sla_violado_em: DataHora | None
    avaliacao_nota: int | None


class ChamadoDetalhe(ChamadoSaida):
    comentarios: list[ComentarioSaida] = []


class HistoricoSaida(BaseModel):
    model_config = SAIDA

    id: int
    acao: str
    campo: str | None
    valor_anterior: str | None
    valor_novo: str | None
    detalhe: str | None
    autor_id: int | None
    autor_nome: str
    criado_em: DataHora


class AvaliacaoCriar(BaseModel):
    model_config = ENTRADA
    nota: int = Field(ge=1, le=5)
    comentario: str | None = Field(default=None, max_length=1000)


class AvaliacaoSaida(BaseModel):
    model_config = SAIDA

    id: int
    chamado_id: int
    nota: int
    comentario: str | None
    tecnico_id: int | None
    tecnico_nome: str | None
    criado_em: DataHora


class ItemSla(BaseModel):
    model_config = ENTRADA
    prioridade: Prioridade
    horas: int = Field(ge=1, le=720)
    alerta_percentual: int = Field(ge=10, le=95)


class DesempenhoTecnico(BaseModel):
    tecnico_id: int
    tecnico_nome: str
    atribuidos: int
    em_aberto: int
    resolvidos: int
    tempo_medio_horas: float | None
    violacoes_sla: int
    avaliacao_media: float | None
    avaliacoes: int


class PontoSerie(BaseModel):
    dia: str
    abertos: int
    resolvidos: int


class Painel(BaseModel):
    total: int
    por_status: dict[str, int]
    atrasados: int
    abertos: int
    em_andamento: int
    concluidos: int
    por_prioridade: dict[str, int]
    por_categoria: dict[str, int]
    tempo_medio_atendimento_horas: float | None
    tempo_medio_primeira_resposta_horas: float | None
    sla_cumprido_percentual: float | None
    violacoes_sla: int
    em_alerta: int
    satisfacao_media: float | None
    serie: list[PontoSerie]
    desempenho_tecnicos: list[DesempenhoTecnico]
    gerado_em: datetime


class RelatorioSatisfacao(BaseModel):
    media: float | None
    total: int
    distribuicao: dict[str, int]
    por_tecnico: list[dict]
    recentes: list[AvaliacaoSaida]
