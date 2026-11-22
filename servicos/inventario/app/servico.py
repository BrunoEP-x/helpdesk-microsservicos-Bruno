"""Regras do serviço de inventário."""
from sqlalchemy.orm import Session

from app import repositorio
from app.esquemas import AtivoAtualizar, AtivoCriar
from app.modelos import Ativo
from helpdesk_comum.clientes import ClienteServico
from helpdesk_comum.erros import NaoEncontrado, RegraDeNegocio


def _nome_do_responsavel(usuarios: ClienteServico, token: str, usuario_id: int) -> str:
    """Confere no serviço de Usuários se a pessoa existe e está ativa."""
    usuario = usuarios.get(f"/usuarios/{usuario_id}", token)
    if not usuario.get("ativo", True):
        raise RegraDeNegocio(f"O usuário {usuario_id} está desativado.")
    return usuario["nome"]


def criar(db: Session, dados: AtivoCriar, usuarios: ClienteServico, token: str) -> Ativo:
    if repositorio.buscar_por_patrimonio(db, dados.patrimonio):
        raise RegraDeNegocio("Já existe um ativo com este patrimônio.")
    ativo = Ativo(**dados.model_dump())
    if dados.responsavel_id:
        ativo.responsavel_nome = _nome_do_responsavel(usuarios, token, dados.responsavel_id)
    return repositorio.salvar(db, ativo)


def obter(db: Session, ativo_id: int) -> Ativo:
    ativo = repositorio.buscar_por_id(db, ativo_id)
    if ativo is None:
        raise NaoEncontrado(f"Ativo {ativo_id} não encontrado.")
    return ativo


def listar(db: Session, **filtros) -> list[Ativo]:
    return repositorio.listar(db, **filtros)


def atualizar(db: Session, ativo_id: int, dados: AtivoAtualizar, usuarios: ClienteServico, token: str) -> Ativo:
    ativo = obter(db, ativo_id)
    mudancas = dados.model_dump(exclude_unset=True)
    if "responsavel_id" in mudancas:
        novo = mudancas.pop("responsavel_id")
        if not novo:
            ativo.responsavel_id, ativo.responsavel_nome = None, None
        elif novo != ativo.responsavel_id:
            ativo.responsavel_nome = _nome_do_responsavel(usuarios, token, novo)
            ativo.responsavel_id = novo
    for campo, valor in mudancas.items():
        setattr(ativo, campo, valor)
    return repositorio.salvar(db, ativo)


def resumo(db: Session) -> dict:
    from app.modelos import Ativo as A
    por_tipo = repositorio.contar_por(db, A.tipo)
    return {"total": sum(por_tipo.values()), "por_tipo": por_tipo, "por_situacao": repositorio.contar_por(db, A.situacao)}
