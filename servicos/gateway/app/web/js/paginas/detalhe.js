// Detalhe do chamado: dados, SLA, ações de atendimento, comentários, histórico e avaliação.
"use strict";
import { get, patch, post, varios } from "../api.js";
import { progresso } from "../graficos.js";
import { ICONES } from "../icones.js";
import {
  ROTULO_CATEGORIA, ROTULO_IMPACTO, ROTULO_PRIORIDADE, ROTULO_STATUS, avisoErro, dataHora, dialogo, duracao, esc,
  iniciais, opcoes, relativo, selo, seloPrioridade, seloSla, seloStatus, toast,
} from "../util.js";

const ACOES_HISTORICO = {
  abertura: "abriu o chamado", atribuicao: "atribuiu o técnico", status: "mudou o status", prioridade: "mudou a prioridade",
  solucao: "registrou a solução", comentario: "comentou", encerramento: "encerrou o atendimento", avaliacao: "avaliou o atendimento",
  alerta_sla: "alerta de SLA", sla_violado: "prazo do SLA ultrapassado",
};
const ORIGEM = { automatica: "definida automaticamente", informada: "informada por quem abriu", ajuste_manual: "ajustada pela equipe" };
const valorLegivel = (campo, v) => (campo === "status" ? ROTULO_STATUS[v] : campo === "prioridade" ? ROTULO_PRIORIDADE[v] : v) ?? "—";

function cartaoSla(c) {
  const inicio = new Date(c.criado_em).getTime(), fim = new Date(c.prazo_sla).getTime();
  const encerrado = ["resolvido", "fechado"].includes(c.status);
  const ref = encerrado && c.resolvido_em ? new Date(c.resolvido_em).getTime() : Date.now();
  const pct = ((ref - inicio) / Math.max(1, fim - inicio)) * 100;
  const classe = { no_prazo: "ok", alerta: "alerta", vencido: "perigo", cumprido: "ok", violado: "perigo" }[c.sla_situacao];
  const texto = encerrado ? (c.sla_violado ? "Resolvido fora do prazo" : "Resolvido dentro do prazo")
    : c.sla_restante_minutos < 0 ? duracao(c.sla_restante_minutos) : `${duracao(c.sla_restante_minutos)} restantes`;
  return `<section class="cartao sla-cartao"><header><h2>Prazo de atendimento (SLA)</h2>${seloSla(c)}</header>
    <div class="restante ${classe}">${esc(texto)}</div>
    ${progresso(pct, { ok: "f-verde", alerta: "f-alerta", perigo: "f-perigo" }[classe])}
    <dl class="info-lista"><dt>Prazo</dt><dd>${esc(dataHora(c.prazo_sla))}</dd>
      ${c.sla_violado_em ? `<dt>Vencido em</dt><dd>${esc(dataHora(c.sla_violado_em))}</dd>` : ""}
      ${c.resolvido_em ? `<dt>Resolvido em</dt><dd>${esc(dataHora(c.resolvido_em))}</dd>` : ""}</dl></section>`;
}

function cartaoAcoes(c, eu, tecnicos) {
  const equipe = eu.perfil !== "solicitante";
  const dono = c.solicitante_id === eu.id;
  const aberto = ["aberto", "em_atendimento"].includes(c.status);
  const partes = [];
  if (equipe && aberto) {
    partes.push(`<label for="sel-tecnico">${c.tecnico_id ? "Reatribuir para" : "Atribuir para"}</label>
      <div class="campo-inline"><select id="sel-tecnico">${tecnicos.length
        ? tecnicos.map((t) => `<option value="${esc(t.id)}" ${t.id === (c.tecnico_id || eu.id) ? "selected" : ""}>${esc(t.nome)}</option>`).join("")
        : `<option value="">Lista de técnicos indisponível</option>`}</select>
        <button class="btn" data-acao="atribuir" ${tecnicos.length ? "" : "disabled"}>Atribuir</button></div>`);
    partes.push(`<label for="sel-prioridade">Prioridade</label>
      <div class="campo-inline"><select id="sel-prioridade">${opcoes(ROTULO_PRIORIDADE, c.prioridade)}</select>
        <button class="btn sec" data-acao="prioridade">Ajustar</button></div>
      <p class="ajuda">Ao ajustar, o prazo do SLA é recalculado a partir da abertura.</p>`);
  }
  if (equipe && c.status === "em_atendimento") partes.push(`<button class="btn ok bloco mt" data-acao="resolver">${ICONES.ok} Marcar como resolvido</button>`);
  if (c.status === "resolvido" && (equipe || dono)) {
    partes.push(`<p class="suave">${dono ? "O técnico marcou como resolvido. O problema foi solucionado?" : "Aguardando confirmação do solicitante."}</p>
      <div class="campo-inline"><button class="btn ok" data-acao="fechar">${dono ? "Sim, encerrar" : "Encerrar"}</button>
      <button class="btn sec" data-acao="reabrir">${dono ? "Não, reabrir" : "Reabrir"}</button></div>`);
  }
  if (!partes.length) return "";
  return `<section class="cartao"><header><h2>Atendimento</h2></header>${partes.join("")}<div class="erro-texto" id="erro-acao"></div></section>`;
}

