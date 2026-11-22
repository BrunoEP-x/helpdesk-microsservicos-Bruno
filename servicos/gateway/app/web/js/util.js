// Utilidades da tela. REGRA DE SEGURANÇA: todo texto vindo da API passa por esc()
// antes de entrar no HTML, para impedir que um título como <script> seja executado (XSS).
"use strict";

export const $ = (seletor, raiz = document) => raiz.querySelector(seletor);
export const $$ = (seletor, raiz = document) => [...raiz.querySelectorAll(seletor)];
export const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

export const ROTULO_STATUS = { aberto: "Aberto", em_atendimento: "Em andamento", resolvido: "Resolvido", fechado: "Encerrado" };
export const ROTULO_PRIORIDADE = { baixa: "Baixa", media: "Média", alta: "Alta", critica: "Crítica" };
export const ROTULO_CATEGORIA = { rede: "Rede e internet", hardware: "Computador e hardware", software: "Programas e sistemas",
  impressora: "Impressora", acesso: "Acesso e senha", seguranca: "Segurança", outro: "Outro" };
export const ROTULO_IMPACTO = { individual: "Só eu", setor: "Meu setor", empresa: "A empresa toda" };
export const ROTULO_PERFIL = { solicitante: "Usuário", tecnico: "Técnico", admin: "Administrador" };
export const ROTULO_TIPO = { computador: "Computador", notebook: "Notebook", impressora: "Impressora", monitor: "Monitor",
  periferico: "Periférico", rede: "Rede", outro: "Outro" };
export const ROTULO_SITUACAO = { em_uso: "Em uso", estoque: "Em estoque", manutencao: "Em manutenção", descartado: "Descartado" };
export const ROTULO_SLA = { no_prazo: "No prazo", alerta: "Vence em breve", vencido: "Atrasado", cumprido: "Cumprido", violado: "Fora do prazo" };

export const opcoes = (mapa, atual, vazio) =>
  (vazio !== undefined ? `<option value="">${esc(vazio)}</option>` : "") +
  Object.entries(mapa).map(([v, t]) => `<option value="${esc(v)}"${v === atual ? " selected" : ""}>${esc(t)}</option>`).join("");

export const dataHora = (s) => s ? new Date(s).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", year: "2-digit", hour: "2-digit", minute: "2-digit" }) : "—";
export const dataCurta = (s) => s ? new Date(s).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }) : "—";
export const relativo = (s) => {
  const min = Math.round((Date.now() - new Date(s).getTime()) / 60000);
  if (min < 1) return "agora";
  if (min < 60) return `há ${min} min`;
  if (min < 1440) return `há ${Math.round(min / 60)} h`;
  return `há ${Math.round(min / 1440)} d`;
};
export const duracao = (minutos) => {
  const m = Math.abs(minutos);
  const texto = m >= 1440 ? `${Math.floor(m / 1440)}d ${Math.floor((m % 1440) / 60)}h` : m >= 60 ? `${Math.floor(m / 60)}h ${m % 60}min` : `${m} min`;
  return minutos < 0 ? `atrasado ${texto}` : texto;
};
export const numero = (v, sufixo = "") => (v === null || v === undefined ? "—" : `${String(v).replace(".", ",")}${sufixo}`);
export const horas = (v) => (v === null || v === undefined ? "—" : v < 1 ? `${Math.round(v * 60)} min` : `${String(v).replace(".", ",")} h`);
export const iniciais = (nome) => esc(String(nome || "?").split(/\s+/).map((p) => p[0]).slice(0, 2).join("").toUpperCase());

export const selo = (classe, texto) => `<span class="selo ${esc(classe)}">${esc(texto)}</span>`;
export const seloStatus = (s) => selo("s-" + s, ROTULO_STATUS[s] || s);
export const seloPrioridade = (p) => selo("p-" + p, ROTULO_PRIORIDADE[p] || p);
export const seloSla = (c) => {
  const texto = c.sla_restante_minutos !== null && c.sla_restante_minutos !== undefined && ["no_prazo", "alerta", "vencido"].includes(c.sla_situacao)
    ? duracao(c.sla_restante_minutos) : ROTULO_SLA[c.sla_situacao];
  return selo("sla-" + c.sla_situacao, texto);
};

export function toast(mensagem, tipo = "ok") {
  const div = document.createElement("div");
  div.className = "toast" + (tipo === "erro" ? " erro" : "");
  div.textContent = mensagem;
  $("#toasts").append(div);
  setTimeout(() => div.remove(), 4200);
}

export const avisoErro = (mensagem) => `<div class="aviso erro" role="alert">${esc(mensagem)}</div>`;
export const vazio = (texto) => `<div class="vazio"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M3 7h18M5 7l1 13h12l1-13M9 7V4h6v3"/></svg>${esc(texto)}</div>`;

export function debounce(fn, ms = 350) {
  let t;
  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
}

// Abre o <dialog> com o HTML informado e devolve uma Promise com os dados do formulário (ou null se cancelar)
export function dialogo(html, aoEnviar) {
  const d = $("#dialogo");
  d.innerHTML = html;
  d.showModal();
  const form = $("form", d);
  return new Promise((resolver) => {
    const fechar = (valor) => { d.close(); resolver(valor); };
    $$("[data-cancelar]", d).forEach((b) => b.addEventListener("click", () => fechar(null)));
    d.addEventListener("cancel", () => resolver(null), { once: true });
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const erro = $(".erro-texto", d);
      const botao = $("button[type=submit]", form);
      botao.disabled = true;
      try { fechar(await aoEnviar(new FormData(form))); }
      catch (err) { if (erro) erro.textContent = err.message; botao.disabled = false; }
    });
  });
}

export function parametrosHash() {
  const [, consulta = ""] = location.hash.split("?");
  return new URLSearchParams(consulta);
}
