import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from helpdesk_comum.banco import DataHora

Perfil = Literal["solicitante", "tecnico", "admin"]
ENTRADA = ConfigDict(extra="forbid", str_strip_whitespace=True)


def _senha_forte(senha: str) -> str:
    if not (re.search(r"[A-Za-z]", senha) and re.search(r"\d", senha)):
        raise ValueError("A senha precisa ter letras e números.")
    return senha


class UsuarioCriar(BaseModel):
    model_config = ENTRADA

    nome: str = Field(min_length=2, max_length=120)
    email: EmailStr
    perfil: Perfil
    setor: str | None = Field(default=None, max_length=80)
    senha: str = Field(min_length=8, max_length=128)

    @field_validator("senha")
    @classmethod
    def senha_forte(cls, senha: str) -> str:
        return _senha_forte(senha)


class UsuarioAtualizar(BaseModel):
    """Campos que o administrador pode alterar. Todos opcionais."""
    model_config = ENTRADA

    nome: str | None = Field(default=None, min_length=2, max_length=120)
    perfil: Perfil | None = None
    setor: str | None = Field(default=None, max_length=80)
    ativo: bool | None = None


class NovaSenha(BaseModel):
    model_config = ENTRADA
    senha: str = Field(min_length=8, max_length=128)

    @field_validator("senha")
    @classmethod
    def senha_forte(cls, senha: str) -> str:
        return _senha_forte(senha)


class TrocaSenha(BaseModel):
    model_config = ENTRADA
    senha_atual: str = Field(min_length=1, max_length=128)
    nova_senha: str = Field(min_length=8, max_length=128)

    @field_validator("nova_senha")
    @classmethod
    def senha_forte(cls, senha: str) -> str:
        return _senha_forte(senha)


class UsuarioSaida(BaseModel):
    """Dados completos: só para o próprio usuário e administradores."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    email: str
    perfil: Perfil
    setor: str | None
    ativo: bool


class UsuarioDetalhado(UsuarioSaida):
    criado_em: DataHora
    ultimo_login: DataHora | None


class UsuarioPublico(BaseModel):
    """Dados que qualquer usuário logado pode ver (sem e-mail)."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    perfil: Perfil
    setor: str | None
    ativo: bool


class Contato(BaseModel):
    """Usado pelo serviço de Notificações para preparar o envio de e-mails."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    email: str
    ativo: bool
