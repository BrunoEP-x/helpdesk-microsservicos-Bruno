// Painel: indicadores, gráficos de desempenho e chamados que exigem atenção.
"use strict";
import { varios } from "../api.js";
import { barras, linhas, rosca } from "../graficos.js";
import { ICONES } from "../icones.js";
import { ROTULO_CATEGORIA, ROTULO_PRIORIDADE, ROTULO_STATUS, avisoErro, esc, horas, numero, seloPrioridade, seloSla, vazio } from "../util.js";

const kpi = (rotulo, valor, classe = "", detalhe = "") =>
  `<div class="kpi ${classe}"><small>${esc(rotulo)}</small><b>${esc(valor)}</b>${detalhe ? `<span>${esc(detalhe)}</span>` : ""}</div>`;

function listaAtencao(chamados) {
  if (!chamados.length) return `<div class="vazio">${ICONES.ok}Nenhum chamado atrasado ou perto do prazo.</div>`;
  return `<table class="tabela responsiva"><tbody>${chamados.slice(0, 8).map((c) => `
    <tr class="clicavel" data-id="${esc(c.id)}">
      <td class="titulo-celula"><b>#${esc(c.id)} · ${esc(c.titulo)}</b><small>${esc(c.tecnico_nome || "Sem técnico")}</small></td>
      <td data-rotulo="Prioridade">${seloPrioridade(c.prioridade)}</td>
      <td data-rotulo="SLA">${seloSla(c)}</td></tr>`).join("")}</tbody></table>`;
}

function tabelaTecnicos(lista) {
  if (!lista.length) return vazio("Nenhum chamado atribuído ainda.");
  return `<div class="envoltorio-tabela"><table class="tabela responsiva"><thead><tr><th>Técnico</th><th>Atribuídos</th><th>Em aberto</th>
    <th>Resolvidos</th><th>Tempo médio</th><th>Fora do SLA</th><th>Avaliação</th></tr></thead><tbody>${lista.map((t) => `<tr>
      <td class="titulo-celula"><b>${esc(t.tecnico_nome)}</b></td><td data-rotulo="Atribuídos">${t.atribuidos}</td>
      <td data-rotulo="Em aberto">${t.em_aberto}</td><td data-rotulo="Resolvidos">${t.resolvidos}</td>
      <td data-rotulo="Tempo médio">${horas(t.tempo_medio_horas)}</td><td data-rotulo="Fora do SLA">${t.violacoes_sla}</td>
      <td data-rotulo="Avaliação">${t.avaliacao_media ? `★ ${numero(t.avaliacao_media)} <small>(${t.avaliacoes})</small>` : "—"}</td></tr>`).join("")}
    </tbody></table></div>`;
}

export async function render(el, ctx) {
  const equipe = ctx.eu.perfil !== "solicitante";
  let apenasMeus = false;

  async function desenhar() {
    const [painel, vencidos, alerta, recentes] = await varios([
      `/chamados/painel${apenasMeus ? "?apenas_meus=true" : ""}`, "/chamados?sla=vencido&limite=20",
      "/chamados?sla=alerta&limite=20", "/chamados?limite=5",
    ]);
    if (!painel.ok) { el.innerHTML = avisoErro(painel.erro); return; }
    const p = painel.dados;
    const atencao = [...(vencidos.ok ? vencidos.dados : []), ...(alerta.ok ? alerta.dados : [])];

    el.innerHTML = `
      <div class="cabecalho">
        <div><h1>Olá, ${esc(ctx.eu.nome.split(" ")[0])}</h1>
          <p>${equipe ? "Visão geral do suporte técnico." : "Acompanhe as suas solicitações."} Atualizado às ${new Date(p.gerado_em).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}.</p></div>
        <div class="chips">${ctx.eu.perfil === "tecnico" ? `<button class="chip ${apenasMeus ? "" : "ativo"}" data-escopo="todos">Todos</button>
          <button class="chip ${apenasMeus ? "ativo" : ""}" data-escopo="meus">Meus atendimentos</button>` : ""}
          <a class="btn" href="#/novo">${ICONES.novo} Abrir chamado</a></div>
      </div>
      <div class="kpis">
        ${kpi("Total de chamados", p.total)}
        ${kpi("Abertos", p.abertos, "", "aguardando técnico")}
        ${kpi("Em andamento", p.em_andamento, "k-alerta")}
        ${kpi("Concluídos", p.concluidos, "k-ok")}
        ${kpi("Atrasados", p.atrasados, p.atrasados ? "k-perigo" : "k-neutro", `${p.em_alerta} perto do prazo`)}
        ${kpi("Tempo médio de atendimento", horas(p.tempo_medio_atendimento_horas), "k-neutro", `1ª resposta: ${horas(p.tempo_medio_primeira_resposta_horas)}`)}
        ${kpi("SLA cumprido", numero(p.sla_cumprido_percentual, "%"), "k-ok", `${p.violacoes_sla} fora do prazo`)}
        ${kpi("Satisfação", p.satisfacao_media ? `★ ${numero(p.satisfacao_media)}` : "—", "k-alerta", "média de 1 a 5")}
      </div>
      <div class="grade g-2-1">
        <section class="cartao"><header><h2>Abertos x resolvidos · últimos 14 dias</h2></header>${linhas(p.serie)}</section>
        <section class="cartao"><header><h2>Por prioridade</h2></header>${rosca(p.por_prioridade, ROTULO_PRIORIDADE)}</section>
      </div>
      <div class="grade g-2-1 mt">
        <section class="cartao"><header><h2>${equipe ? "Exigem atenção (SLA)" : "Meus chamados recentes"}</h2>
          <a href="#/chamados${equipe ? "?sla=vencido" : ""}">Ver todos</a></header>
          ${equipe ? (vencidos.ok ? listaAtencao(atencao) : avisoErro(vencidos.erro)) : (recentes.ok ? listaAtencao(recentes.dados) : avisoErro(recentes.erro))}
        </section>
        <section class="cartao"><header><h2>Por status</h2></header>${barras(Object.fromEntries(Object.entries(p.por_status)), ROTULO_STATUS)}
          <h3 class="mt">Por categoria</h3>${barras(p.por_categoria, ROTULO_CATEGORIA, "f-media")}</section>
      </div>
      ${equipe ? `<section class="cartao mt"><header><h2>${ctx.eu.perfil === "admin" ? "Desempenho dos técnicos" : "Meus indicadores"}</h2>
        <a href="#/relatorios">Relatórios</a></header>${tabelaTecnicos(p.desempenho_tecnicos)}</section>` : ""}`;

    el.querySelectorAll("tr[data-id]").forEach((tr) => tr.addEventListener("click", () => { location.hash = `#/chamados/${tr.dataset.id}`; }));
    el.querySelectorAll("[data-escopo]").forEach((b) => b.addEventListener("click", () => { apenasMeus = b.dataset.escopo === "meus"; desenhar(); }));
  }

  await desenhar();
  const temporizador = setInterval(() => desenhar().catch(() => {}), 60000);
  return () => clearInterval(temporizador);
}
