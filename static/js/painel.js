// ---------------------------------------------------------------- sessão
const usuario = JSON.parse(sessionStorage.getItem("usuario") || "null");
if (!usuario || !sessionStorage.getItem("token")) {
  location.replace("/");
}

const ROTULO_PAPEL = { comum: "Usuário comum", gestor: "Gestor", admin: "Administrador" };
const ROTULO_STATUS = {
  disponivel: "Disponível",
  emprestado: "Emprestado",
  manutencao: "Em manutenção",
  solicitado: "Solicitado",
  aprovado: "Aprovado",
  recusado: "Recusado",
  devolvido: "Devolvido",
};

const el = (id) => document.getElementById(id);
const ehComum = usuario?.papel === "comum";
const ehGestor = usuario?.papel === "gestor";
const ehAdmin = usuario?.papel === "admin";

// ---------------------------------------------------------------- avisos
let temporizadorAviso;
function mostrarAviso(texto, tipo = "ok") {
  const caixa = el("aviso");
  caixa.textContent = texto;
  caixa.className = "mensagem " + tipo;
  caixa.hidden = false;
  clearTimeout(temporizadorAviso);
  temporizadorAviso = setTimeout(() => (caixa.hidden = true), 6000);
}

function formatarData(iso) {
  return iso ? new Date(iso).toLocaleString("pt-BR") : "—";
}

function selo(status) {
  return `<span class="selo status-${esc(status)}">${esc(ROTULO_STATUS[status] || status)}</span>`;
}

// ---------------------------------------------------------------- equipamentos
async function carregarEquipamentos() {
  try {
    const lista = await api("/equipamentos");
    const corpo = el("tbody-equipamentos");
    if (!lista.length) {
      corpo.innerHTML = `<tr><td colspan="5" class="vazio">Nenhum equipamento cadastrado.</td></tr>`;
      return;
    }
    corpo.innerHTML = lista
      .map((e) => {
        let acao = "";
        if (ehComum) {
          acao =
            e.status === "disponivel"
              ? `<td><button class="botao primario pequeno" data-acao="solicitar" data-id="${e.id}">Solicitar</button></td>`
              : `<td>—</td>`;
        }
        return `<tr>
          <td>${esc(e.nome)}</td>
          <td>${esc(e.codigo_patrimonio)}</td>
          <td>${esc(e.descricao || "—")}</td>
          <td>${selo(e.status)}</td>
          ${acao}
        </tr>`;
      })
      .join("");
  } catch (e) {
    mostrarAviso(e.message, "erro");
  }
}

// ---------------------------------------------------------------- empréstimos
function botoesGestor(emp) {
  if (emp.status === "solicitado") {
    return `<button class="botao primario pequeno" data-acao="aprovar" data-id="${emp.id}">Aprovar</button>
            <button class="botao perigo pequeno" data-acao="recusar" data-id="${emp.id}">Recusar</button>`;
  }
  if (emp.status === "aprovado") {
    return `<button class="botao primario pequeno" data-acao="devolver" data-id="${emp.id}">Registrar devolução</button>`;
  }
  return "—";
}

async function carregarEmprestimos() {
  try {
    const status = ehComum ? "" : el("select-status").value;
    const lista = await api("/emprestimos" + (status ? "?status=" + status : ""));
    const corpo = el("tbody-emprestimos");
    const colunas = 5 + (ehGestor ? 1 : 0);
    if (!lista.length) {
      corpo.innerHTML = `<tr><td colspan="${colunas}" class="vazio">Nenhum empréstimo encontrado.</td></tr>`;
      return;
    }
    corpo.innerHTML = lista
      .map(
        (emp) => `<tr>
          <td>${emp.id}</td>
          <td>${esc(emp.equipamento_nome)} <small>(${esc(emp.codigo_patrimonio)})</small></td>
          <td>${esc(emp.usuario_nome)}</td>
          <td>${formatarData(emp.data_solicitacao)}</td>
          <td>${selo(emp.status)}${emp.observacao ? `<br><small>${esc(emp.observacao)}</small>` : ""}</td>
          ${ehGestor ? `<td class="acoes">${botoesGestor(emp)}</td>` : ""}
        </tr>`
      )
      .join("");
  } catch (e) {
    mostrarAviso(e.message, "erro");
  }
}

