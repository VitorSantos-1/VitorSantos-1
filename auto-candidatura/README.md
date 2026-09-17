# 🎯 Auto-Candidatura

Automação de candidatura a vagas em Python: o **Apify coleta** as vagas, o **app
qualifica e escreve** os e-mails de abordagem contra o seu CV, e **você revisa e
envia**. Inspirado no fluxo de 5 passos (buscar → qualificar → achar quem
contrata → escrever e-mail personalizado → revisar e enviar).

> **Expectativa honesta:** "centenas de candidaturas por dia" é exagero de
> marketing. E-mail bom é personalizado, e personalização não escala pra 300/dia
> sem virar spam — o que **derruba** sua taxa de resposta. O ganho real é fazer
> **20–40 candidaturas boas** no tempo que antes você fazia 5. **Qualidade > volume.**
> O diferencial é e-mail direto pra quem decide, em vez de formulário (onde você
> vira mais um CV numa fila de 300).

---

## Como funciona

```
  ┌─────────┐     ┌──────────────┐     ┌───────────────┐     ┌──────────┐
  │  APIFY  │ ──▶ │  QUALIFICAR  │ ──▶ │   ESCREVER    │ ──▶ │  VOCÊ    │
  │ coleta  │     │ (nota vs CV) │     │ (e-mail/prompt)│    │ revisa+  │
  │ as vagas│     │  local, 0-100│     │  por vaga     │     │ envia ✉️ │
  └─────────┘     └──────────────┘     └───────────────┘     └──────────┘
        └──────────────── mini-CRM em SQLite acompanha tudo ─────────────┘
```

- **Coleta** → Apify (você cria um token grátis).
- **Cérebro** → roda **100% local, sem API paga**: pontua cada vaga contra as
  palavras-chave do seu perfil e gera **prompts prontos** pra você colar no
  **Claude grátis** (claude.ai). Se um dia você colocar uma chave da Claude API
  no `.env`, o app passa a **escrever os e-mails sozinho** (opcional).
- **CRM local** → um SQLite guarda o funil: `novo → qualificado → rascunho →
  enviado → resposta` (e `descartado`).
- **Envio** → o app gera os rascunhos; **quem envia é você** (é o que mantém a
  taxa de resposta alta).

---

## Instalação

Requer **Python 3.9+**.

```bash
cd auto-candidatura
python3 -m venv .venv && source .venv/bin/activate   # opcional, recomendado
pip install -r requirements.txt
```

### Configuração (uma vez só)

```bash
cp .env.example .env                 # cole aqui o token do Apify
cp perfil.exemplo.yaml perfil.yaml   # edite com a sua vaga dos sonhos
cp cv.exemplo.md cv.md               # cole o SEU currículo aqui
```

