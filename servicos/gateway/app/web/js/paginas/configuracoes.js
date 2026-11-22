// Configurações do administrador: prazos de SLA e base de conhecimento do assistente.
"use strict";
import { get, post, put } from "../api.js";
import { ICONES } from "../icones.js";
import { ROTULO_CATEGORIA, ROTULO_PRIORIDADE, avisoErro, dialogo, esc, opcoes, selo, toast } from "../util.js";

export async function render(el) {
  el.innerHTML = `
    <div class="cabecalho"><div><h1>Configurações</h1><p>Prazos de atendimento e base de conhecimento do assistente.</p></div></div>
    <div class="grade g-2-1">
      <section class="cartao"><header><h2>Prazos de SLA por prioridade</h2></header><div id="sla"></div></section>
      <section class="cartao"><header><h2>Como funciona</h2></header><ul class="suave">
        <li><b>Prazo</b>: tempo máximo para resolver, contado da abertura.</li>
        <li><b>Alerta</b>: quando essa porcentagem do prazo passa, o técnico (ou a equipe) é avisado.</li>
        <li>Ao vencer, o chamado é marcado como fora do SLA e isso fica no histórico.</li>
        <li>Os novos prazos valem para chamados abertos daqui em diante.</li></ul>
        <button class="btn sec" id="verificar">${ICONES.relogio} Verificar prazos agora</button></section>
    </div>
    <section class="cartao mt"><header><h2>Base de conhecimento do assistente</h2><button class="btn pequeno" id="novo-artigo">${ICONES.novo} Novo artigo</button></header>
      <div id="artigos"></div></section>`;

  async function carregarSla() {
    const caixa = el.querySelector("#sla");
    try {
      const itens = await get("/chamados/sla");
      caixa.innerHTML = `<form id="form-sla"><table class="tabela"><thead><tr><th>Prioridade</th><th>Prazo (horas)</th><th>Alerta (% do prazo)</th></tr></thead><tbody>
        ${itens.map((i) => `<tr><td><span class="selo p-${esc(i.prioridade)}">${esc(ROTULO_PRIORIDADE[i.prioridade])}</span></td>
          <td><input type="number" name="horas-${esc(i.prioridade)}" min="1" max="720" required value="${esc(i.horas)}" aria-label="Horas"></td>
          <td><input type="number" name="alerta-${esc(i.prioridade)}" min="10" max="95" required value="${esc(i.alerta_percentual)}" aria-label="Alerta"></td></tr>`).join("")}
        </tbody></table><div class="erro-texto"></div><button class="btn mt" type="submit">Salvar prazos</button></form>`;
      caixa.querySelector("#form-sla").addEventListener("submit", async (e) => {
        e.preventDefault();
        const d = new FormData(e.target);
        try {
          await put("/chamados/sla", itens.map((i) => ({ prioridade: i.prioridade, horas: Number(d.get(`horas-${i.prioridade}`)),
            alerta_percentual: Number(d.get(`alerta-${i.prioridade}`)) })));
          toast("Prazos de SLA atualizados.");
        } catch (err) { e.target.querySelector(".erro-texto").textContent = err.message; }
      });
    } catch (e) { caixa.innerHTML = avisoErro(e.message); }
  }

  async function carregarArtigos() {
    const caixa = el.querySelector("#artigos");
    try {
      const artigos = await get("/assistente/artigos");
      caixa.innerHTML = `<div class="envoltorio-tabela"><table class="tabela responsiva"><thead><tr><th>Artigo</th><th>Categoria</th><th>Consultas</th><th>Útil / não útil</th><th>Situação</th><th></th></tr></thead><tbody>
        ${artigos.map((a) => `<tr><td class="titulo-celula"><b>${esc(a.titulo)}</b><small>${esc(a.palavras_chave)}</small></td>
          <td data-rotulo="Categoria">${esc(ROTULO_CATEGORIA[a.categoria] || a.categoria)}</td><td data-rotulo="Consultas">${a.consultas}</td>
          <td data-rotulo="Útil / não útil">${a.util_sim} / ${a.util_nao}</td><td data-rotulo="Situação">${a.ativo ? selo("s-resolvido", "Ativo") : selo("s-fechado", "Inativo")}</td>
          <td data-rotulo="Ações"><button class="btn sec pequeno" data-editar="${esc(a.id)}">Editar</button></td></tr>`).join("")}</tbody></table></div>`;
      caixa.querySelectorAll("[data-editar]").forEach((b) => b.addEventListener("click", () => editar(artigos.find((a) => a.id === Number(b.dataset.editar)))));
    } catch (e) { caixa.innerHTML = avisoErro(e.message); }
  }

  async function editar(a) {
    const ok = await dialogo(`<form><h2>${a ? "Editar artigo" : "Novo artigo"}</h2>
      <label for="a-titulo">Título</label><input id="a-titulo" name="titulo" required minlength="3" maxlength="120" value="${esc(a?.titulo || "")}">
      <label for="a-categoria">Categoria</label><select id="a-categoria" name="categoria">${opcoes(ROTULO_CATEGORIA, a?.categoria || "outro")}</select>
      <label for="a-chaves">Palavras-chave (separadas por vírgula)</label><input id="a-chaves" name="palavras_chave" required minlength="3" maxlength="600" value="${esc(a?.palavras_chave || "")}">
      <label for="a-resposta">Resposta (um passo por linha)</label><textarea id="a-resposta" name="resposta" required minlength="10" maxlength="4000" rows="6">${esc(a?.resposta || "")}</textarea>
      <label class="check"><input type="checkbox" name="ativo" ${!a || a.ativo ? "checked" : ""}> Ativo</label>
      <div class="erro-texto"></div><div class="rodape-dialogo"><button type="button" class="btn sec" data-cancelar>Cancelar</button><button class="btn" type="submit">Salvar</button></div></form>`,
    async (d) => {
      const corpo = { titulo: d.get("titulo").trim(), categoria: d.get("categoria"), palavras_chave: d.get("palavras_chave").trim(),
        resposta: d.get("resposta").trim(), ativo: d.get("ativo") === "on" };
      return a ? put(`/assistente/artigos/${a.id}`, corpo) : post("/assistente/artigos", corpo);
    });
    if (ok) { toast("Artigo salvo."); carregarArtigos(); }
  }

  el.querySelector("#verificar").addEventListener("click", async () => {
    try {
      const r = await post("/chamados/sla/verificar");
      toast(`Verificação concluída: ${r.alertas} alerta(s) e ${r.violacoes} violação(ões) registradas.`);
    } catch (e) { toast(e.message, "erro"); }
  });
  el.querySelector("#novo-artigo").addEventListener("click", () => editar(null));
  await Promise.all([carregarSla(), carregarArtigos()]);
}
