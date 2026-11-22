"""Criação e validação dos tokens JWT.

Só o serviço de Usuários cria tokens de pessoas (no login). Todos os serviços
validam o token localmente com o segredo compartilhado, sem consultar ninguém:
assim um serviço continua conferindo logins mesmo se Usuários cair.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt

from helpdesk_comum import config

PERFIS = ("solicitante", "tecnico", "admin")
PERFIL_SERVICO = "servico"


class TokenInvalido(Exception):
    pass


@dataclass(frozen=True)
class UsuarioToken:
    """Quem está fazendo a requisição, segundo o token."""
    id: int
    perfil: str
    nome: str

    @property
    def eh_equipe(self) -> bool:
        return self.perfil in ("tecnico", "admin")

    @property
    def eh_admin(self) -> bool:
        return self.perfil == "admin"

    @property
    def eh_servico(self) -> bool:
        return self.perfil == PERFIL_SERVICO


def criar(usuario_id: int, perfil: str, nome: str, minutos: int | None = None) -> tuple[str, datetime]:
    agora = datetime.now(timezone.utc)
    expira = agora + timedelta(minutes=minutos or config.TOKEN_MINUTOS)
    dados = {"sub": str(usuario_id), "perfil": perfil, "nome": nome, "iat": agora, "exp": expira,
             "iss": config.JWT_EMISSOR}
    return jwt.encode(dados, config.jwt_segredo(), algorithm=config.JWT_ALGORITMO), expira


def criar_de_servico(nome_servico: str) -> str:
    """Token curto usado quando um serviço precisa falar com outro sem um usuário por trás
    (por exemplo, Notificações consultando a equipe técnica ao consumir um evento)."""
    token, _ = criar(0, PERFIL_SERVICO, nome_servico, minutos=5)
    return token


def ler(token: str) -> UsuarioToken:
    """Devolve quem é o dono do token, ou lança TokenInvalido."""
    try:
        dados = jwt.decode(
            token, config.jwt_segredo(), algorithms=[config.JWT_ALGORITMO], issuer=config.JWT_EMISSOR,
            options={"require": ["exp", "iat", "sub", "iss"]},
        )
        perfil = dados.get("perfil")
        if perfil not in (*PERFIS, PERFIL_SERVICO):
            raise TokenInvalido("perfil inválido")
        return UsuarioToken(id=int(dados["sub"]), perfil=perfil, nome=str(dados.get("nome", ""))[:120])
    except (jwt.PyJWTError, ValueError, TypeError) as erro:
        raise TokenInvalido() from erro
