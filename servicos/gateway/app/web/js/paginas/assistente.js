// Chatbot de suporte: responde perguntas frequentes e, se não resolver, leva para a abertura de chamado.
"use strict";
import { post } from "../api.js";
import { esc } from "../util.js";

const ATALHOS = ["Estou sem internet", "A impressora não imprime", "O computador está lento", "Esqueci minha senha", "Não tenho acesso a um sistema"];
let conversa = []; // mantida enquanto a página estiver aberta

function bolhaBot(r) {
  const passos = r.passos.length ? `<ol>${r.passos.map((p) => `<li>${esc(p)}</li>`).join("")}</ol>` : "";
  const sugestoes = r.sugestoes.length ? `<div class="acoes-msg">${r.sugestoes.map((s) => `<button class="chip" data-artigo="${esc(s.id)}">${esc(s.titulo)}</button>`).join("")}</div>` : "";
  const feedback = r.tipo === "resposta" && !r.avaliada ? `<div class="acoes-msg" data-pergunta="${esc(r.pergunta_id)}">
      <button class="btn ok pequeno" data-util="1">Resolveu</button><button class="btn sec pequeno" data-util="0">Não resolveu</button></div>` : "";
  const chamado = r.abrir_chamado ? `<div class="acoes-msg"><button class="btn pequeno" data-chamado="${esc(r.pergunta_id)}">Abrir chamado</button></div>` : "";
  return `<div class="msg bot">${esc(r.mensagem)}${passos}${sugestoes}${feedback}${chamado}</div>`;
}

export async function render(el) {
  el.innerHTML = `
    <div class="cabecalho"><div><h1>Assistente de suporte</h1><p>Respostas rápidas para os problemas mais comuns. Se não resolver, abrimos um chamado.</p></div></div>
    <section class="cartao chat">
      <div class="chat-mensagens" id="mensagens" aria-live="polite"></div>
      <div class="chat-rodape">
        <div class="chips">${ATALHOS.map((a) => `<button class="chip" data-atalho="${esc(a)}">${esc(a)}</button>`).join("")}</div>
        <form id="form-chat"><input id="pergunta" maxlength="500" placeholder="Descreva o problema…" autocomplete="off" aria-label="Sua pergunta">
          <button class="btn" type="submit">Enviar</button></form>
      </div>
    </section>`;
  const caixa = el.querySelector("#mensagens");
  const respostas = new Map();

  const desenhar = () => {
    caixa.innerHTML = (conversa.length ? "" : `<div class="msg bot">Olá! Sou o assistente do HelpDesk Pro. Como posso ajudar?</div>`) +
      conversa.map((m) => (m.eu ? `<div class="msg eu">${esc(m.texto)}</div>` : bolhaBot(m.resposta))).join("");
    caixa.scrollTop = caixa.scrollHeight;
  };

  async function enviar(texto, chamada) {
    conversa.push({ eu: true, texto });
    desenhar();
    try {
      const r = await chamada();
      respostas.set(r.pergunta_id, r);
      conversa.push({ resposta: r });
    } catch (e) {
      conversa.push({ resposta: { mensagem: e.message, passos: [], sugestoes: [], tipo: "erro", abrir_chamado: false } });
    }
    desenhar();
  }

  function abrirChamado(r) {
    try { sessionStorage.setItem("rascunho-chamado", JSON.stringify(r?.chamado_sugerido || {})); } catch (e) { /* sem armazenamento */ }
    location.hash = "#/novo";
  }

  el.querySelector("#form-chat").addEventListener("submit", (e) => {
    e.preventDefault();
    const campo = el.querySelector("#pergunta");
    const texto = campo.value.trim();
    if (!texto) return;
    campo.value = "";
    enviar(texto, () => post("/assistente/perguntar", { texto }));
  });

  el.addEventListener("click", async (e) => {
    const b = e.target.closest("button");
    if (!b) return;
    if (b.dataset.atalho) enviar(b.dataset.atalho, () => post("/assistente/perguntar", { texto: b.dataset.atalho }));
    if (b.dataset.artigo) enviar(b.textContent, () => post(`/assistente/artigos/${b.dataset.artigo}/consultar`));
    if (b.dataset.chamado) abrirChamado(respostas.get(Number(b.dataset.chamado)));
    if (b.dataset.util !== undefined) {
      const caixaFeedback = b.closest("[data-pergunta]");
      const id = Number(caixaFeedback.dataset.pergunta);
      const util = b.dataset.util === "1";
      if (respostas.get(id)) respostas.get(id).avaliada = true;
      await post(`/assistente/perguntas/${id}/feedback`, { util }).catch(() => {});
      if (util) {
        conversa.push({ resposta: { mensagem: "Que bom que resolveu! Se precisar, é só chamar.", passos: [], sugestoes: [], tipo: "fim", abrir_chamado: false } });
      } else {
        const anterior = respostas.get(id);
        conversa.push({ resposta: { mensagem: "Sinto muito. Vou preparar um chamado com a sua descrição para um técnico analisar.", passos: [], sugestoes: [],
          tipo: "fim", abrir_chamado: true, pergunta_id: id, chamado_sugerido: anterior?.chamado_sugerido } });
      }
      caixaFeedback.remove();
      desenhar();
    }
  });
  desenhar();
  el.querySelector("#pergunta").focus();
}
