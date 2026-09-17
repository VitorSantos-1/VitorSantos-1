"""Qualificação: dá uma nota 0-100 pra cada vaga contra o seu perfil.

Funciona 100% local (sem API paga). Se houver ANTHROPIC_API_KEY no ambiente,
o texto do 'motivo' pode ser refinado, mas a nota-base é sempre determinística
e explicável — você enxerga por que cada vaga combina ou não."""

from __future__ import annotations

from .config import Config
from .modelos import Vaga
from .util import normalizar, contem_palavra


def _pontuar_lista(texto_norm: str, termos: list[str]) -> tuple[list[str], list[str]]:
    presentes, ausentes = [], []
    for termo in termos:
        (presentes if contem_palavra(texto_norm, termo) else ausentes).append(termo)
    return presentes, ausentes


def qualificar(vaga: Vaga, cfg: Config) -> Vaga:
    perfil = cfg.perfil
    busca = cfg.busca

    obrigatorias = [str(x) for x in perfil.get("skills_obrigatorias", []) if str(x).strip()]
    desejaveis = [str(x) for x in perfil.get("skills_desejaveis", []) if str(x).strip()]
    eliminatorias = [str(x) for x in perfil.get("eliminatorias", []) if str(x).strip()]
    senioridade = str(busca.get("senioridade", "")).strip()
    local_alvo = str(busca.get("local", "")).strip()
    remoto_ok = bool(busca.get("aceita_remoto", True))

    texto_norm = normalizar(f"{vaga.titulo}\n{vaga.empresa}\n{vaga.local}\n{vaga.descricao}")

    # 1) Eliminatórias: se aparecer algo que te desqualifica, zera.
    for termo in eliminatorias:
        if contem_palavra(texto_norm, termo):
            vaga.score = 0
            vaga.status = "descartado"
            vaga.motivo = f"Descartada: requisito eliminatório encontrado — '{termo}'."
            vaga.palavras_ok, vaga.palavras_faltando = [], []
            return vaga

    # 2) Skills obrigatórias (peso maior) e desejáveis (peso menor).
    ok_obr, falta_obr = _pontuar_lista(texto_norm, obrigatorias)
    ok_des, _ = _pontuar_lista(texto_norm, desejaveis)

    score = 0.0
    if obrigatorias:
        score += 60.0 * (len(ok_obr) / len(obrigatorias))
    else:
        score += 40.0  # sem obrigatórias definidas, não penaliza tanto
    if desejaveis:
        score += 20.0 * (len(ok_des) / len(desejaveis))

    # 3) Senioridade combinando no título/descrição.
    if senioridade and contem_palavra(texto_norm, senioridade):
        score += 10.0

    # 4) Localização / remoto.
    if remoto_ok and contem_palavra(texto_norm, "remoto") or contem_palavra(texto_norm, "remote"):
        score += 10.0
    elif local_alvo and contem_palavra(texto_norm, local_alvo):
        score += 10.0

    vaga.score = max(0, min(100, round(score)))
    vaga.palavras_ok = ok_obr + ok_des
    vaga.palavras_faltando = falta_obr

    partes = []
    if ok_obr:
        partes.append(f"bate em: {', '.join(ok_obr)}")
    if falta_obr:
        partes.append(f"não menciona: {', '.join(falta_obr)}")
    if senioridade and contem_palavra(texto_norm, senioridade):
        partes.append(f"senioridade '{senioridade}' compatível")
    vaga.motivo = "; ".join(partes) if partes else "sem palavras-chave do perfil no anúncio"

    # Só promove pra 'qualificado' se ainda estiver 'novo' (não mexe no seu funil).
    if vaga.status == "novo":
        limite = int(cfg.get("qualificacao", "score_minimo", padrao=50))
        vaga.status = "qualificado" if vaga.score >= limite else "descartado"
    return vaga
