from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from helpdesk_comum.banco import DataHora

TipoAtivo = Literal["computador", "notebook", "impressora", "monitor", "periferico", "rede", "outro"]
Situacao = Literal["em_uso", "estoque", "manutencao", "descartado"]
ENTRADA = ConfigDict(extra="forbid", str_strip_whitespace=True)


class AtivoCriar(BaseModel):
    model_config = ENTRADA

    patrimonio: str = Field(min_length=3, max_length=30, pattern=r"^[A-Za-z0-9-]+$")
    tipo: TipoAtivo
    descricao: str = Field(min_length=2, max_length=200)
    setor: str = Field(min_length=2, max_length=80)
    marca: str | None = Field(default=None, max_length=60)
    modelo: str | None = Field(default=None, max_length=80)
    numero_serie: str | None = Field(default=None, max_length=80)
    situacao: Situacao = "em_uso"
    responsavel_id: int | None = Field(default=None, gt=0)
    observacoes: str | None = Field(default=None, max_length=1000)


class AtivoAtualizar(BaseModel):
    model_config = ENTRADA

    descricao: str | None = Field(default=None, min_length=2, max_length=200)
    setor: str | None = Field(default=None, min_length=2, max_length=80)
    marca: str | None = Field(default=None, max_length=60)
    modelo: str | None = Field(default=None, max_length=80)
    numero_serie: str | None = Field(default=None, max_length=80)
    situacao: Situacao | None = None
    responsavel_id: int | None = Field(default=None, ge=0)  # 0 = remover o responsável
    observacoes: str | None = Field(default=None, max_length=1000)


class AtivoSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patrimonio: str
    tipo: TipoAtivo
    descricao: str
    setor: str
    marca: str | None
    modelo: str | None
    numero_serie: str | None
    situacao: Situacao
    responsavel_id: int | None
    responsavel_nome: str | None
    observacoes: str | None
    criado_em: DataHora
    atualizado_em: DataHora


class Resumo(BaseModel):
    total: int
    por_tipo: dict[str, int]
    por_situacao: dict[str, int]
