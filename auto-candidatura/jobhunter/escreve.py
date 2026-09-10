"""Gera, para cada vaga qualificada, um arquivo de rascunho pronto pra revisar.

Cada rascunho traz:
  - um e-mail base já preenchido (template), pra você editar e enviar;
  - a linha 'mailto:' pronta (abre no seu cliente de e-mail);
  - o PROMPT pronto pra colar no Claude grátis e deixar o texto redondo;
  - (se houver ANTHROPIC_API_KEY) o e-mail já escrito pela Claude API.
"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import quote

from .config import Config
from .modelos import Vaga
from .claude import prompt_abordagem, prompt_qualificacao, escrever_email_api
from .util import trecho, aviso


def _assunto_base(vaga: Vaga, perfil: dict) -> str:
    cargo = perfil.get("cargo_alvo") or vaga.titulo
    nome = perfil.get("nome", "").strip()
    sufixo = f" — {nome}" if nome else ""
    return f"{cargo} na {vaga.empresa}?{sufixo}"


def _email_template(vaga: Vaga, cfg: Config) -> str:
    perfil = cfg.perfil
    nome = perfil.get("nome", "[seu nome]")
    destaque = perfil.get("conquista_destaque", "[cite aqui uma conquista sua com número]")
    detalhe = trecho(vaga.descricao, 160) or "[cite algo específico da vaga]"
    saudacao = f"Oi {vaga.contato_nome}," if vaga.contato_nome else "Olá,"
    return (
        f"{saudacao}\n\n"
        f"Vi a vaga de {vaga.titulo} na {vaga.empresa} e um ponto me chamou atenção: "
        f"{detalhe}\n\n"
        f"É exatamente o tipo de desafio com que eu trabalho. {destaque}\n\n"
        f"Faria sentido uma conversa rápida de 15 minutos? Anexo meu CV e fico à disposição.\n\n"
        f"Abraço,\n{nome}"
    )


def _mailto(vaga: Vaga, assunto: str, corpo: str) -> str:
    dest = vaga.contato_email or ""
    return f"mailto:{dest}?subject={quote(assunto)}&body={quote(corpo)}"


def _slug(texto: str) -> str:
    texto = re.sub(r"[^a-zA-Z0-9]+", "-", texto.lower()).strip("-")
    return texto[:40] or "vaga"


def gerar_rascunho(vaga: Vaga, cfg: Config, cv_texto: str, pasta: str) -> str:
    """Escreve o arquivo de rascunho da vaga e devolve o caminho."""
    perfil = cfg.perfil
    Path(pasta).mkdir(parents=True, exist_ok=True)

    assunto = _assunto_base(vaga, perfil)
    template = _email_template(vaga, cfg)

    # E-mail automático via API (opcional).
    email_api = ""
    if cfg.tem_claude:
        try:
            email_api = escrever_email_api(vaga, cfg, cv_texto)
        except Exception as e:  # nunca deixa a falha da API travar o rascunho
            aviso(f"Claude API falhou nesta vaga ({e}); usando template.")

    linhas = [
        f"# {vaga.titulo} — {vaga.empresa}",
        "",
        f"- **Score:** {vaga.score}/100 · **Status:** {vaga.status}",
        f"- **Local:** {vaga.local or '—'}",
        f"- **Link da vaga:** {vaga.url or '—'}",
        f"- **Por que combina:** {vaga.motivo or '—'}",
        f"- **Contato:** {vaga.contato_nome or '(descubra no LinkedIn)'}"
        f" · {vaga.contato_email or '(e-mail a confirmar)'}",
        "",
        "---",
        "",
        "## ✅ Assunto sugerido",
        "",
        assunto,
        "",
        "## ✉️ E-mail (template — edite antes de enviar)",
        "",
        "```",
        template,
        "```",
        "",
        f"**Abrir no seu e-mail:** <{_mailto(vaga, assunto, template)}>",
        "",
    ]

    if email_api:
        linhas += [
            "## 🤖 E-mail escrito pela Claude API",
            "",
            "```",
            email_api,
            "```",
            "",
        ]
    else:
        linhas += [
            "## 🧠 Prompt pronto — cole no Claude grátis (claude.ai) pra deixar redondo",
            "",
            "```",
            prompt_abordagem(vaga, cfg, cv_texto),
            "```",
            "",
            "<details><summary>Prompt de qualificação (opcional)</summary>",
            "",
            "```",
            prompt_qualificacao(vaga, cfg, cv_texto),
            "```",
            "",
            "</details>",
            "",
        ]

    linhas += [
        "---",
        "**Checklist antes de enviar:** nome certo? empresa certa? nenhum "
        "`[placeholder]` esquecido? soa como você? Leia os 30 segundos. 🚀",
    ]

    conteudo = "\n".join(linhas)
    nome_arq = f"{vaga.score:03d}_{_slug(vaga.empresa)}_{vaga.id}.md"
    caminho = Path(pasta) / nome_arq
    caminho.write_text(conteudo, encoding="utf-8")
    return str(caminho)
