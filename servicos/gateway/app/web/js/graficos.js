// Gráficos em SVG puro (sem bibliotecas externas: a política CSP só permite arquivos do próprio servidor).
"use strict";
import { esc } from "./util.js";

// Linhas: abertos x resolvidos por dia
export function linhas(serie) {
  const L = 560, A = 230, m = { e: 30, d: 22, t: 14, b: 28 };
  const max = Math.max(1, ...serie.flatMap((p) => [p.abertos, p.resolvidos]));
  const x = (i) => m.e + (i * (L - m.e - m.d)) / Math.max(1, serie.length - 1);
  const y = (v) => A - m.b - (v * (A - m.t - m.b)) / max;
  const passo = Math.max(1, Math.ceil(max / 4));
  let grade = "";
  for (let v = 0; v <= max; v += passo) grade += `<line class="l-grade" x1="${m.e}" x2="${L - m.d}" y1="${y(v)}" y2="${y(v)}"/><text x="${m.e - 8}" y="${y(v) + 4}" text-anchor="end">${v}</text>`;
  const caminho = (campo) => serie.map((p, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(p[campo]).toFixed(1)}`).join(" ");
  const area = `${caminho("abertos")} L${x(serie.length - 1)},${y(0)} L${x(0)},${y(0)} Z`;
  const rotulos = serie.map((p, i) => (i % 2 === serie.length % 2 ? "" : `<text x="${x(i)}" y="${A - 6}" text-anchor="middle">${esc(p.dia.slice(8, 10))}/${esc(p.dia.slice(5, 7))}</text>`)).join("");
  const pontos = (campo, classe) => serie.map((p, i) => `<circle class="${classe}" cx="${x(i)}" cy="${y(p[campo])}" r="3"><title>${esc(p.dia)}: ${p[campo]}</title></circle>`).join("");
  return `<svg class="grafico" viewBox="0 0 ${L} ${A}" role="img" aria-label="Chamados abertos e resolvidos por dia">
    ${grade}<path class="a-azul" d="${area}"/><path class="l-azul" d="${caminho("abertos")}"/><path class="l-verde" d="${caminho("resolvidos")}"/>
    ${pontos("abertos", "f-azul")}${pontos("resolvidos", "f-verde")}${rotulos}</svg>
    <div class="legenda"><span><i class="leg-azul"></i>Abertos</span><span><i class="leg-verde"></i>Resolvidos</span></div>`;
}

// Rosca: distribuição por prioridade
export function rosca(dados, rotulos) {
  const ordem = Object.keys(rotulos);
  const total = ordem.reduce((s, k) => s + (dados[k] || 0), 0);
  const R = 52, C = 2 * Math.PI * R;
  let acumulado = 0;
  const fatias = total ? ordem.map((k) => {
    const v = dados[k] || 0;
    const fatia = `<circle r="${R}" cx="70" cy="70" fill="none" class="s-${k}" stroke-width="22" stroke-dasharray="${(v / total) * C} ${C}" stroke-dashoffset="${-acumulado}" transform="rotate(-90 70 70)"><title>${esc(rotulos[k])}: ${v}</title></circle>`;
    acumulado += (v / total) * C;
    return fatia;
  }).join("") : `<circle r="${R}" cx="70" cy="70" fill="none" stroke="#e3e8f1" stroke-width="22"/>`;
  return `<div class="rosca"><svg class="grafico" viewBox="0 0 140 140" role="img" aria-label="Chamados por prioridade">${fatias}
      <text x="70" y="68" text-anchor="middle" class="rotulo-valor" font-size="22">${total}</text><text x="70" y="86" text-anchor="middle">chamados</text></svg>
    <ul>${ordem.map((k) => `<li><i class="leg-${k}"></i>${esc(rotulos[k])}<b>${dados[k] || 0}</b></li>`).join("")}</ul></div>`;
}

// Barras horizontais: valores por categoria
export function barras(dados, rotulos, classe = "f-azul") {
  const itens = Object.entries(dados).sort((a, b) => b[1] - a[1]);
  if (!itens.length) return `<p class="suave">Sem dados ainda.</p>`;
  const max = Math.max(...itens.map(([, v]) => v));
  const L = 340, linha = 30;
  return `<svg class="grafico" viewBox="0 0 ${L} ${itens.length * linha}" role="img" aria-label="Gráfico de barras">${itens.map(([k, v], i) => {
    const largura = Math.max(2, (v / max) * (L - 150));
    return `<text x="0" y="${i * linha + 19}">${esc(rotulos[k] || k)}</text>
      <rect class="f-trilho" x="118" y="${i * linha + 8}" width="${L - 150}" height="14" rx="4"/>
      <rect class="${classe}" x="118" y="${i * linha + 8}" width="${largura}" height="14" rx="4"/>
      <text class="rotulo-valor" x="${118 + (L - 150) + 6}" y="${i * linha + 19}">${v}</text>`;
  }).join("")}</svg>`;
}

// Barra de progresso do SLA (quanto do prazo já foi consumido)
export function progresso(percentual, classe) {
  const p = Math.max(0, Math.min(100, percentual));
  return `<svg class="barra" viewBox="0 0 100 10" preserveAspectRatio="none" role="img" aria-label="${Math.round(p)}% do prazo consumido">
    <rect class="f-trilho" width="100" height="10" rx="5"/><rect class="${classe}" width="${p}" height="10" rx="5"/></svg>`;
}
