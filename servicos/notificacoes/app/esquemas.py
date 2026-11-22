from pydantic import BaseModel, ConfigDict

from helpdesk_comum.banco import DataHora


class NotificacaoSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tipo: str
    destinatario_id: int
    chamado_id: int | None
    titulo: str
    mensagem: str
    lida: bool
    criada_em: DataHora


class Contagem(BaseModel):
    nao_lidas: int
