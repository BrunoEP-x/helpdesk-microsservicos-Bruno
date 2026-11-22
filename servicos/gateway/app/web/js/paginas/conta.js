// Minha conta: dados do usuário e troca de senha.
"use strict";
import { post } from "../api.js";
import { ROTULO_PERFIL, esc, toast } from "../util.js";

export async function render(el, ctx) {
  const eu = ctx.eu;
  el.innerHTML = `
    <div class="cabecalho"><div><h1>Minha conta</h1><p>Seus dados de acesso.</p></div></div>
    <div class="grade g-2">
      <section class="cartao"><header><h2>Dados</h2></header><dl class="info-lista">
        <dt>Nome</dt><dd>${esc(eu.nome)}</dd><dt>E-mail</dt><dd>${esc(eu.email)}</dd>
        <dt>Perfil</dt><dd>${esc(ROTULO_PERFIL[eu.perfil])}</dd><dt>Setor</dt><dd>${esc(eu.setor || "—")}</dd></dl>
        <p class="ajuda mt">Para alterar nome, perfil ou setor, fale com o administrador.</p></section>
      <form class="cartao" id="form-senha"><header><h2>Trocar senha</h2></header>
        <label for="atual">Senha atual</label><input id="atual" type="password" required maxlength="128" autocomplete="current-password">
        <label for="nova">Nova senha</label><input id="nova" type="password" required minlength="8" maxlength="128" autocomplete="new-password">
        <label for="confirma">Confirme a nova senha</label><input id="confirma" type="password" required minlength="8" maxlength="128" autocomplete="new-password">
        <p class="ajuda">Mínimo de 8 caracteres, com letras e números.</p>
        <div class="erro-texto" role="alert"></div><button class="btn" type="submit">Trocar senha</button></form>
    </div>`;
  const form = el.querySelector("#form-senha");
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const erro = form.querySelector(".erro-texto");
    const [atual, nova, confirma] = ["atual", "nova", "confirma"].map((id) => form.querySelector("#" + id).value);
    if (nova !== confirma) { erro.textContent = "A confirmação não confere com a nova senha."; return; }
    try {
      await post("/auth/senha", { senha_atual: atual, nova_senha: nova });
      form.reset(); erro.textContent = "";
      toast("Senha alterada.");
    } catch (err) { erro.textContent = err.message; }
  });
}
