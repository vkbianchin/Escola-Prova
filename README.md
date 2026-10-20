# Operação "Cadê o Equipamento?" — Avaliação Prática 3

Sistema de empréstimo de equipamentos do almoxarifado com **login** e **proteção das rotas por papel de usuário**.

SENAC Videira — Professor Ricardo Köhler

## Tecnologias

| Camada | Tecnologia |
|---|---|
| Banco de dados | MySQL 8+ |
| Back-end | Python 3 + Flask, PyJWT (token), bcrypt (hash de senha) |
| Front-end | HTML, CSS e JavaScript puros |

## Estrutura do projeto

```
cade-o-equipamento/
├── .gitignore
├── README.md
├── database/
│   └── schema.sql          # criação do banco e das tabelas
├── backend/
│   ├── app.py              # rotas e tratamento central de exceções
│   ├── auth.py             # hash de senha, JWT e decoradores de permissão
│   ├── config.py           # leitura do .env
│   ├── db.py               # conexão e transações com o MySQL
│   ├── exceptions.py       # exceções de domínio (401, 403, 404, 409, 400)
│   ├── seed.py             # cria usuários e equipamentos de teste
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── index.html          # login
    ├── painel.html         # painel (muda conforme o papel)
    ├── css/style.css
    └── js/ (api.js, login.js, painel.js)
```

## Papéis e permissões

| Papel | Pode |
|---|---|
| **comum** | Solicitar empréstimos |
| **gestor** | Aprovar/recusar empréstimos e registrar devoluções |
| **admin** | Cadastrar equipamentos |

Cada ação pertence a **um único papel**: o gestor não cadastra equipamentos e o administrador não aprova empréstimos.

## Como executar

### 1. Banco de dados

```
mysql -u root -p < database/schema.sql
```

### 2. Back-end

```
cd backend
python -m venv .venv
.venv\Scripts\activate          # Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env          # Linux/Mac: cp .env.example .env
```

Edite o `.env` e coloque a senha do seu MySQL em `DB_PASSWORD`. Depois:

```
python seed.py                  # cria os usuários e equipamentos de teste
python app.py                   # API em http://127.0.0.1:5000
```

### 3. Front-end

Em outro terminal, dentro da pasta `frontend`:

```
python -m http.server 5500
```

Abra `http://localhost:5500`. (Também funciona com a extensão Live Server do VS Code.)

### Usuários de teste

| Papel | E-mail | Senha |
|---|---|---|
| admin | admin@senac.com | Admin@123 |
| gestor | gestor@senac.com | Gestor@123 |
| comum | comum@senac.com | Comum@123 |

## Rotas da API

| Método | Rota | Quem pode |
|---|---|---|
| POST | `/auth/login` | Público |
| GET | `/auth/me` | Qualquer usuário logado |
| GET | `/equipamentos` | Qualquer usuário logado |
| POST | `/equipamentos` | **admin** |
| GET | `/emprestimos` | Logado (comum vê só os seus; gestor e admin veem todos). Filtro opcional: `?status=solicitado` |
| POST | `/emprestimos` | **comum** |
| PATCH | `/emprestimos/<id>/aprovar` | **gestor** |
| PATCH | `/emprestimos/<id>/recusar` | **gestor** |
| PATCH | `/emprestimos/<id>/devolver` | **gestor** |

As rotas protegidas exigem o cabeçalho `Authorization: Bearer <token>`, obtido no login.

## Tratamento de exceções

As falhas viram exceções de domínio (`exceptions.py`), tratadas em um único ponto (`app.py`) e devolvidas como JSON `{"erro": "...", "mensagem": "..."}` com o código HTTP semântico:

| Código | Exceção | Quando acontece |
|---|---|---|
| 400 | `DadosInvalidos` | Corpo ausente ou campo obrigatório vazio |
| 401 | `NaoAutenticado` | Sem token, token inválido/expirado ou login incorreto |
| 403 | `SemPermissao` | Usuário logado, mas com papel que não permite a ação |
| 404 | `NaoEncontrado` | Equipamento ou empréstimo inexistente |
| 409 | `Conflito` | Equipamento indisponível, pedido duplicado, status que não permite a transição, patrimônio duplicado |
| 503 | — | Falha ao acessar o banco de dados |
| 500 | — | Erro inesperado |

## Roteiro de testes das permissões

Faça login com cada usuário e confira o resultado esperado:

| Ação | Sem login | comum | gestor | admin |
|---|---|---|---|---|
| `POST /equipamentos` | 401 | **403** | **403** | 201 |
| `POST /emprestimos` | 401 | 201 | **403** | **403** |
| `PATCH /emprestimos/<id>/aprovar` | 401 | **403** | 200 | **403** |
| `PATCH /emprestimos/<id>/recusar` | 401 | **403** | 200 | **403** |
| `PATCH /emprestimos/<id>/devolver` | 401 | **403** | 200 | **403** |

Outros casos para testar:

1. Com o **comum**, solicitar um equipamento já emprestado → **409**.
2. Com o **comum**, solicitar um `equipamento_id` que não existe → **404**.
3. Com o **gestor**, aprovar um empréstimo já aprovado → **409**.
4. Com o **gestor**, devolver um empréstimo que ainda está só "solicitado" → **409**.
5. Com o **admin**, cadastrar dois equipamentos com o mesmo código de patrimônio → **409**.
6. Enviar um token adulterado → **401**.

Exemplo de teste direto na API (Git Bash ou Linux):

```
TOKEN=$(curl -s -X POST http://127.0.0.1:5000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"comum@senac.com","senha":"Comum@123"}' | python -c "import sys,json;print(json.load(sys.stdin)['token'])")

# comum tentando cadastrar equipamento -> deve retornar 403
curl -i -X POST http://127.0.0.1:5000/equipamentos \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"nome":"Teste","codigo_patrimonio":"X-1"}'
```

## Observações de segurança

- Senhas são guardadas com **bcrypt** (nunca em texto puro).
- O papel do usuário é lido do **banco** a cada requisição, não apenas do token.
- A segurança é garantida no **back-end**; esconder botões no front é só conveniência.
- O arquivo `.env` (senha do banco e chave do JWT) **não** vai para o repositório.
