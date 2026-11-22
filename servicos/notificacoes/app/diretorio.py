"""Consulta ao serviço de Usuários com um token de serviço.

Ao consumir um evento não há usuário logado, então o serviço se identifica
com um token próprio (perfil "servico", válido por 5 minutos).
"""
import time

from app.config import USUARIOS_URL
from helpdesk_comum import tokens
from helpdesk_comum.clientes import ClienteServico


class DiretorioUsuarios:
    def __init__(self, cliente: ClienteServico | None = None, cache_segundos: int = 60):
        self.cliente = cliente or ClienteServico("Usuários", USUARIOS_URL)
        self.cache_segundos = cache_segundos
        self._equipe: tuple[float, list[int]] | None = None

    def _token(self) -> str:
        return tokens.criar_de_servico("notificacoes")

    def equipe(self) -> list[int]:
        """Ids de técnicos e administradores ativos (com cache curto)."""
        if self._equipe and time.monotonic() - self._equipe[0] < self.cache_segundos:
            return self._equipe[1]
        token = self._token()
        ids = [u["id"] for perfil in ("tecnico", "admin")
               for u in self.cliente.get("/usuarios", token, params={"perfil": perfil, "ativos": "true"})]
        self._equipe = (time.monotonic(), ids)
        return ids

    def email(self, usuario_id: int) -> str | None:
        contato = self.cliente.get(f"/usuarios/{usuario_id}/contato", self._token())
        return contato["email"] if contato.get("ativo") else None
