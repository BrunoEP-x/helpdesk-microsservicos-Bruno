"""Artigos iniciais da base de conhecimento. O administrador pode editar pela tela."""

ARTIGOS = [
    dict(titulo="Sem conexão com a internet", categoria="rede",
         palavras_chave="internet, sem internet, rede, wifi, wi-fi, conexão, conectar, conecta, não conecta, caiu a rede, navegar, cabo de rede, offline, site não abre",
         resposta="Confira se o cabo de rede está bem encaixado ou se o Wi-Fi está ligado.\n"
                  "Veja se outras pessoas perto de você também estão sem internet.\n"
                  "Desligue e ligue o Wi-Fi (ou desconecte e reconecte o cabo).\n"
                  "Reinicie o computador.\n"
                  "Se só um site não abre, tente outro navegador ou limpe o cache."),
    dict(titulo="Impressora não funciona", categoria="impressora",
         palavras_chave="impressora, imprimir, impressão, papel, atolado, atolando, toner, tinta, fila de impressão, não imprime",
         resposta="Confira se a impressora está ligada e sem luz de erro piscando.\n"
                  "Verifique se há papel e se nenhuma folha está presa (abra as tampas com cuidado).\n"
                  "No computador, abra a fila de impressão e cancele documentos travados.\n"
                  "Confirme se a impressora certa está selecionada na hora de imprimir.\n"
                  "Desligue a impressora por 30 segundos e ligue de novo."),
    dict(titulo="Computador lento", categoria="hardware",
         palavras_chave="lento, lentidão, devagar, travando, trava, demora, congelando, pesado, memória, computador lento",
         resposta="Feche programas e abas do navegador que não está usando.\n"
                  "Reinicie o computador (desligar e ligar resolve muitos casos).\n"
                  "Verifique se há atualizações sendo instaladas e aguarde terminarem.\n"
                  "Libere espaço no disco: esvazie a lixeira e apague downloads antigos.\n"
                  "Se a lentidão começou depois de instalar algo, avise a TI no chamado."),
    dict(titulo="Problemas de login ou senha", categoria="acesso",
         palavras_chave="login, senha, entrar, acesso negado, bloqueado, bloqueada, esqueci, expirada, usuário, não consigo entrar, credencial",
         resposta="Confira se o Caps Lock está desligado e se o usuário está escrito certo.\n"
                  "Depois de várias tentativas erradas, a conta fica bloqueada por alguns minutos: aguarde e tente de novo.\n"
                  "Se esqueceu a senha, peça a redefinição ao administrador.\n"
                  "Se a senha expirou, o sistema pede uma nova: use letras e números, com pelo menos 8 caracteres."),
    dict(titulo="Sem acesso a um sistema", categoria="acesso",
         palavras_chave="acesso, sistema, permissão, liberar, liberação, erp, rh, financeiro, pasta, compartilhada, não tenho acesso, sem permissão",
         resposta="Confirme o nome exato do sistema ou da pasta que você precisa.\n"
                  "Pergunte ao seu gestor se o acesso já foi autorizado: a TI só libera com a aprovação dele.\n"
                  "Se você já tinha acesso e perdeu, saia e entre de novo no sistema.\n"
                  "Para pedir um acesso novo, abra um chamado na categoria Acesso informando o sistema e o motivo."),
    dict(titulo="E-mail não envia ou não recebe", categoria="software",
         palavras_chave="email, e-mail, outlook, caixa de entrada, enviar, receber, anexo, caixa cheia, spam",
         resposta="Verifique a pasta de spam ou lixo eletrônico.\n"
                  "Confira se a caixa de e-mail não está cheia e apague mensagens antigas com anexos grandes.\n"
                  "Anexos muito grandes (acima de 20 MB) costumam ser recusados: use um link de compartilhamento.\n"
                  "Feche e abra o programa de e-mail."),
    dict(titulo="Suspeita de vírus ou e-mail falso", categoria="seguranca",
         palavras_chave="vírus, virus, phishing, golpe, e-mail falso, hacker, invadido, malware, link suspeito, ransomware",
         resposta="Não clique em links nem abra anexos da mensagem suspeita.\n"
                  "Se já clicou, desconecte o computador da rede (tire o cabo ou desligue o Wi-Fi).\n"
                  "Não digite senhas em páginas abertas pelo link.\n"
                  "Abra um chamado na categoria Segurança imediatamente: esse tipo de chamado recebe prioridade alta."),
]