function estrelas(nota, editavel) {
  return `<span class="estrelas ${editavel ? "" : "leitura"}" ${editavel ? 'role="radiogroup" aria-label="Nota de 1 a 5"' : ""}>${[1, 2, 3, 4, 5].map((n) =>
    editavel ? `<button type="button" class="estrela ${n <= nota ? "cheia" : ""}" data-nota="${n}" aria-label="${n} estrela${n > 1 ? "s" : ""}">${ICONES.estrela}</button>`
      : `<span class="${n <= nota ? "cheia" : ""}">${ICONES.estrela}</span>`).join("")}</span>`;
}

function cartaoAvaliacao(c, eu) {
  if (c.status !== "fechado") return "";
  if (c.avaliacao_nota) return `<section class="cartao"><header><h2>Avaliação do atendimento</h2></header>${estrelas(c.avaliacao_nota, false)}</section>`;
  if (c.solicitante_id !== eu.id) return `<section class="cartao"><header><h2>Avaliação</h2></header><p class="suave">Aguardando a avaliação do solicitante.</p></section>`;
  return `<section class="cartao"><header><h2>Como foi o atendimento?</h2></header>
    <form id="form-avaliacao">${estrelas(0, true)}<input type="hidden" name="nota" value="0">
      <label for="av-comentario">Comentário (opcional)</label><textarea id="av-comentario" name="comentario" maxlength="1000" rows="3"></textarea>
      <button class="btn mt" type="submit">Enviar avaliação</button><div class="erro-texto"></div></form></section>`;
}

function comentariosHtml(c, eu) {
  const equipe = eu.perfil !== "solicitante";
  const itens = c.comentarios.length ? c.comentarios.map((m) => `<div class="comentario ${m.interno ? "interno" : ""}">
      <span class="avatar">${iniciais(m.autor_nome)}</span>
      <div class="balao"><b>${esc(m.autor_nome)}</b> <small>${esc(relativo(m.criado_em))}${m.interno ? " · nota interna" : ""}</small><p>${esc(m.texto)}</p></div></div>`).join("")
    : `<p class="suave">Nenhum comentário ainda.</p>`;
  const form = c.status === "fechado" ? "" : `<form id="form-comentario" class="mt">
      <label for="texto-comentario">Escrever comentário</label><textarea id="texto-comentario" required maxlength="2000" rows="3"></textarea>
      <div class="campo-inline mt">${equipe ? `<label class="check"><input type="checkbox" id="comentario-interno"> Nota interna (só a equipe vê)</label>` : ""}
        <span class="espaco"></span><button class="btn" type="submit">Comentar</button></div><div class="erro-texto"></div></form>`;
  return `<div class="comentarios">${itens}</div>${form}`;
}

function historicoHtml(lista) {
  return `<ol class="linha-tempo">${lista.map((h) => `<li class="${h.autor_id ? "" : "sistema"}">
    <b>${esc(h.autor_nome)}</b> ${esc(ACOES_HISTORICO[h.acao] || h.acao)}
    ${h.campo && h.campo !== "solucao" ? `: ${esc(valorLegivel(h.campo, h.valor_anterior))} → <b>${esc(valorLegivel(h.campo, h.valor_novo))}</b>` : ""}
    ${h.detalhe ? `<div class="suave">${esc(h.detalhe)}</div>` : ""}
    <div class="quando">${esc(dataHora(h.criado_em))}</div></li>`).join("")}</ol>`;
}

