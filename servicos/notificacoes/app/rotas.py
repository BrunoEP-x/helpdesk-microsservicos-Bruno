from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app import servico
from app.banco import get_db
from app.esquemas import Contagem, NotificacaoSaida
from helpdesk_comum.auth import usuario_pessoa
from helpdesk_comum.tokens import UsuarioToken

router = APIRouter(prefix="/notificacoes", tags=["Notificações"])


@router.get("", response_model=list[NotificacaoSaida])
def minhas_notificacoes(nao_lidas: bool = False, limite: int = Query(50, ge=1, le=200),
                        usuario: UsuarioToken = Depends(usuario_pessoa), db: Session = Depends(get_db)):
    """Cada usuário vê só as próprias notificações, das mais novas para as mais antigas."""
    return servico.listar(db, usuario.id, nao_lidas, limite)


@router.get("/contagem", response_model=Contagem)
def contagem(usuario: UsuarioToken = Depends(usuario_pessoa), db: Session = Depends(get_db)):
    return {"nao_lidas": servico.contar_nao_lidas(db, usuario.id)}


@router.patch("/{notificacao_id}/lida", response_model=NotificacaoSaida)
def marcar_lida(notificacao_id: int, usuario: UsuarioToken = Depends(usuario_pessoa), db: Session = Depends(get_db)):
    return servico.marcar_lida(db, notificacao_id, usuario.id)


@router.post("/lidas")
def marcar_todas(usuario: UsuarioToken = Depends(usuario_pessoa), db: Session = Depends(get_db)):
    return {"marcadas": servico.marcar_todas(db, usuario.id)}
