// Controle de equipamentos: cadastro, edição, responsável e chamados vinculados.
"use strict";
import { get, patch, post } from "../api.js";
import { ICONES } from "../icones.js";
import { ROTULO_SITUACAO, ROTULO_TIPO, avisoErro, debounce, dialogo, esc, opcoes, selo, toast, vazio } from "../util.js";

const CLASSE_SITUACAO = { em_uso: "s-resolvido", estoque: "s-aberto", manutencao: "s-em_atendimento", descartado: "s-fechado" };

function formulario(a, usuarios, erroUsuarios) {
  const v = (campo) => esc(a?.[campo] ?? "");
  return `<form><h2>${a ? `Editar ${esc(a.patrimonio)}` : "Novo equipamento"}</h2>
    <div class="grade g-2">
      <div><label for="e-patrimonio">Patrimônio</label><input id="e-patrimonio" name="patrimonio" value="${v("patrimonio")}" ${a ? "disabled" : "required"} pattern="[A-Za-z0-9-]{3,30}" maxlength="30" placeholder="PAT-0010"></div>
      <div><label for="e-tipo">Tipo</label><select id="e-tipo" name="tipo" ${a ? "disabled" : ""}>${opcoes(ROTULO_TIPO, a?.tipo || "computador")}</select></div>
    </div>
    <label for="e-descricao">Descrição</label><input id="e-descricao" name="descricao" value="${v("descricao")}" required minlength="2" maxlength="200">
    <div class="grade g-2">
      <div><label for="e-marca">Marca</label><input id="e-marca" name="marca" value="${v("marca")}" maxlength="60"></div>
      <div><label for="e-modelo">Modelo</label><input id="e-modelo" name="modelo" value="${v("modelo")}" maxlength="80"></div>
      <div><label for="e-serie">Número de série</label><input id="e-serie" name="numero_serie" value="${v("numero_serie")}" maxlength="80"></div>
      <div><label for="e-setor">Setor</label><input id="e-setor" name="setor" value="${v("setor")}" required minlength="2" maxlength="80"></div>
      <div><label for="e-situacao">Situação</label><select id="e-situacao" name="situacao">${opcoes(ROTULO_SITUACAO, a?.situacao || "em_uso")}</select></div>
      <div><label for="e-responsavel">Responsável</label><select id="e-responsavel" name="responsavel_id" ${erroUsuarios ? "disabled" : ""}>
        <option value="0">Ninguém</option>${usuarios.map((u) => `<option value="${esc(u.id)}" ${u.id === a?.responsavel_id ? "selected" : ""}>${esc(u.nome)}</option>`).join("")}</select>
        ${erroUsuarios ? `<p class="ajuda">${esc(erroUsuarios)}</p>` : ""}</div>
    </div>
    <label for="e-obs">Observações</label><textarea id="e-obs" name="observacoes" maxlength="1000" rows="2">${v("observacoes")}</textarea>
    <div class="erro-texto"></div>
    <div class="rodape-dialogo"><button type="button" class="btn sec" data-cancelar>Cancelar</button><button class="btn" type="submit">Salvar</button></div></form>`;
}