export async function render(el, ctx, params) {
  const id = Number(params[0]);
  const eu = ctx.eu;
  let aba = "comentarios";

  async function desenhar() {
    const equipe = eu.perfil !== "solicitante";
    const [chamado, historico, tecnicos] = await varios([`/chamados/${id}`, `/chamados/${id}/historico`,
      ...(equipe ? ["/usuarios?perfil=tecnico&ativos=true"] : [])]);
    if (!chamado.ok) { el.innerHTML = `<a href="#/chamados">← Voltar</a>${avisoErro(chamado.erro)}`; return; }
    const c = chamado.dados;
    el.innerHTML = `
      <div class="cabecalho"><div><a href="#/chamados">← Chamados</a>
        <h1 class="mt">#${esc(c.id)} · ${esc(c.titulo)}</h1>
        <div class="detalhe-topo">${seloStatus(c.status)} ${seloPrioridade(c.prioridade)} ${seloSla(c)}
          <span class="tag">${esc(ROTULO_CATEGORIA[c.categoria])}</span></div></div></div>
      ${tecnicos && !tecnicos.ok ? `<div class="aviso atencao">${esc(tecnicos.erro)} A atribuição fica indisponível até o serviço voltar.</div>` : ""}
      <div class="grade g-2-1">
        <div class="grade">
          <section class="cartao"><header><h2>Descrição</h2><small>aberto ${esc(relativo(c.criado_em))}</small></header>
            <p class="descricao">${esc(c.descricao)}</p>
            <dl class="info-lista mt">
              <dt>Solicitante</dt><dd>${esc(c.solicitante_nome)}</dd>
              <dt>Técnico</dt><dd>${esc(c.tecnico_nome || "Ainda não atribuído")}</dd>
              <dt>Impacto</dt><dd>${esc(ROTULO_IMPACTO[c.impacto])}</dd>
              <dt>Equipamento</dt><dd>${c.ativo_id ? `<a href="#/chamados?ativo=${esc(c.ativo_id)}">${esc(c.ativo_descricao)}</a>` : "—"}</dd>
              <dt>Prioridade</dt><dd>${esc(ROTULO_PRIORIDADE[c.prioridade])} <small>(${esc(ORIGEM[c.prioridade_origem] || "")}; sugerida: ${esc(ROTULO_PRIORIDADE[c.prioridade_sugerida])})</small></dd>
              <dt>Aberto em</dt><dd>${esc(dataHora(c.criado_em))}</dd>
              ${c.fechado_em ? `<dt>Encerrado em</dt><dd>${esc(dataHora(c.fechado_em))}</dd>` : ""}
            </dl></section>
          ${c.solucao ? `<section class="cartao"><header><h2>Solução registrada</h2>${selo("s-resolvido", "Resolvido")}</header><p class="descricao">${esc(c.solucao)}</p></section>` : ""}
          <section class="cartao">
            <div class="abas" role="tablist"><button class="aba ${aba === "comentarios" ? "ativo" : ""}" data-aba="comentarios" role="tab">Comentários (${c.comentarios.length})</button>
              <button class="aba ${aba === "historico" ? "ativo" : ""}" data-aba="historico" role="tab">Histórico e auditoria</button></div>
            <div id="painel-aba">${aba === "comentarios" ? comentariosHtml(c, eu) : historico.ok ? historicoHtml(historico.dados) : avisoErro(historico.erro)}</div>
          </section>
        </div>
        <div class="grade">${cartaoSla(c)}${cartaoAcoes(c, eu, tecnicos?.ok ? tecnicos.dados : [])}${cartaoAvaliacao(c, eu)}</div>
      </div>`;
    ligarEventos(c);
  }

  async function executar(fn, sucesso) {
    const erro = el.querySelector("#erro-acao");
    try { await fn(); toast(sucesso); await desenhar(); }
    catch (e) { if (erro) erro.textContent = e.message; else toast(e.message, "erro"); }
  }

  function ligarEventos(c) {
    el.querySelectorAll("[data-aba]").forEach((b) => b.addEventListener("click", () => { aba = b.dataset.aba; desenhar(); }));
    el.querySelectorAll("[data-acao]").forEach((b) => b.addEventListener("click", async () => {
      const acao = b.dataset.acao;
      if (acao === "atribuir") await executar(() => patch(`/chamados/${id}/atribuir`, { tecnico_id: Number(el.querySelector("#sel-tecnico").value) }), "Técnico atribuído.");
      if (acao === "prioridade") {
        const nova = el.querySelector("#sel-prioridade").value;
        if (nova === c.prioridade) return toast("A prioridade já é essa.");
        const motivo = await dialogo(`<form><h2>Ajustar prioridade para ${esc(ROTULO_PRIORIDADE[nova])}</h2>
          <label for="motivo">Motivo (fica registrado no histórico)</label><input id="motivo" name="motivo" maxlength="300" required>
          <div class="erro-texto"></div><div class="rodape-dialogo"><button type="button" class="btn sec" data-cancelar>Cancelar</button><button class="btn" type="submit">Ajustar</button></div></form>`,
        async (dados) => dados.get("motivo"));
        if (motivo !== null) await executar(() => patch(`/chamados/${id}/prioridade`, { prioridade: nova, motivo }), "Prioridade ajustada e SLA recalculado.");
      }
      if (acao === "resolver") {
        const ok = await dialogo(`<form><h2>Registrar solução</h2><p class="suave">Descreva o que foi feito. O solicitante verá este texto.</p>
          <label for="solucao">Solução</label><textarea id="solucao" name="solucao" required minlength="3" maxlength="2000" rows="5"></textarea>
          <div class="erro-texto"></div><div class="rodape-dialogo"><button type="button" class="btn sec" data-cancelar>Cancelar</button><button class="btn ok" type="submit">Resolver</button></div></form>`,
        async (dados) => { await patch(`/chamados/${id}/status`, { status: "resolvido", solucao: dados.get("solucao").trim() }); return true; });
        if (ok) { toast("Chamado resolvido. O solicitante foi avisado."); await desenhar(); }
      }
      if (acao === "fechar") await executar(() => patch(`/chamados/${id}/status`, { status: "fechado" }), "Chamado encerrado.");
      if (acao === "reabrir") await executar(() => patch(`/chamados/${id}/status`, { status: "em_atendimento" }), "Chamado reaberto.");
    }));

    const formComentario = el.querySelector("#form-comentario");
    formComentario?.addEventListener("submit", async (e) => {
      e.preventDefault();
      const texto = el.querySelector("#texto-comentario").value.trim();
      if (!texto) return;
      try {
        await post(`/chamados/${id}/comentarios`, { texto, interno: Boolean(el.querySelector("#comentario-interno")?.checked) });
        await desenhar();
      } catch (err) { formComentario.querySelector(".erro-texto").textContent = err.message; }
    });

    const formAvaliacao = el.querySelector("#form-avaliacao");
    if (formAvaliacao) {
      formAvaliacao.querySelectorAll("[data-nota]").forEach((b) => b.addEventListener("click", () => {
        formAvaliacao.nota.value = b.dataset.nota;
        formAvaliacao.querySelectorAll("[data-nota]").forEach((s) => s.classList.toggle("cheia", Number(s.dataset.nota) <= Number(b.dataset.nota)));
      }));
      formAvaliacao.addEventListener("submit", async (e) => {
        e.preventDefault();
        const nota = Number(formAvaliacao.nota.value);
        if (!nota) { formAvaliacao.querySelector(".erro-texto").textContent = "Escolha de 1 a 5 estrelas."; return; }
        try {
          await post(`/chamados/${id}/avaliacao`, { nota, comentario: formAvaliacao.comentario.value.trim() || null });
          toast("Obrigado pela avaliação!");
          await desenhar();
        } catch (err) { formAvaliacao.querySelector(".erro-texto").textContent = err.message; }
      });
    }
  }

  await desenhar();
  const temporizador = setInterval(() => { if (!document.querySelector("dialog[open]") && !el.querySelector("textarea:focus")) desenhar().catch(() => {}); }, 60000);
  return () => clearInterval(temporizador);
}
