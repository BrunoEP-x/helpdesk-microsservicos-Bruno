from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy.orm import Session

from app import servico
from app.banco import get_db
from app.esquemas import TrocaSenha, UsuarioSaida
from app.limite import limite
from helpdesk_comum import tokens
from helpdesk_comum.auth import NAO_AUTENTICADO, usuario_pessoa
from helpdesk_comum.erros import NaoEncontrado
from helpdesk_comum.tokens import UsuarioToken

router = APIRouter(prefix="/auth", tags=["Autenticação"])


class Login(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    senha: str = Field(min_length=1, max_length=128)


class TokenSaida(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expira_em: datetime
    usuario: UsuarioSaida


@router.post("/login", response_model=TokenSaida)
def login(dados: Login, request: Request, db: Session = Depends(get_db)):
    email = dados.email.lower()
    # Atrás do gateway, o endereço real vem em X-Forwarded-For (o uvicorn roda com --proxy-headers)
    chave = f"{email}|{request.client.host if request.client else '-'}"
    if limite.bloqueado(chave):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Muitas tentativas. Tente de novo em alguns minutos.")

    usuario = servico.autenticar(db, email, dados.senha)
    if usuario is None:
        limite.registrar_falha(chave)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "E-mail ou senha inválidos.")

    limite.limpar(chave)
    token, expira = tokens.criar(usuario.id, usuario.perfil, usuario.nome)
    return TokenSaida(access_token=token, expira_em=expira, usuario=UsuarioSaida.model_validate(usuario))


@router.get("/eu", response_model=UsuarioSaida)
def quem_sou_eu(quem: UsuarioToken = Depends(usuario_pessoa), db: Session = Depends(get_db)):
    """Confere no banco: um usuário desativado deixa de entrar na tela na hora."""
    try:
        usuario = servico.obter(db, quem.id)
    except NaoEncontrado:
        raise NAO_AUTENTICADO
    if not usuario.ativo:
        raise NAO_AUTENTICADO
    return usuario


@router.post("/senha", status_code=204)
def trocar_senha(dados: TrocaSenha, quem: UsuarioToken = Depends(usuario_pessoa), db: Session = Depends(get_db)):
    servico.trocar_propria_senha(db, quem.id, dados.senha_atual, dados.nova_senha)