export async function render(el, ctx) {
  const equipe = ctx.eu.perfil !== "solicitante";
  const filtros = { tipo: "", situacao: "", busca: "", meus: !equipe };

  el.innerHTML = `
    <div class="cabecalho"><div><h1>${equipe ? "Equipamentos" : "Meus equipamentos"}</h1>
      <p>${equipe ? "Computadores, notebooks, impressoras, monitores e periféricos da empresa." : "Equipamentos sob sua responsabilidade."}</p></div>
      ${equipe ? `<button class="btn" id="novo-equipamento">${ICONES.novo} Novo equipamento</button>` : ""}</div>
    ${equipe ? `<div class="kpis" id="resumo"></div>` : ""}
    <section class="cartao">
      <div class="filtros">
        <input type="search" id="f-busca" placeholder="Buscar por patrimônio, descrição, modelo ou série" maxlength="80" aria-label="Buscar">
        <select id="f-tipo" aria-label="Tipo">${opcoes(ROTULO_TIPO, "", "Todos os tipos")}</select>
        <select id="f-situacao" aria-label="Situação">${opcoes(ROTULO_SITUACAO, "", "Qualquer situação")}</select>
        ${equipe ? "" : `<label class="check"><input type="checkbox" id="f-meus" checked> Só os meus</label>`}
      </div>
      <div id="lista"></div>
    </section>`;

  let usuarios = [], erroUsuarios = "";
  if (equipe) {
    get("/usuarios?ativos=true").then((u) => { usuarios = u; }).catch((e) => { erroUsuarios = e.message; });
  }

  async function carregarResumo() {
    if (!equipe) return;
    try {
      const r = await get("/ativos/resumo");
      el.querySelector("#resumo").innerHTML = [["Total", r.total, ""], ["Em uso", r.por_situacao.em_uso || 0, "k-ok"],
        ["Em manutenção", r.por_situacao.manutencao || 0, "k-alerta"], ["Em estoque", r.por_situacao.estoque || 0, "k-neutro"]]
        .map(([t, n, c]) => `<div class="kpi ${c}"><small>${esc(t)}</small><b>${esc(n)}</b></div>`).join("");
    } catch (e) { el.querySelector("#resumo").innerHTML = avisoErro(e.message); }
  }

  async function carregar() {
    const q = new URLSearchParams();
    if (filtros.tipo) q.set("tipo", filtros.tipo);
    if (filtros.situacao) q.set("situacao", filtros.situacao);
    if (filtros.busca) q.set("busca", filtros.busca);
    if (filtros.meus) q.set("responsavel_id", ctx.eu.id);
    const lista = el.querySelector("#lista");
    try {
      const ativos = await get("/ativos?" + q.toString());
      lista.innerHTML = ativos.length ? `<div class="envoltorio-tabela"><table class="tabela responsiva"><thead><tr><th>Patrimônio</th><th>Equipamento</th>
        <th>Tipo</th><th>Setor</th><th>Responsável</th><th>Situação</th><th></th></tr></thead><tbody>${ativos.map((a) => `<tr>
          <td data-rotulo="Patrimônio"><b>${esc(a.patrimonio)}</b></td>
          <td class="titulo-celula"><b>${esc(a.descricao)}</b><small>${esc([a.marca, a.modelo, a.numero_serie && "S/N " + a.numero_serie].filter(Boolean).join(" · ") || "—")}</small></td>
          <td data-rotulo="Tipo">${esc(ROTULO_TIPO[a.tipo])}</td><td data-rotulo="Setor">${esc(a.setor)}</td>
          <td data-rotulo="Responsável">${esc(a.responsavel_nome || "—")}</td>
          <td data-rotulo="Situação">${selo(CLASSE_SITUACAO[a.situacao], ROTULO_SITUACAO[a.situacao])}</td>
          <td data-rotulo="Ações"><div class="campo-inline"><a class="btn fantasma pequeno" href="#/chamados?ativo=${esc(a.id)}">Chamados</a>
            ${equipe ? `<button class="btn sec pequeno" data-editar="${esc(a.id)}">Editar</button>` : ""}</div></td></tr>`).join("")}</tbody></table></div>`
        : vazio(filtros.meus ? "Nenhum equipamento está no seu nome." : "Nenhum equipamento encontrado.");
      lista.querySelectorAll("[data-editar]").forEach((b) => b.addEventListener("click", () => editar(ativos.find((a) => a.id === Number(b.dataset.editar)))));
    } catch (e) { lista.innerHTML = avisoErro(e.message); }
  }

  async function editar(ativo) {
    const salvo = await dialogo(formulario(ativo, usuarios, erroUsuarios), async (dados) => {
      const corpo = {};
      for (const [k, v] of dados.entries()) corpo[k] = typeof v === "string" ? v.trim() : v;
      ["marca", "modelo", "numero_serie", "observacoes"].forEach((k) => { if (corpo[k] === "") corpo[k] = null; });
      if ("responsavel_id" in corpo) corpo.responsavel_id = Number(corpo.responsavel_id);
      if (ativo) return patch(`/ativos/${ativo.id}`, corpo);
      if (!corpo.responsavel_id) delete corpo.responsavel_id;
      return post("/ativos", corpo);
    });
    if (salvo) { toast(ativo ? "Equipamento atualizado." : "Equipamento cadastrado."); carregar(); carregarResumo(); }
  }

  el.querySelector("#novo-equipamento")?.addEventListener("click", () => editar(null));
  el.querySelector("#f-busca").addEventListener("input", debounce((e) => { filtros.busca = e.target.value.trim(); carregar(); }));
  el.querySelector("#f-tipo").addEventListener("change", (e) => { filtros.tipo = e.target.value; carregar(); });
  el.querySelector("#f-situacao").addEventListener("change", (e) => { filtros.situacao = e.target.value; carregar(); });
  el.querySelector("#f-meus")?.addEventListener("change", (e) => { filtros.meus = e.target.checked; carregar(); });
  await Promise.all([carregar(), carregarResumo()]);
}
