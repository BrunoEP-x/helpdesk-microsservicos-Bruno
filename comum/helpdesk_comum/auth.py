"""Dependências do FastAPI para exigir login e perfil em qualquer serviço."""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from helpdesk_comum import tokens
from helpdesk_comum.tokens import UsuarioToken

esquema = HTTPBearer(auto_error=False)

NAO_AUTENTICADO = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Faça login para continuar.",
    headers={"WWW-Authenticate": "Bearer"},
)
SEM_PERMISSAO = HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Você não tem permissão para esta ação.")


def token_bruto(credenciais: HTTPAuthorizationCredentials | None = Depends(esquema)) -> str:
    """O token como veio, para ser repassado a outros serviços."""
    if credenciais is None or credenciais.scheme.lower() != "bearer":
        raise NAO_AUTENTICADO
    return credenciais.credentials


def usuario_atual(token: str = Depends(token_bruto)) -> UsuarioToken:
    try:
        usuario = tokens.ler(token)
    except tokens.TokenInvalido:
        raise NAO_AUTENTICADO
    return usuario


def usuario_pessoa(usuario: UsuarioToken = Depends(usuario_atual)) -> UsuarioToken:
    """Como usuario_atual, mas recusa tokens de serviço (rotas usadas só por pessoas)."""
    if usuario.eh_servico:
        raise SEM_PERMISSAO
    return usuario


def exigir_perfil(*perfis: str):
    """Libera a rota só para os perfis informados."""
    def verificar(usuario: UsuarioToken = Depends(usuario_atual)) -> UsuarioToken:
        if usuario.perfil not in perfis:
            raise SEM_PERMISSAO
        return usuario
    return verificar
