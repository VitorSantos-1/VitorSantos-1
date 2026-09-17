"""Ponte com o Claude.

Duas formas de uso:

1. SEM chave paga (padrão): a gente gera PROMPTS prontos pra você colar no
   Claude grátis (claude.ai). O app faz o trabalho chato de montar o prompt
   com a vaga + seu CV + suas regras.

2. COM chave (opcional): se ANTHROPIC_API_KEY estiver no .env, o app chama a
   Claude API e já devolve o e-mail escrito. Modelo configurável no perfil.yaml.
"""

from __future__ import annotations

from .config import Config
from .modelos import Vaga
from .util import trecho


# --------------------------------------------------------------------------
# Prompts prontos (caminho gratuito) — os 3 do post: busca, qualificação e
# abordagem. 'busca' é informativo (a coleta é feita pelo Apify).
# --------------------------------------------------------------------------
def prompt_qualificacao(vaga: Vaga, cfg: Config, cv_texto: str) -> str:
    perfil = cfg.perfil
    return f"""Você é meu conselheiro de carreira. Avalie se esta vaga vale a candidatura.

MEU CV:
\"\"\"{cv_texto.strip()[:4000]}\"\"\"

MEU OBJETIVO: {perfil.get('cargo_alvo', '')} ({cfg.busca.get('senioridade', '')}), {cfg.busca.get('local', '')}.

VAGA:
- Título: {vaga.titulo}
- Empresa: {vaga.empresa}
- Local: {vaga.local}
- Link: {vaga.url}
- Descrição: {trecho(vaga.descricao, 1200)}

Responda em 3 linhas:
1) Nota de 0 a 10 de aderência e por quê.
2) O que do meu CV eu devo destacar pra esta vaga.
3) Algum requisito eliminatório que eu não tenho? (sim/não + qual)"""


def prompt_abordagem(vaga: Vaga, cfg: Config, cv_texto: str) -> str:
    perfil = cfg.perfil
    contato = vaga.contato_nome or "a pessoa que lidera a área/o time"
    return f"""Escreva um e-mail curto de candidatura direta (máx. 120 palavras), em português, \
para {contato} da empresa {vaga.empresa}, sobre a vaga "{vaga.titulo}".

Regras:
- Cite 1 detalhe específico da vaga ou da empresa (mostra que li de verdade).
- Conecte com 1 conquista concreta minha, com número se possível.
- Tom humano e direto, nada de "venho por meio desta".
- CTA leve: uma conversa de 15 min.
- Gere também uma linha de ASSUNTO que dê vontade de abrir.

MEU CV (use pra achar a conquista certa):
\"\"\"{cv_texto.strip()[:3500]}\"\"\"

DADOS DA VAGA:
- Local: {vaga.local}
- Link: {vaga.url}
- Descrição: {trecho(vaga.descricao, 1000)}

Formato da resposta:
ASSUNTO: <linha de assunto>
---
<corpo do e-mail>"""


# --------------------------------------------------------------------------
# Caminho automático (opcional, requer ANTHROPIC_API_KEY)
# --------------------------------------------------------------------------
_SYSTEM = (
    "Você escreve e-mails de candidatura direta que soam humanos, específicos "
    "e respeitosos. Nunca invente conquistas: use só o que estiver no CV. "
    "Seja conciso. Responda exatamente no formato pedido."
)


def escrever_email_api(vaga: Vaga, cfg: Config, cv_texto: str) -> str:
    """Chama a Claude API pra escrever o e-mail. Só use se cfg.tem_claude."""
    import anthropic  # import tardio: só carrega se for usar

    client = anthropic.Anthropic(api_key=cfg.anthropic_key)
    modelo = str(cfg.get("claude", "modelo", padrao="claude-opus-5"))

    resp = client.messages.create(
        model=modelo,
        max_tokens=1200,
        system=_SYSTEM,
        messages=[{"role": "user", "content": prompt_abordagem(vaga, cfg, cv_texto)}],
    )
    partes = [b.text for b in resp.content if getattr(b, "type", "") == "text"]
    return "\n".join(partes).strip()