function recarregarTudo() {
  return Promise.all([carregarEquipamentos(), carregarEmprestimos()]);
}

// ---------------------------------------------------------------- ações
const ACOES = {
  solicitar: (id) => ({
    caminho: "/emprestimos",
    metodo: "POST",
    corpo: { equipamento_id: Number(id) },
    sucesso: "Empréstimo solicitado. Aguarde a aprovação do gestor.",
  }),
  aprovar: (id) => ({
    caminho: `/emprestimos/${id}/aprovar`,
    metodo: "PATCH",
    sucesso: "Empréstimo aprovado.",
  }),
  recusar: (id) => {
    const motivo = prompt("Motivo da recusa (opcional):");
    if (motivo === null) return null; // cancelou
    return {
      caminho: `/emprestimos/${id}/recusar`,
      metodo: "PATCH",
      corpo: { observacao: motivo },
      sucesso: "Empréstimo recusado.",
    };
  },
  devolver: (id) => ({
    caminho: `/emprestimos/${id}/devolver`,
    metodo: "PATCH",
    sucesso: "Devolução registrada.",
  }),
};

document.addEventListener("click", async (evento) => {
  const botao = evento.target.closest("button[data-acao]");
  if (!botao) return;

  const definicao = ACOES[botao.dataset.acao]?.(botao.dataset.id);
  if (!definicao) return;

  botao.disabled = true;
  try {
    await api(definicao.caminho, { metodo: definicao.metodo, corpo: definicao.corpo });
    mostrarAviso(definicao.sucesso, "ok");
  } catch (e) {
    mostrarAviso(e.message, "erro");
  }
  await recarregarTudo();
});

el("form-equipamento").addEventListener("submit", async (evento) => {
  evento.preventDefault();
  const corpo = {
    nome: el("eq-nome").value.trim(),
    codigo_patrimonio: el("eq-patrimonio").value.trim(),
    descricao: el("eq-descricao").value.trim(),
  };
  if (!corpo.nome || !corpo.codigo_patrimonio) {
    mostrarAviso("Preencha o nome e o código de patrimônio.", "erro");
    return;
  }
  try {
    await api("/equipamentos", { metodo: "POST", corpo });
    evento.target.reset();
    mostrarAviso("Equipamento cadastrado.", "ok");
    await carregarEquipamentos();
  } catch (e) {
    mostrarAviso(e.message, "erro");
  }
});

el("select-status").addEventListener("change", carregarEmprestimos);
el("btn-sair").addEventListener("click", () => sair());

// ---------------------------------------------------------------- montagem da tela por papel
// Esconder partes da tela é só conveniência: quem garante a segurança é o back-end.
function montarTela() {
  el("nome-usuario").textContent = usuario.nome;
  const seloPapel = el("papel-usuario");
  seloPapel.textContent = ROTULO_PAPEL[usuario.papel] || usuario.papel;
  seloPapel.classList.add("papel-" + usuario.papel);

  el("sec-cadastro").hidden = !ehAdmin;
  el("th-acao-equip").hidden = !ehComum;
  el("th-acao-emp").hidden = !ehGestor;
  el("filtro-status").hidden = ehComum;
  el("titulo-emprestimos").textContent = ehComum ? "Meus empréstimos" : "Empréstimos";
  el("th-solicitante").hidden = false;

  // O gestor abre direto nos pedidos pendentes.
  if (ehGestor) el("select-status").value = "solicitado";
}

if (usuario) {
  montarTela();
  recarregarTudo();
}
