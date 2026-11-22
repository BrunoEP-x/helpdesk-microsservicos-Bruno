// Central de notificações do usuário.
"use strict";
import { get, patch, post } from "../api.js";
import { ICONES } from "../icones.js";
import { avisoErro, esc, relativo, toast, vazio } from "../util.js";

const ESTILO = { SlaVencido: ["perigo", "alerta"], SlaProximo: ["alerta", "relogio"], ChamadoResolvido: ["ok", "ok"],
  ChamadoFechado: ["ok", "ok"], ChamadoAtribuido: ["", "conta"], PrioridadeAlterada: ["alerta", "alerta"] };

export async function render(el, ctx) {
  let soNaoLidas = false;
  async function desenhar() {
    let lista;
    try { lista = await get(`/notificacoes?limite=100${soNaoLidas ? "&nao_lidas=true" : ""}`); }
    catch (e) { el.innerHTML = `<div class="cabecalho"><h1>Notificações</h1></div>${avisoErro(e.message)}`; return; }
    el.innerHTML = `
      <div class="cabecalho"><div><h1>Notificações</h1><p>Avisos sobre os seus chamados e prazos.</p></div>
        <div class="chips"><button class="chip ${soNaoLidas ? "" : "ativo"}" data-filtro="todas">Todas</button>
          <button class="chip ${soNaoLidas ? "ativo" : ""}" data-filtro="nao">Não lidas</button>
          <button class="btn sec pequeno" id="todas-lidas">Marcar todas como lidas</button></div></div>
      <section class="cartao">${lista.length ? `<div class="lista-avisos">${lista.map((n) => {
        const [classe, icone] = ESTILO[n.tipo] || ["", "notificacoes"];
        return `<div class="item-aviso ${n.lida ? "" : "nao-lida"}" data-id="${esc(n.id)}" data-chamado="${esc(n.chamado_id ?? "")}" tabindex="0">
          <span class="icone-aviso ${classe}">${ICONES[icone]}</span>
          <div><b>${esc(n.titulo)}</b><div class="suave">${esc(n.mensagem)}</div></div><small>${esc(relativo(n.criada_em))}</small></div>`;
      }).join("")}</div>` : vazio(soNaoLidas ? "Nenhuma notificação não lida." : "Você ainda não tem notificações.")}</section>`;

    el.querySelectorAll("[data-filtro]").forEach((b) => b.addEventListener("click", () => { soNaoLidas = b.dataset.filtro === "nao"; desenhar(); }));
    el.querySelector("#todas-lidas").addEventListener("click", async () => {
      const r = await post("/notificacoes/lidas");
      toast(`${r.marcadas} notificação(ões) marcadas como lidas.`);
      ctx.atualizarContagem();
      desenhar();
    });
    el.querySelectorAll(".item-aviso").forEach((item) => {
      const abrir = async () => {
        await patch(`/notificacoes/${item.dataset.id}/lida`).catch(() => {});
        ctx.atualizarContagem();
        if (item.dataset.chamado) location.hash = `#/chamados/${item.dataset.chamado}`;
        else desenhar();
      };
      item.addEventListener("click", abrir);
      item.addEventListener("keydown", (e) => { if (e.key === "Enter") abrir(); });
    });
  }
  await desenhar();
}
