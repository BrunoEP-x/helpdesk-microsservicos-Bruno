from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Categoria = Literal["rede", "hardware", "software", "impressora", "acesso", "seguranca", "outro"]
ENTRADA = ConfigDict(extra="forbid", str_strip_whitespace=True)


class PerguntaEntrada(BaseModel):
    model_config = ENTRADA
    texto: str = Field(min_length=1, max_length=500)


class ArtigoResumo(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    titulo: str
    categoria: str


class ArtigoSaida(ArtigoResumo):
    palavras_chave: str
    resposta: str
    ativo: bool
    consultas: int
    util_sim: int
    util_nao: int


class ArtigoEntrada(BaseModel):
    model_config = ENTRADA
    titulo: str = Field(min_length=3, max_length=120)
    categoria: Categoria
    palavras_chave: str = Field(min_length=3, max_length=600)
    resposta: str = Field(min_length=10, max_length=4000)
    ativo: bool = True


class ChamadoSugerido(BaseModel):
    titulo: str
    descricao: str
    categoria: str


class RespostaAssistente(BaseModel):
    pergunta_id: int
    tipo: str
    mensagem: str
    passos: list[str]
    artigo: ArtigoResumo | None
    sugestoes: list[ArtigoResumo]
    abrir_chamado: bool
    chamado_sugerido: ChamadoSugerido | None


class Feedback(BaseModel):
    model_config = ENTRADA
    util: bool


class Estatisticas(BaseModel):
    perguntas: int
    respondidas: int
    uteis: int
    nao_uteis: int
    sem_resposta_recentes: list[str]
    mais_consultados: list[ArtigoSaida]
