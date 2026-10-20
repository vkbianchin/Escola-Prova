const form = document.getElementById("form-login");
const caixaErro = document.getElementById("erro-login");
const botao = document.getElementById("btn-entrar");

// Quem já está logado vai direto para o painel.
if (sessionStorage.getItem("token")) location.replace("/painel");

function mostrarErro(texto) {
  caixaErro.textContent = texto;
  caixaErro.hidden = false;
}

if (new URLSearchParams(location.search).get("motivo") === "expirado") {
  mostrarErro("Sua sessão expirou. Faça login novamente.");
}

form.addEventListener("submit", async (evento) => {
  evento.preventDefault();
  caixaErro.hidden = true;

  const email = document.getElementById("email").value.trim();
  const senha = document.getElementById("senha").value;
  if (!email || !senha) {
    mostrarErro("Informe e-mail e senha.");
    return;
  }

  botao.disabled = true;
  botao.textContent = "Entrando...";
  try {
    const dados = await api("/auth/login", { metodo: "POST", corpo: { email, senha } });
    sessionStorage.setItem("token", dados.token);
    sessionStorage.setItem("usuario", JSON.stringify(dados.usuario));
    location.replace("/painel");
  } catch (e) {
    mostrarErro(e.message);
    botao.disabled = false;
    botao.textContent = "Entrar";
  }
});
