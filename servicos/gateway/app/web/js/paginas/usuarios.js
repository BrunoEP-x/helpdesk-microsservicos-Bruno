// Gestão de usuários e técnicos (administrador).
"use strict";
import { get, patch, post, put } from "../api.js";
import { ICONES } from "../icones.js";
import { ROTULO_PERFIL, avisoErro, dataCurta, dialogo, esc, iniciais, opcoes, selo, toast, vazio } from "../util.js";

const rodape = (texto) => `<div class="erro-texto"></div><div class="rodape-dialogo"><button type="button" class="btn sec" data-cancelar>Cancelar</button><button class="btn" type="submit">${texto}</button></div>`;
const regraSenha = `<p class="ajuda">Mínimo de 8 caracteres, com letras e números.</p>`;

export async function render(el, ctx) {
  let perfil = "";
  el.innerHTML = `
    <div class="cabecalho"><div><h1>Usuários e técnicos</h1><p>Cadastre pessoas, defina perfis e desative acessos.</p></div>
      <button class="btn" id="novo-usuario">${ICONES.novo} Novo usuário</button></div>
    <section class="cartao"><div class="chips" id="perfis"><button class="chip ativo" data-perfil="">Todos</button>
      ${Object.entries(ROTULO_PERFIL).map(([k, v]) => `<button class="chip" data-perfil="${k}">${esc(v)}s</button>`).join("")}</div>
      <div id="lista" class="mt"></div></section>`;

  async function carregar() {
    const lista = el.querySelector("#lista");
    try {
      const usuarios = await get("/usuarios/detalhes" + (perfil ? `?perfil=${perfil}` : ""));
      lista.innerHTML = usuarios.length ? `<div class="envoltorio-tabela"><table class="tabela responsiva"><thead><tr><th>Nome</th><th>Perfil</th><th>Setor</th>
        <th>Situação</th><th>Último acesso</th><th></th></tr></thead><tbody>${usuarios.map((u) => `<tr>
          <td class="titulo-celula"><div class="campo-inline"><span class="avatar">${iniciais(u.nome)}</span><div><b>${esc(u.nome)}</b><small>${esc(u.email)}</small></div></div></td>
          <td data-rotulo="Perfil">${esc(ROTULO_PERFIL[u.perfil])}</td><td data-rotulo="Setor">${esc(u.setor || "—")}</td>
          <td data-rotulo="Situação">${u.ativo ? selo("s-resolvido", "Ativo") : selo("s-fechado", "Desativado")}</td>
          <td data-rotulo="Último acesso">${esc(u.ultimo_login ? dataCurta(u.ultimo_login) : "nunca")}</td>
          <td data-rotulo="Ações"><div class="campo-inline"><button class="btn sec pequeno" data-editar="${esc(u.id)}">Editar</button>
            <button class="btn fantasma pequeno" data-senha="${esc(u.id)}">Redefinir senha</button></div></td></tr>`).join("")}</tbody></table></div>`
        : vazio("Nenhum usuário com esse perfil.");
      lista.querySelectorAll("[data-editar]").forEach((b) => b.addEventListener("click", () => editar(usuarios.find((u) => u.id === Number(b.dataset.editar)))));
      lista.querySelectorAll("[data-senha]").forEach((b) => b.addEventListener("click", () => senha(usuarios.find((u) => u.id === Number(b.dataset.senha)))));
    } catch (e) { lista.innerHTML = avisoErro(e.message); }
  }

  async function novo() {
    const ok = await dialogo(`<form><h2>Novo usuário</h2>
      <label for="u-nome">Nome</label><input id="u-nome" name="nome" required minlength="2" maxlength="120">
      <label for="u-email">E-mail</label><input id="u-email" name="email" type="email" required maxlength="120">
      <div class="grade g-2"><div><label for="u-perfil">Perfil</label><select id="u-perfil" name="perfil">${opcoes(ROTULO_PERFIL, "solicitante")}</select></div>
        <div><label for="u-setor">Setor</label><input id="u-setor" name="setor" maxlength="80"></div></div>
      <label for="u-senha">Senha inicial</label><input id="u-senha" name="senha" type="password" required minlength="8" maxlength="128" autocomplete="new-password">${regraSenha}
      ${rodape("Cadastrar")}</form>`, async (d) => post("/usuarios", { nome: d.get("nome").trim(), email: d.get("email").trim(),
      perfil: d.get("perfil"), setor: d.get("setor").trim() || null, senha: d.get("senha") }));
    if (ok) { toast("Usuário cadastrado."); carregar(); }
  }

  async function editar(u) {
    const ok = await dialogo(`<form><h2>Editar ${esc(u.nome)}</h2>
      <label for="u-nome">Nome</label><input id="u-nome" name="nome" required minlength="2" maxlength="120" value="${esc(u.nome)}">
      <div class="grade g-2"><div><label for="u-perfil">Perfil</label><select id="u-perfil" name="perfil">${opcoes(ROTULO_PERFIL, u.perfil)}</select></div>
        <div><label for="u-setor">Setor</label><input id="u-setor" name="setor" maxlength="80" value="${esc(u.setor || "")}"></div></div>
      <label class="check"><input type="checkbox" name="ativo" ${u.ativo ? "checked" : ""}> Acesso ativo</label>
      <p class="ajuda">Ao desativar, a pessoa não consegue mais entrar e deixa de receber chamados.</p>
      ${rodape("Salvar")}</form>`, async (d) => patch(`/usuarios/${u.id}`, { nome: d.get("nome").trim(), perfil: d.get("perfil"),
      setor: d.get("setor").trim() || null, ativo: d.get("ativo") === "on" }));
    if (ok) { toast("Usuário atualizado."); carregar(); }
  }

  async function senha(u) {
    const ok = await dialogo(`<form><h2>Redefinir senha de ${esc(u.nome)}</h2>
      <label for="u-nova">Nova senha</label><input id="u-nova" name="senha" type="password" required minlength="8" maxlength="128" autocomplete="new-password">${regraSenha}
      ${rodape("Redefinir")}</form>`, async (d) => { await put(`/usuarios/${u.id}/senha`, { senha: d.get("senha") }); return true; });
    if (ok) toast("Senha redefinida. Informe a nova senha à pessoa por um canal seguro.");
  }

  el.querySelector("#novo-usuario").addEventListener("click", novo);
  el.querySelector("#perfis").addEventListener("click", (e) => {
    const b = e.target.closest("[data-perfil]");
    if (!b) return;
    perfil = b.dataset.perfil;
    el.querySelectorAll("#perfis .chip").forEach((c) => c.classList.toggle("ativo", c === b));
    carregar();
  });
  await carregar();
}
