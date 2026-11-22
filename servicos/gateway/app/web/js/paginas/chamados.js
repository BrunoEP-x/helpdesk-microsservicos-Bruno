// Lista de chamados com filtros (status, prioridade, SLA, busca e "atribuídos a mim").
"use strict";
import { get } from "../api.js";
import { ICONES } from "../icones.js";
import {
  ROTULO_CATEGORIA, ROTULO_PRIORIDADE, ROTULO_STATUS, avisoErro, dataCurta, debounce, esc, opcoes, parametrosHash,
  seloPrioridade, seloSla, seloStatus, vazio,
} from "../util.js";

export async function render(el, ctx) {
  const equipe = ctx.eu.perfil !== "solicitante";
  const ph = parametrosHash();
  const filtros = { status: ph.get("status") || "", prioridade: ph.get("prioridade") || "", sla: ph.get("sla") || "",
    busca: ph.get("busca") || "", ativo_id: ph.get("ativo") || "", meus: ph.get("meus") === "1" };

  el.innerHTML = `
    <div class="cabecalho"><div><h1>${equipe ? "Chamados" : "Meus chamados"}</h1>
      <p>${equipe ? "Todos os chamados do suporte. Clique em um chamado para atender." : "Acompanhe o andamento das suas solicitações."}</p></div>
      <a class="btn" href="#/novo">${ICONES.novo} Abrir chamado</a></div>
    <section class="cartao">
      <div class="filtros">
        <input type="search" id="f-busca" placeholder="Buscar por título, descrição ou número" value="${esc(filtros.busca)}" maxlength="80" aria-label="Buscar">
        <select id="f-prioridade" aria-label="Prioridade">${opcoes(ROTULO_PRIORIDADE, filtros.prioridade, "Todas as prioridades")}</select>
        <select id="f-sla" aria-label="Prazo">${opcoes({ vencido: "Atrasados", alerta: "Vencendo em breve" }, filtros.sla, "Qualquer prazo")}</select>
        ${ctx.eu.perfil === "tecnico" ? `<label class="check"><input type="checkbox" id="f-meus" ${filtros.meus ? "checked" : ""}> Atribuídos a mim</label>` : ""}
      </div>
      <div class="chips" id="f-status">
        <button class="chip ${filtros.status ? "" : "ativo"}" data-status="">Todos</button>
        ${Object.entries(ROTULO_STATUS).map(([k, v]) => `<button class="chip ${filtros.status === k ? "ativo" : ""}" data-status="${k}">${esc(v)}</button>`).join("")}
      </div>
      ${filtros.ativo_id ? `<div class="aviso info mt">Mostrando os chamados do equipamento #${esc(filtros.ativo_id)}. <a href="#/chamados">Limpar</a></div>` : ""}
      <div id="lista" class="mt"></div>
    </section>`;

  async function carregar() {
    const q = new URLSearchParams();
    if (filtros.status) q.set("status", filtros.status);
    if (filtros.prioridade) q.set("prioridade", filtros.prioridade);
    if (filtros.sla) q.set("sla", filtros.sla);
    if (filtros.busca) q.set("busca", filtros.busca);
    if (filtros.ativo_id) q.set("ativo_id", filtros.ativo_id);
    if (filtros.meus) q.set("tecnico_id", ctx.eu.id);
    const lista = el.querySelector("#lista");
    try {
      const chamados = await get("/chamados?" + q.toString());
      lista.innerHTML = chamados.length ? `<div class="envoltorio-tabela"><table class="tabela responsiva">
        <thead><tr><th>#</th><th>Chamado</th><th>Prioridade</th><th>Status</th><th>Técnico</th><th>Prazo (SLA)</th><th>Aberto em</th></tr></thead>
        <tbody>${chamados.map((c) => `<tr class="clicavel" data-id="${esc(c.id)}" tabindex="0">
          <td data-rotulo="Número"><b>#${esc(c.id)}</b></td>
          <td class="titulo-celula"><b>${esc(c.titulo)}</b><small>${esc(c.solicitante_nome)} · ${esc(ROTULO_CATEGORIA[c.categoria])}</small></td>
          <td data-rotulo="Prioridade">${seloPrioridade(c.prioridade)}</td>
          <td data-rotulo="Status">${seloStatus(c.status)}</td>
          <td data-rotulo="Técnico">${esc(c.tecnico_nome || "—")}</td>
          <td data-rotulo="Prazo">${seloSla(c)}</td>
          <td data-rotulo="Aberto em">${esc(dataCurta(c.criado_em))}</td></tr>`).join("")}</tbody></table></div>`
        : vazio("Nenhum chamado encontrado com esses filtros.");
      lista.querySelectorAll("tr[data-id]").forEach((tr) => {
        const abrir = () => { location.hash = `#/chamados/${tr.dataset.id}`; };
        tr.addEventListener("click", abrir);
        tr.addEventListener("keydown", (e) => { if (e.key === "Enter") abrir(); });
      });
    } catch (e) {
      lista.innerHTML = avisoErro(e.message);
    }
  }

  el.querySelector("#f-busca").addEventListener("input", debounce((e) => { filtros.busca = e.target.value.trim(); carregar(); }));
  el.querySelector("#f-prioridade").addEventListener("change", (e) => { filtros.prioridade = e.target.value; carregar(); });
  el.querySelector("#f-sla").addEventListener("change", (e) => { filtros.sla = e.target.value; carregar(); });
  el.querySelector("#f-meus")?.addEventListener("change", (e) => { filtros.meus = e.target.checked; carregar(); });
  el.querySelector("#f-status").addEventListener("click", (e) => {
    const b = e.target.closest("[data-status]");
    if (!b) return;
    filtros.status = b.dataset.status;
    el.querySelectorAll("#f-status .chip").forEach((c) => c.classList.toggle("ativo", c === b));
    carregar();
  });
  await carregar();
}
