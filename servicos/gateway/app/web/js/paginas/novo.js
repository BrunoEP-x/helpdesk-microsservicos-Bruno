// Abertura de chamado com sugestão automática de prioridade enquanto a pessoa digita.
"use strict";
import { get, post } from "../api.js";
import { ROTULO_CATEGORIA, ROTULO_IMPACTO, ROTULO_PRIORIDADE, debounce, esc, opcoes, toast } from "../util.js";

const DESCRICAO_IMPACTO = { individual: "só o meu trabalho", setor: "várias pessoas do setor", empresa: "a empresa toda" };

export async function render(el, ctx) {
  // O assistente pode deixar um rascunho de chamado preparado
  let rascunho = {};
  try { rascunho = JSON.parse(sessionStorage.getItem("rascunho-chamado") || "{}"); sessionStorage.removeItem("rascunho-chamado"); } catch (e) { rascunho = {}; }

  el.innerHTML = `
    <div class="cabecalho"><div><h1>Abrir chamado</h1><p>Conte o que está acontecendo. O sistema sugere a prioridade e calcula o prazo de atendimento.</p></div>
      <a class="btn sec" href="#/assistente">Tentar resolver com o assistente</a></div>
    <div class="grade g-2-1">
      <form class="cartao" id="form-novo" novalidate>
        <label for="titulo">Título</label>
        <input id="titulo" required minlength="3" maxlength="120" placeholder="Ex.: Computador não liga" value="${esc(rascunho.titulo || "")}">
        <label for="descricao">Descrição</label>
        <textarea id="descricao" required minlength="3" maxlength="2000" rows="5" placeholder="O que aconteceu? Desde quando? Aparece alguma mensagem de erro?">${esc(rascunho.descricao || "")}</textarea>
        <div class="grade g-2">
          <div><label for="categoria">Categoria</label><select id="categoria">${opcoes(ROTULO_CATEGORIA, rascunho.categoria || "outro")}</select></div>
          <div><label for="ativo">Equipamento (opcional)</label><select id="ativo"><option value="">Nenhum</option></select></div>
        </div>
        <label>Quem está sendo afetado?</label>
        <div class="opcoes-impacto">${Object.entries(ROTULO_IMPACTO).map(([k, v]) => `<label><input type="radio" name="impacto" value="${k}" ${k === "individual" ? "checked" : ""}>${esc(v)}<small>${esc(DESCRICAO_IMPACTO[k])}</small></label>`).join("")}</div>
        <label for="prioridade">Prioridade</label>
        <select id="prioridade"><option value="">Usar a sugestão do sistema</option>${opcoes(ROTULO_PRIORIDADE)}</select>
        <div class="sugestao" id="sugestao" aria-live="polite"><small>Digite o título e a descrição para ver a prioridade sugerida.</small></div>
        <div class="erro-texto" id="erro-novo" role="alert"></div>
        <p><button class="btn" type="submit">Abrir chamado</button></p>
      </form>
      <aside class="cartao"><h2>Prazos de atendimento</h2><p class="suave">Tempo máximo para resolver, conforme a prioridade.</p><div id="prazos"></div>
        <h2 class="mt">Dicas</h2><ul class="suave"><li>Um problema por chamado.</li><li>Informe o patrimônio do equipamento, se souber.</li>
        <li>Problemas que afetam várias pessoas recebem prioridade maior.</li></ul></aside>
    </div>`;

  const f = (id) => el.querySelector("#" + id);

  get("/chamados/sla").then((itens) => {
    f("prazos").innerHTML = `<table class="tabela"><tbody>${itens.map((i) => `<tr><td>${esc(ROTULO_PRIORIDADE[i.prioridade])}</td><td><b>${esc(i.horas)} h</b></td></tr>`).join("")}</tbody></table>`;
  }).catch(() => { f("prazos").innerHTML = `<small>Indisponível no momento.</small>`; });

  // Equipamentos: os do próprio usuário aparecem primeiro
  get("/ativos").then((ativos) => {
    const meus = ativos.filter((a) => a.responsavel_id === ctx.eu.id && a.situacao !== "descartado");
    const outros = ativos.filter((a) => a.responsavel_id !== ctx.eu.id && a.situacao !== "descartado");
    const opcao = (a) => `<option value="${esc(a.id)}">${esc(a.patrimonio)} · ${esc(a.descricao)}</option>`;
    f("ativo").innerHTML = `<option value="">Nenhum</option>${meus.length ? `<optgroup label="Meus equipamentos">${meus.map(opcao).join("")}</optgroup>` : ""}
      ${outros.length ? `<optgroup label="Outros">${outros.map(opcao).join("")}</optgroup>` : ""}`;
  }).catch((e) => {
    f("ativo").innerHTML = `<option value="">Inventário indisponível</option>`;
    f("ativo").disabled = true;
    toast(e.message, "erro");
  });

  const impacto = () => el.querySelector("input[name=impacto]:checked").value;
  const atualizarSugestao = debounce(async () => {
    const titulo = f("titulo").value.trim(), descricao = f("descricao").value.trim();
    if (titulo.length + descricao.length < 4) return;
    try {
      const s = await post("/chamados/sugerir-prioridade", { titulo, descricao, categoria: f("categoria").value, impacto: impacto() });
      f("sugestao").innerHTML = `<b>Prioridade sugerida: <span class="selo p-${esc(s.prioridade)}">${esc(ROTULO_PRIORIDADE[s.prioridade])}</span></b>
        <small> · prazo de ${esc(s.prazo_horas)} h</small><ul>${s.motivos.map((m) => `<li>${esc(m)}</li>`).join("")}</ul>`;
    } catch (e) { f("sugestao").innerHTML = `<small>${esc(e.message)}</small>`; }
  }, 400);
  ["titulo", "descricao", "categoria"].forEach((id) => f(id).addEventListener("input", atualizarSugestao));
  el.querySelectorAll("input[name=impacto]").forEach((r) => r.addEventListener("change", atualizarSugestao));
  atualizarSugestao();

  f("form-novo").addEventListener("submit", async (e) => {
    e.preventDefault();
    const erro = f("erro-novo");
    const titulo = f("titulo").value.trim(), descricao = f("descricao").value.trim();
    if (titulo.length < 3) { erro.textContent = "O título precisa ter pelo menos 3 letras."; return f("titulo").focus(); }
    if (descricao.length < 3) { erro.textContent = "Descreva o problema."; return f("descricao").focus(); }
    erro.textContent = "";
    const botao = e.submitter || el.querySelector("button[type=submit]");
    botao.disabled = true;
    try {
      const c = await post("/chamados", { titulo, descricao, categoria: f("categoria").value, impacto: impacto(),
        prioridade: f("prioridade").value || null, ativo_id: f("ativo").value ? Number(f("ativo").value) : null });
      toast(`Chamado #${c.id} aberto. Prazo: ${new Date(c.prazo_sla).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })}.`);
      location.hash = `#/chamados/${c.id}`;
    } catch (err) {
      erro.textContent = err.message;
      botao.disabled = false;
    }
  });
}