1. **Token do Apify** — crie a conta grátis em [apify.com](https://apify.com),
   vá em **Settings → Integrations → API token**, copie e cole no `.env`
   (`APIFY_TOKEN=...`).
2. **Perfil** — abra `perfil.yaml` e ajuste: cargo, senioridade, cidade e,
   principalmente, as `skills_obrigatorias` / `desejaveis` / `eliminatorias`.
   Esse recorte define a qualidade de tudo o que vem depois.
3. **CV** — cole seu currículo em `cv.md` (ou aponte `perfil.cv_arquivo` pro
   arquivo certo). Quanto mais completo, melhores a qualificação e os e-mails.

> `.env`, `perfil.yaml` e `cv.md` estão no `.gitignore` — seus dados **não** vão
> pro GitHub.

---

## Uso

O jeito mais rápido — roda tudo de uma vez:

```bash
python -m jobhunter fluxo
```

Ou passo a passo:

```bash
python -m jobhunter buscar        # 1. coleta vagas no Apify
python -m jobhunter qualificar    # 2. pontua as vagas contra o seu perfil
python -m jobhunter escrever      # 3. gera os rascunhos de e-mail (top vagas)
python -m jobhunter listar        # vê todas as vagas e seus status
python -m jobhunter status        # vê o funil e a taxa de resposta
```

Depois de revisar e enviar um e-mail, registre no funil:

```bash
# marque o contato que você descobriu no LinkedIn e o status
python -m jobhunter marcar <id> --status enviado \
    --contato "Ana Souza" --email ana@empresa.com --nota "respondi via LinkedIn tb"
```

`<id>` é o código curto que aparece na tabela (basta o prefixo).
Status possíveis: `novo`, `qualificado`, `rascunho`, `enviado`, `resposta`, `descartado`.

### O que sai

Cada vaga qualificada vira um arquivo em `saidas/rascunhos/` com:

- ✅ um **assunto** sugerido;
- ✉️ um **e-mail base** já preenchido com uma conquista sua (e um link `mailto:`
  que abre direto no seu cliente de e-mail);
- 🧠 o **prompt pronto** pra colar no Claude grátis e deixar o texto redondo —
  **ou**, se você tiver a chave da API, o **e-mail já escrito** pela Claude API;
- um **checklist** de 30 segundos antes de enviar.

---

## Os 3 prompts do fluxo

O app usa os três prompts do post (busca, qualificação e abordagem):

- **Busca** → é a coleta, feita pelo Apify a partir do `busca.cargo`/`local`.
- **Qualificação** → roda local (nota 0–100 explicável); o prompt equivalente pro
  Claude grátis vem dentro de cada rascunho, na seção recolhível.
- **Abordagem** → o prompt que escreve o e-mail personalizado, no topo de cada rascunho.

---

## Achar "quem contrata" (passo 3 do fluxo)

O app não faz login no LinkedIn por você (isso viola os termos e derruba conta).
O fluxo saudável é: com a lista já qualificada em mãos, para cada empresa você
procura no LinkedIn a pessoa que **lidera a área/o time** (não o RH genérico),
confirma o padrão de e-mail (`nome.sobrenome@empresa.com` costuma funcionar; o
[Hunter.io](https://hunter.io) ajuda a validar) e registra com `marcar ... --contato --email`.
Aí é só regenerar o rascunho — ele passa a chamar a pessoa pelo nome.

---

## Trocando o coletor (Actor do Apify)

No `perfil.yaml`, a seção `apify` define qual scraper roda. O exemplo usa um do
Indeed; há vários no [Apify Store](https://apify.com/store) (Indeed, LinkedIn
Jobs, Glassdoor…). Para trocar:

1. Escolha um Actor no Store e veja o **input schema** dele.
2. Ajuste `apify.actor_id` e o bloco `apify.input` (os campos entre chaves —
   `{query}`, `{location}`, `{country}`, `{rows}` — são preenchidos
   automaticamente a partir da sua `busca`).

O app normaliza a saída de qualquer scraper que devolva título, empresa, local,
link e descrição — então costuma funcionar sem mexer em código.

---

## Custos

- **Apify:** plano grátis com créditos mensais; scrapers consomem créditos por
  execução. Buscas pequenas cabem no grátis; volume grande é pago.
- **Claude:** o modo padrão (prompts pro claude.ai) é **grátis**. A escrita
  automática via API é **opcional** e paga por uso — o modelo é configurável em
  `perfil.yaml` (`claude.modelo`); use `claude-sonnet-5` ou `claude-haiku-4-5`
  pra gastar menos por e-mail.

---

## Estrutura

```
auto-candidatura/
├── jobhunter/
│   ├── cli.py         # comandos (buscar, qualificar, escrever, listar, marcar, status, fluxo)
│   ├── coleta.py      # integração com o Apify + normalização das vagas
│   ├── qualifica.py   # pontuação local da vaga vs. seu perfil
│   ├── escreve.py     # gera os arquivos de rascunho
│   ├── claude.py      # prompts prontos + escrita opcional via Claude API
│   ├── tracker.py     # mini-CRM em SQLite
│   ├── modelos.py     # a estrutura Vaga e os status do funil
│   └── config.py / util.py
├── perfil.exemplo.yaml
├── cv.exemplo.md
├── .env.example
└── requirements.txt
```

---

## Aviso

Use com responsabilidade: respeite os termos de uso dos sites, não faça envio em
massa nem spam. A ferramenta existe pra você candidatar-se **melhor** — com
pesquisa e mensagem personalizada — não pra disparar e-mail genérico em volume.
