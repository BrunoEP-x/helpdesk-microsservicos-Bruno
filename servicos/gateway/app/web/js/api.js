// Comunicação com o API Gateway. A tela é servida pelo próprio gateway, então as rotas são relativas.
"use strict";

let token = null;
try { token = sessionStorage.getItem("token"); } catch (e) { token = null; }
let aoExpirar = () => {};

export const temToken = () => Boolean(token);
export const definirAoExpirar = (fn) => { aoExpirar = fn; };
export function guardarToken(t) {
  token = t;
  try { t ? sessionStorage.setItem("token", t) : sessionStorage.removeItem("token"); } catch (e) { /* modo privado */ }
}

function mensagemDeErro(dados, status) {
  if (typeof dados.detail === "string") return dados.detail;
  if (Array.isArray(dados.detail) && dados.detail.length) {
    const d = dados.detail[0];
    const campo = Array.isArray(d.loc) ? d.loc[d.loc.length - 1] : "";
    return `Confira o campo "${campo}": ${d.msg}`;
  }
  return `Não foi possível concluir (erro ${status}).`;
}

export async function req(metodo, caminho, corpo) {
  const cab = { "Content-Type": "application/json" };
  if (token) cab.Authorization = "Bearer " + token;
  let r;
  try {
    r = await fetch(caminho, { method: metodo, headers: cab, body: corpo !== undefined ? JSON.stringify(corpo) : undefined });
  } catch (e) {
    throw new Error("Sem conexão com o servidor. Verifique a rede.");
  }
  if (r.status === 204) return null;
  const dados = await r.json().catch(() => ({}));
  if (r.status === 401 && caminho !== "/auth/login") { aoExpirar(); throw new Error("Sessão expirada. Entre novamente."); }
  if (!r.ok) { const erro = new Error(mensagemDeErro(dados, r.status)); erro.status = r.status; throw erro; }
  return dados;
}

export const get = (c) => req("GET", c);
export const post = (c, d) => req("POST", c, d ?? {});
export const patch = (c, d) => req("PATCH", c, d);
export const put = (c, d) => req("PUT", c, d);

// Baixa um arquivo protegido por login (o token vai no cabeçalho, nunca na URL)
export async function baixar(caminho, nomeArquivo) {
  const r = await fetch(caminho, { headers: { Authorization: "Bearer " + token } });
  if (!r.ok) throw new Error("Não foi possível gerar o arquivo.");
  const url = URL.createObjectURL(await r.blob());
  const a = document.createElement("a");
  a.href = url; a.download = nomeArquivo; document.body.append(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

// Busca vários recursos sem deixar a falha de um derrubar os outros
export async function varios(caminhos) {
  const resultados = await Promise.allSettled(caminhos.map(get));
  return resultados.map((r) => (r.status === "fulfilled" ? { ok: true, dados: r.value } : { ok: false, erro: r.reason.message }));
}
