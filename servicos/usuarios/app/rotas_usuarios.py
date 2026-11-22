from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app import servico
from app.banco import get_db
from app.esquemas import (
    Contato, NovaSenha, Perfil, UsuarioAtualizar, UsuarioCriar, UsuarioDetalhado, UsuarioPublico, UsuarioSaida,
)
from helpdesk_comum.auth import exigir_perfil, usuario_atual
from helpdesk_comum.tokens import UsuarioToken

router = APIRouter(prefix="/usuarios", tags=["Usuários"])
so_admin = exigir_perfil("admin")


@router.post("", response_model=UsuarioSaida, status_code=201, dependencies=[Depends(so_admin)])
def criar_usuario(dados: UsuarioCriar, db: Session = Depends(get_db)):
    return servico.criar(db, dados)


@router.get("", response_model=list[UsuarioPublico], dependencies=[Depends(usuario_atual)])
def listar_usuarios(perfil: Perfil | None = None, ativos: bool = False,
                    ids: list[int] | None = Query(None, max_length=200), db: Session = Depends(get_db)):
    """Lista pública (sem e-mail). `ids` permite buscar vários de uma vez (evita N chamadas)."""
    return servico.listar(db, perfil, ativos, ids)


@router.get("/detalhes", response_model=list[UsuarioDetalhado], dependencies=[Depends(so_admin)])
def listar_detalhes(perfil: Perfil | None = None, db: Session = Depends(get_db)):
    """Lista completa, com e-mail e situação, para a tela de gestão de usuários."""
    return servico.listar(db, perfil)


@router.get("/{usuario_id}", response_model=UsuarioPublico, dependencies=[Depends(usuario_atual)])
def obter_usuario(usuario_id: int, db: Session = Depends(get_db)):
    return servico.obter(db, usuario_id)


@router.get("/{usuario_id}/contato", response_model=Contato,
            dependencies=[Depends(exigir_perfil("admin", "servico"))])
def obter_contato(usuario_id: int, db: Session = Depends(get_db)):
    """E-mail do usuário: só administradores e outros serviços (token de serviço)."""
    return servico.obter(db, usuario_id)


@router.patch("/{usuario_id}", response_model=UsuarioSaida)
def atualizar_usuario(usuario_id: int, dados: UsuarioAtualizar, quem: UsuarioToken = Depends(so_admin),
                      db: Session = Depends(get_db)):
    return servico.atualizar(db, usuario_id, dados, quem)


@router.put("/{usuario_id}/senha", status_code=204, dependencies=[Depends(so_admin)])
def redefinir_senha(usuario_id: int, dados: NovaSenha, db: Session = Depends(get_db)):
    servico.redefinir_senha(db, usuario_id, dados.senha)
