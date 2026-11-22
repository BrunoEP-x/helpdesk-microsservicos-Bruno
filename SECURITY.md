# Segurança

O HelpDesk Pro mantém (e amplia) todas as proteções do monólito original, agora em cada microsserviço.

## O que está protegido

| Risco | Proteção |
|---|---|
| Acesso sem login | **Todo serviço confere o token** (JWT HS256, emissor, validade e algoritmo fixos; `alg: none` recusado). Só `/auth/login`, `/saude` e a tela são públicos. |
| Acesso direto aos serviços | **Só o gateway publica porta** (`127.0.0.1:8000`). Serviços, bancos e Redis ficam numa rede Docker interna, sem portas publicadas e sem saída para a internet. |
| Segredo no código | O segredo do JWT vem do `.env` ou de um volume gerado na primeira subida (somente leitura para os serviços). Nunca está no código ou na imagem. |
| Chamada entre serviços sem identidade | O token do usuário é **repassado** (`Authorization`) em toda chamada HTTP entre serviços; o serviço chamado aplica as próprias permissões. Quando não há usuário (consumo de eventos), o serviço usa um **token de serviço** de 5 minutos, aceito só nas rotas que o permitem. |
| Senhas vazadas do banco | Hash **scrypt** com sal aleatório; a senha nunca é salva nem devolvida. Regras de senha forte. |
| Adivinhar senhas | Bloqueio temporário após 5 erros (por e-mail e IP real, repassado pelo gateway); contagem no Redis, com reserva em memória. Mesma mensagem e mesmo tempo para e-mail inexistente e senha errada. |
| Ver ou mexer no que não é seu | Permissões por perfil em cada serviço: solicitante só vê os próprios chamados, histórico e avisos; só a equipe atribui, resolve e ajusta prioridade; só admin gerencia usuários, SLA e base do assistente; notas internas escondidas do solicitante. |
| Agir em nome de outra pessoa | Solicitante, autor de comentário e avaliador vêm do token, nunca do corpo. Campos extras são recusados (422). |
| Descobrir o que existe | Chamado alheio responde 404. Lista de usuários sem e-mail; e-mail só para admin e serviços. |
| Usuário desligado | Admin desativa: login bloqueado e a tela perde o acesso na hora (o token restante expira em até `TOKEN_MINUTOS`). O sistema impede remover o último administrador. |
| XSS na tela | Todo texto da API passa por `esc()`; sem scripts ou estilos embutidos, sem `eval`; CSP só permite arquivos do próprio servidor (teste automatizado confere). |
| Injeção de fórmulas no CSV | Células que começam com `=`, `+`, `-`, `@` são prefixadas com apóstrofo. |
| Clickjacking e afins | `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`, `Cross-Origin-Opener-Policy`, `Cache-Control: no-store` em respostas autenticadas. |
| Dados enormes | Limites em todos os campos e corpo limitado a 64 KB (no gateway e em cada serviço). |
| SQL injection | Acesso ao banco só pelo SQLAlchemy, com parâmetros. |
| Erros que vazam detalhes | Tratamento centralizado: erros de banco e erros inesperados respondem com mensagem genérica; detalhes só no log. |
| Rastreabilidade | Logs em JSON com o `X-Request-ID` criado no gateway e repassado a todos os serviços; histórico de auditoria imutável nos chamados. |
| Contêineres | Usuário sem privilégios (uid 10001), sistema de arquivos somente leitura, `cap_drop: ALL`, `no-new-privileges`. |
| Dependências vulneráveis | Versões fixas, `pip-audit` por serviço no GitHub Actions e Dependabot semanal (pip, Docker e Actions). |

## Antes de usar em produção

- Defina `JWT_SEGREDO` (≥ 32 caracteres aleatórios) num cofre de segredos, ou mantenha o volume `segredos` protegido.
- Rode com `DADOS_EXEMPLO=0` (as contas de exemplo têm senha conhecida), crie o admin com `ADMIN_EMAIL`/`ADMIN_SENHA` e use `DOCS=0`.
- Coloque o gateway atrás de HTTPS (proxy reverso com certificado).
- Troque o SQLite por PostgreSQL gerenciado (um banco por serviço) com backup.
- Proteja o Redis com senha/ACL se ele sair da rede interna.
- Para revogar tokens antes de expirarem, adicione uma lista de revogação no Redis consultada por todos os serviços.

## Como relatar um problema

Encontrou uma falha? Não abra uma issue pública: envie os detalhes diretamente ao professor.
