// Configuração e funções comuns às duas páginas.
// Vazio = mesma origem: as páginas e a API são servidas pelo mesmo Flask.
const API_URL = "";

class ApiError extends Error {
  constructor(status, codigo, mensagem) {
    super(mensagem);
    this.status = status;
    this.codigo = codigo;
  }
}

function sair(motivo) {
  sessionStorage.removeItem("token");
  sessionStorage.removeItem("usuario");
  location.replace("/" + (motivo ? "?motivo=" + motivo : ""));
}

// Faz a requisição já com o token e traduz erros HTTP em ApiError.
async function api(caminho, { metodo = "GET", corpo } = {}) {
  const token = sessionStorage.getItem("token");
  const headers = {};
  if (corpo !== undefined) headers["Content-Type"] = "application/json";
  if (token) headers["Authorization"] = "Bearer " + token;

  let resposta;
  try {
    resposta = await fetch(API_URL + caminho, {
      method: metodo,
      headers,
      body: corpo !== undefined ? JSON.stringify(corpo) : undefined,
    });
  } catch (e) {
    throw new ApiError(0, "sem_conexao", "Não foi possível conectar ao servidor. A API está rodando?");
  }

  const dados = await resposta.json().catch(() => null);

  if (!resposta.ok) {
    // Token expirado/inválido numa tela protegida: volta para o login.
    if (resposta.status === 401 && token) sair("expirado");
    throw new ApiError(
      resposta.status,
      dados?.erro || "erro",
      dados?.mensagem || "Erro inesperado (" + resposta.status + ")."
    );
  }
  return dados;
}

// Evita que texto vindo da API seja interpretado como HTML.
function esc(texto) {
  return String(texto ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}
