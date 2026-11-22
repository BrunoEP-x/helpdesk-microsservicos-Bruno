// HelpDesk Pro · aplicação da tela (SPA com rotas por #hash).
// Todo texto vindo da API passa por esc() antes de ir para o HTML (veja util.js).
"use strict";
import { definirAoExpirar, get, guardarToken, post, temToken } from "./api.js";
import { ICONES, LOGO } from "./icones.js";
import { $, $$, ROTULO_PERFIL, esc, iniciais, toast } from "./util.js";

const PAGINAS = {
  painel: { titulo: "Painel", modulo: "./paginas/painel.js" },
  chamados: { titulo: "Chamados", modulo: "./paginas/chamados.js" },
  chamado: { titulo: "Chamado", modulo: "./paginas/detalhe.js" },
  novo: { titulo: "Novo chamado", modulo: "./paginas/novo.js" },
  equipamentos: { titulo: "Equipamentos", modulo: "./paginas/equipamentos.js" },
  assistente: { titulo: "Assistente de suporte", modulo: "./paginas/assistente.js" },
  notificacoes: { titulo: "Notificações", modulo: "./paginas/notificacoes.js" },
  relatorios: { titulo: "Relatórios", modulo: "./paginas/relatorios.js", perfis: ["tecnico", "admin"] },
  usuarios: { titulo: "Usuários e técnicos", modulo: "./paginas/usuarios.js", perfis: ["admin"] },
  configuracoes: { titulo: "Configurações", modulo: "./paginas/configuracoes.js", perfis: ["admin"] },
  conta: { titulo: "Minha conta", modulo: "./paginas/conta.js" },
};

const ctx = { eu: null, contagem: 0, atualizarContagem: () => atualizarContagem() };
let limparPagina = null;
let temporizadores = [];

$$("[data-logo]").forEach((el) => { el.innerHTML = LOGO; });

function mostrar(logado) {
  $("#tela-login").hidden = logado;
  $("#tela-sistema").hidden = !logado;
}

function sair() {
  guardarToken(null);
  ctx.eu = null;
  temporizadores.forEach(clearInterval);
  temporizadores = [];
  mostrar(false);
  history.replaceState(null, "", "#/");
}
definirAoExpirar(sair);

function montarMenu() {
  const { perfil } = ctx.eu;
  const equipe = perfil !== "solicitante";
  const item = (rota, texto, icone, extra = "") => `<li><a href="#/${rota}" data-rota="${rota}">${ICONES[icone]}<span>${esc(texto)}</span>${extra}</a></li>`;
  $("#menu").innerHTML = [
    `<li class="grupo">Atendimento</li>`,
    item("painel", "Painel", "painel"),
    item("chamados", equipe ? "Chamados" : "Meus chamados", "chamados"),
    item("novo", "Abrir chamado", "novo"),
    item("assistente", "Assistente", "assistente"),
    item("notificacoes", "Notificações", "notificacoes", `<span class="contador" id="contador" hidden></span>`),
    `<li class="grupo">Gestão</li>`,
    item("equipamentos", equipe ? "Equipamentos" : "Meus equipamentos", "equipamentos"),
    equipe ? item("relatorios", "Relatórios", "relatorios") : "",
    perfil === "admin" ? item("usuarios", "Usuários e técnicos", "usuarios") : "",
    perfil === "admin" ? item("configuracoes", "Configurações", "configuracoes") : "",
    item("conta", "Minha conta", "conta"),
  ].join("");
  $("#avatar").innerHTML = iniciais(ctx.eu.nome);
  $("#quem-nome").textContent = ctx.eu.nome;
  $("#quem-perfil").textContent = ROTULO_PERFIL[perfil];
}

async function atualizarContagem() {
  try {
    const { nao_lidas } = await get("/notificacoes/contagem");
    ctx.contagem = nao_lidas;
    const el = $("#contador");
    if (el) { el.hidden = !nao_lidas; el.textContent = nao_lidas > 99 ? "99+" : nao_lidas; }
  } catch (e) { /* serviço de notificações fora do ar: o resto da tela continua */ }
}

async function atualizarSaude() {
  try {
    const r = await fetch("/saude").then((x) => x.json());
    const nomes = { usuarios: "Usuários", inventario: "Inventário", chamados: "Chamados", notificacoes: "Notificações", assistente: "Assistente" };
    $("#saude").innerHTML = `<b>Serviços</b><ul>${Object.entries(r.servicos).map(([k, v]) =>
      `<li title="${esc(v.status)}"><span class="ponto ${v.status === "ok" ? "ok" : "fora"}"></span>${esc(nomes[k] || k)}</li>`).join("")}</ul>`;
  } catch (e) {
    $("#saude").innerHTML = `<b>Serviços</b><small>Gateway sem resposta</small>`;
  }
}

async function navegar() {
  if (!ctx.eu) return;
  const [caminho] = location.hash.replace(/^#\/?/, "").split("?");
  const partes = caminho.split("/").filter(Boolean);
  let nome = partes[0] || "painel";
  if (nome === "chamados" && partes[1]) nome = "chamado";
  const pagina = PAGINAS[nome] || PAGINAS.painel;
  const conteudo = $("#conteudo");

  if (pagina.perfis && !pagina.perfis.includes(ctx.eu.perfil)) {
    location.hash = "#/painel";
    return;
  }
  if (typeof limparPagina === "function") limparPagina();
  limparPagina = null;
  $$("#menu a").forEach((a) => a.classList.toggle("ativo", a.dataset.rota === (nome === "chamado" ? "chamados" : nome)));
  $("#tela-sistema").classList.remove("menu-aberto");
  $("#titulo-pagina").textContent = pagina.titulo;
  document.title = `${pagina.titulo} · HelpDesk Pro`;
  conteudo.innerHTML = `<div class="carregando">Carregando…</div>`;
  try {
    const modulo = await import(pagina.modulo);
    limparPagina = await modulo.render(conteudo, ctx, partes.slice(1));
  } catch (e) {
    conteudo.innerHTML = `<div class="aviso erro" role="alert">${esc(e.message)}</div>`;
  }
  conteudo.focus({ preventScroll: true });
}

async function entrar() {
  ctx.eu = await get("/auth/eu");
  mostrar(true);
  montarMenu();
  atualizarContagem();
  atualizarSaude();
  temporizadores.push(setInterval(atualizarContagem, 30000), setInterval(atualizarSaude, 15000));
  await navegar();
}

$("#form-login").addEventListener("submit", async (e) => {
  e.preventDefault();
  const erro = $("#erro-login");
  const botao = $("#form-login button");
  erro.textContent = "";
  if (!$("#email").value || !$("#senha").value) { erro.textContent = "Informe e-mail e senha."; return; }
  botao.disabled = true;
  try {
    const r = await post("/auth/login", { email: $("#email").value.trim(), senha: $("#senha").value });
    guardarToken(r.access_token);
    $("#senha").value = "";
    if (!location.hash || location.hash === "#/") location.hash = "#/painel";
    await entrar();
  } catch (err) {
    erro.textContent = err.message;
  } finally {
    botao.disabled = false;
  }
});

$("#sair").addEventListener("click", () => { sair(); toast("Você saiu do sistema."); });
$("#abrir-menu").addEventListener("click", () => $("#tela-sistema").classList.toggle("menu-aberto"));
$("#tela-sistema").addEventListener("click", (e) => {
  if (e.target === $("#tela-sistema")) $("#tela-sistema").classList.remove("menu-aberto");
});
window.addEventListener("hashchange", navegar);

if (temToken()) {
  entrar().catch(() => sair());
} else {
  mostrar(false);
}
