"""Regras do serviço de usuários."""
from sqlalchemy.orm import Session

from app import repositorio, senhas
from app.esquemas import UsuarioAtualizar, UsuarioCriar
from app.modelos import Usuario
from helpdesk_comum.banco import agora
from helpdesk_comum.erros import NaoEncontrado, RegraDeNegocio
from helpdesk_comum.tokens import UsuarioToken


def criar(db: Session, dados: UsuarioCriar) -> Usuario:
    email = dados.email.lower()
    if repositorio.buscar_por_email(db, email):
        raise RegraDeNegocio("Já existe um usuário com este e-mail.")
    usuario = Usuario(nome=dados.nome, email=email, perfil=dados.perfil, setor=dados.setor,
                      senha_hash=senhas.gerar_hash(dados.senha))
    return repositorio.salvar(db, usuario)


def autenticar(db: Session, email: str, senha: str) -> Usuario | None:
    usuario = repositorio.buscar_por_email(db, email.lower())
    # Confere a senha mesmo sem usuário, para o tempo de resposta não revelar se o e-mail existe
    senha_ok = senhas.conferir(senha, usuario.senha_hash if usuario else senhas.HASH_FALSO)
    if not usuario or not senha_ok or not usuario.ativo:
        return None
    usuario.ultimo_login = agora()
    return repositorio.salvar(db, usuario)


def obter(db: Session, usuario_id: int) -> Usuario:
    usuario = repositorio.buscar_por_id(db, usuario_id)
    if usuario is None:
        raise NaoEncontrado(f"Usuário {usuario_id} não encontrado.")
    return usuario


def listar(db: Session, perfil: str | None = None, somente_ativos: bool = False,
           ids: list[int] | None = None) -> list[Usuario]:
    return repositorio.listar(db, perfil, somente_ativos, ids)


def atualizar(db: Session, usuario_id: int, dados: UsuarioAtualizar, quem: UsuarioToken) -> Usuario:
    usuario = obter(db, usuario_id)
    mudancas = dados.model_dump(exclude_unset=True)
    deixa_de_ser_admin = usuario.perfil == "admin" and (
        mudancas.get("perfil", "admin") != "admin" or mudancas.get("ativo") is False)
    if deixa_de_ser_admin:
        if usuario.id == quem.id:
            raise RegraDeNegocio("Você não pode remover o seu próprio acesso de administrador.")
        if repositorio.contar_admins_ativos(db) <= 1:
            raise RegraDeNegocio("O sistema precisa de pelo menos um administrador ativo.")
    for campo, valor in mudancas.items():
        setattr(usuario, campo, valor)
    return repositorio.salvar(db, usuario)


def redefinir_senha(db: Session, usuario_id: int, senha: str) -> None:
    usuario = obter(db, usuario_id)
    usuario.senha_hash = senhas.gerar_hash(senha)
    repositorio.salvar(db, usuario)


def trocar_propria_senha(db: Session, usuario_id: int, atual: str, nova: str) -> None:
    usuario = obter(db, usuario_id)
    if not senhas.conferir(atual, usuario.senha_hash):
        raise RegraDeNegocio("A senha atual não confere.")
    usuario.senha_hash = senhas.gerar_hash(nova)
    repositorio.salvar(db, usuario)
