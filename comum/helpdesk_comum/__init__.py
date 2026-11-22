"""Biblioteca compartilhada do HelpDesk Pro.

Contém apenas código de infraestrutura que todos os serviços usam do mesmo jeito
(conferência do token, tratamento de erros, cabeçalhos de segurança, logs,
clientes HTTP com timeout e migrações). Nenhuma regra de negócio mora aqui:
cada serviço continua dono dos próprios dados e das próprias regras.
"""
