from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import servico
from app.banco import get_db
from app.esquemas import ArtigoEntrada, ArtigoSaida, Estatisticas, Feedback, PerguntaEntrada, RespostaAssistente
from helpdesk_comum.auth import exigir_perfil, usuario_pessoa
from helpdesk_comum.tokens import UsuarioToken

router = APIRouter(prefix="/assistente", tags=["Assistente"])
so_admin = exigir_perfil("admin")


@router.post("/perguntar", response_model=RespostaAssistente)
def perguntar(dados: PerguntaEntrada, usuario: UsuarioToken = Depends(usuario_pessoa), db: Session = Depends(get_db)):
    return servico.perguntar(db, dados.texto, usuario)


@router.post("/artigos/{artigo_id}/consultar", response_model=RespostaAssistente)
def consultar_artigo(artigo_id: int, usuario: UsuarioToken = Depends(usuario_pessoa), db: Session = Depends(get_db)):
    return servico.ver_artigo(db, artigo_id, usuario)


@router.post("/perguntas/{pergunta_id}/feedback", status_code=204)
def feedback(pergunta_id: int, dados: Feedback, usuario: UsuarioToken = Depends(usuario_pessoa),
             db: Session = Depends(get_db)):
    servico.registrar_feedback(db, pergunta_id, dados.util, usuario)


@router.get("/artigos", response_model=list[ArtigoSaida])
def listar_artigos(usuario: UsuarioToken = Depends(usuario_pessoa), db: Session = Depends(get_db)):
    return servico.listar_artigos(db, usuario)


@router.post("/artigos", response_model=ArtigoSaida, status_code=201, dependencies=[Depends(so_admin)])
def criar_artigo(dados: ArtigoEntrada, db: Session = Depends(get_db)):
    return servico.salvar_artigo(db, dados)


@router.put("/artigos/{artigo_id}", response_model=ArtigoSaida, dependencies=[Depends(so_admin)])
def editar_artigo(artigo_id: int, dados: ArtigoEntrada, db: Session = Depends(get_db)):
    return servico.salvar_artigo(db, dados, artigo_id)


@router.get("/estatisticas", response_model=Estatisticas, dependencies=[Depends(so_admin)])
def estatisticas(db: Session = Depends(get_db)):
    return servico.estatisticas(db)
