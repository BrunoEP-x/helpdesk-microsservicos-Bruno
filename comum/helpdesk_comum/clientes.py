"""Cliente HTTP para um serviço chamar outro.

Regras aplicadas em todas as chamadas entre serviços:
- tempo limite (TIMEOUT_HTTP, 3 s por padrão): nunca espera para sempre;
- repassa o token do usuário (cabeçalho Authorization) e o X-Request-ID;
- traduz falhas de rede e respostas 5xx para ServicoIndisponivel (HTTP 503),
  com uma mensagem clara de qual serviço falhou;
- traduz 404 para NaoEncontrado.
"""
import logging

import httpx

from helpdesk_comum import config
from helpdesk_comum.erros import NaoEncontrado, ServicoIndisponivel, SemPermissao
from helpdesk_comum.http import id_requisicao

log = logging.getLogger("helpdesk.clientes")


class ClienteServico:
    def __init__(self, nome: str, url_base: str, timeout: float | None = None,
                 transporte: httpx.BaseTransport | None = None):
        self.nome = nome
        self.url_base = url_base.rstrip("/")
        self.timeout = timeout if timeout is not None else config.TIMEOUT_HTTP
        self.transporte = transporte  # permite simular o outro serviço nos testes

    def get(self, caminho: str, token: str, params: dict | None = None) -> dict | list:
        cabecalhos = {"Authorization": f"Bearer {token}", "X-Request-ID": id_requisicao.get()}
        try:
            with httpx.Client(timeout=self.timeout, transport=self.transporte) as cliente:
                resposta = cliente.get(self.url_base + caminho, headers=cabecalhos, params=params)
        except httpx.TimeoutException:
            log.warning("tempo esgotado chamando %s %s", self.nome, caminho)
            raise ServicoIndisponivel(f"O serviço de {self.nome} não respondeu a tempo. Tente novamente em instantes.")
        except httpx.HTTPError:
            log.warning("serviço %s fora do ar (%s)", self.nome, caminho)
            raise ServicoIndisponivel(f"O serviço de {self.nome} está indisponível no momento. Tente novamente em instantes.")

        if resposta.status_code == 404:
            raise NaoEncontrado(_detalhe(resposta, "Registro não encontrado."))
        if resposta.status_code in (401, 403):
            raise SemPermissao(f"O serviço de {self.nome} recusou o acesso.")
        if resposta.status_code >= 500:
            raise ServicoIndisponivel(f"O serviço de {self.nome} está com problemas no momento.")
        if resposta.status_code >= 400:
            raise NaoEncontrado(_detalhe(resposta, "Registro inválido."))
        return resposta.json()


def _detalhe(resposta: httpx.Response, padrao: str) -> str:
    try:
        detalhe = resposta.json().get("detail")
        return detalhe if isinstance(detalhe, str) else padrao
    except ValueError:
        return padrao
