"""Canal de e-mail (preparado, desligado por padrão).

Com SMTP_HOST definido, cada aviso também é enviado por e-mail. O endereço é
buscado no serviço de Usuários (único dono dos e-mails). Falhas de envio só
geram log: o aviso na tela já foi gravado.
"""
import logging
import smtplib
from email.message import EmailMessage

from app import config

log = logging.getLogger("helpdesk.email")


class CanalEmail:
    def __init__(self, diretorio):
        self.diretorio = diretorio

    @property
    def ativo(self) -> bool:
        return bool(config.SMTP_HOST)

    def enviar(self, destinatario_id: int, titulo: str, mensagem: str) -> bool:
        if not self.ativo:
            return False
        try:
            endereco = self.diretorio.email(destinatario_id)
            if not endereco:
                return False
            msg = EmailMessage()
            msg["Subject"], msg["From"], msg["To"] = f"[HelpDesk Pro] {titulo}", config.SMTP_REMETENTE, endereco
            msg.set_content(f"{mensagem}\n\nAcesse o HelpDesk Pro para acompanhar.")
            with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORTA, timeout=5) as smtp:
                smtp.starttls()
                if config.SMTP_USUARIO:
                    smtp.login(config.SMTP_USUARIO, config.SMTP_SENHA)
                smtp.send_message(msg)
            return True
        except Exception as erro:
            log.warning("falha ao enviar e-mail para o usuário %s: %s", destinatario_id, erro)
            return False
