// Relatórios: satisfação, desempenho e uso do assistente; exportação CSV (admin).
"use strict";
import { baixar, varios } from "../api.js";
import { barras } from "../graficos.js";
import { ICONES } from "../icones.js";
import { avisoErro, dataCurta, esc, horas, numero, toast, vazio } from "../util.js";

const estrelasTexto = (n) => "★".repeat(n) + "☆".repeat(5 - n);

export async function render(el, ctx) {
  const admin = ctx.eu.perfil === "admin";
  const [satisfacao, painel, assistente] = await varios(["/chamados/relatorios/satisfacao", "/chamados/painel",
    ...(admin ? ["/assistente/estatisticas"] : [])]);

  const s = satisfacao.ok ? satisfacao.dados : null;
  const p = painel.ok ? painel.dados : null;
  el.innerHTML = `
    <div class="cabecalho"><div><h1>Relatórios</h1><p>${admin ? "Satisfação, desempenho da equipe e uso do assistente." : "Seus indicadores e as avaliações dos seus atendimentos."}</p></div>
      ${admin ? `<button class="btn sec" id="exportar">${ICONES.relatorios} Exportar chamados (CSV)</button>` : ""}</div>
    ${s ? `<div class="kpis">
      <div class="kpi k-alerta"><small>Satisfação média</small><b>${s.media ? "★ " + numero(s.media) : "—"}</b><span>${s.total} avaliação(ões)</span></div>
      ${p ? `<div class="kpi k-ok"><small>SLA cumprido</small><b>${numero(p.sla_cumprido_percentual, "%")}</b><span>${p.violacoes_sla} fora do prazo</span></div>
      <div class="kpi"><small>Tempo médio de atendimento</small><b>${horas(p.tempo_medio_atendimento_horas)}</b></div>
      <div class="kpi k-neutro"><small>Tempo até a 1ª resposta</small><b>${horas(p.tempo_medio_primeira_resposta_horas)}</b></div>` : ""}
    </div>` : avisoErro(satisfacao.erro)}
    <div class="grade g-2">
      <section class="cartao"><header><h2>Distribuição das notas</h2></header>
        ${s ? barras(Object.fromEntries(Object.entries(s.distribuicao).reverse()), { 5: "★★★★★", 4: "★★★★", 3: "★★★", 2: "★★", 1: "★" }, "f-alerta") : ""}</section>
      <section class="cartao"><header><h2>Satisfação por técnico</h2></header>
        ${s && s.por_tecnico.length ? `<table class="tabela"><thead><tr><th>Técnico</th><th>Média</th><th>Avaliações</th></tr></thead><tbody>
          ${s.por_tecnico.map((t) => `<tr><td>${esc(t.tecnico_nome)}</td><td>★ ${numero(t.media)}</td><td>${t.total}</td></tr>`).join("")}</tbody></table>`
          : vazio("Ainda não há avaliações.")}</section>
    </div>
    <section class="cartao mt"><header><h2>Comentários recentes</h2></header>
      ${s && s.recentes.length ? `<div class="envoltorio-tabela"><table class="tabela responsiva"><thead><tr><th>Chamado</th><th>Nota</th><th>Comentário</th><th>Técnico</th><th>Data</th></tr></thead><tbody>
        ${s.recentes.map((a) => `<tr class="clicavel" data-id="${esc(a.chamado_id)}"><td data-rotulo="Chamado">#${esc(a.chamado_id)}</td>
          <td data-rotulo="Nota">${esc(estrelasTexto(a.nota))}</td><td class="titulo-celula">${esc(a.comentario || "—")}</td>
          <td data-rotulo="Técnico">${esc(a.tecnico_nome || "—")}</td><td data-rotulo="Data">${esc(dataCurta(a.criado_em))}</td></tr>`).join("")}</tbody></table></div>`
        : vazio("Sem comentários ainda.")}</section>
    ${admin ? `<section class="cartao mt"><header><h2>Assistente de suporte</h2></header>${assistente.ok ? `
      <div class="kpis"><div class="kpi"><small>Perguntas</small><b>${assistente.dados.perguntas}</b></div>
        <div class="kpi k-ok"><small>Respondidas pela base</small><b>${assistente.dados.respondidas}</b></div>
        <div class="kpi k-ok"><small>Marcadas como úteis</small><b>${assistente.dados.uteis}</b></div>
        <div class="kpi k-perigo"><small>Não resolveram</small><b>${assistente.dados.nao_uteis}</b></div></div>
      <h3>Perguntas sem resposta (para melhorar a base)</h3>
      ${assistente.dados.sem_resposta_recentes.length ? `<ul>${assistente.dados.sem_resposta_recentes.map((t) => `<li>${esc(t)}</li>`).join("")}</ul>` : `<p class="suave">Nenhuma.</p>`}`
      : avisoErro(assistente.erro)}</section>` : ""}`;

  el.querySelectorAll("tr[data-id]").forEach((tr) => tr.addEventListener("click", () => { location.hash = `#/chamados/${tr.dataset.id}`; }));
  el.querySelector("#exportar")?.addEventListener("click", () => baixar("/chamados/relatorios/chamados.csv", "chamados.csv").catch((e) => toast(e.message, "erro")));
}
