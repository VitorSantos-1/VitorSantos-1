"""Coleta de vagas via Apify. O Apify roda o 'Actor' (scraper) escolhido no
perfil e devolve um dataset; aqui a gente normaliza pra o formato Vaga."""

from __future__ import annotations

import copy
from typing import Any

from .config import Config
from .modelos import Vaga

# Mapeia possíveis nomes de campo na saída de vários actors -> nossos campos.
# Assim o app funciona com scrapers diferentes de Indeed/LinkedIn/etc.
_ALIAS = {
    "titulo": ["title", "jobTitle", "position", "positionName", "job_title"],
    "empresa": ["company", "companyName", "employer", "company_name", "hiringOrganization"],
    "local": ["location", "jobLocation", "formattedLocation", "place", "city"],
    "url": ["url", "jobUrl", "link", "applyUrl", "externalApplyLink",
            "detailsUrl", "job_url", "apply_link"],
    "descricao": ["description", "descriptionText", "jobDescription",
                  "snippet", "description_text", "summary"],
}


def _primeiro(item: dict[str, Any], nomes: list[str]) -> str:
    for nome in nomes:
        val = item.get(nome)
        if isinstance(val, dict):  # ex.: hiringOrganization: {name: ...}
            val = val.get("name") or val.get("displayName")
        if val:
            return str(val).strip()
    return ""


def normalizar_item(item: dict[str, Any], fonte: str) -> Vaga | None:
    titulo = _primeiro(item, _ALIAS["titulo"])
    empresa = _primeiro(item, _ALIAS["empresa"])
    url = _primeiro(item, _ALIAS["url"])
    if not titulo and not url:
        return None  # item sem nada útil
    local = _primeiro(item, _ALIAS["local"])
    descricao = _primeiro(item, _ALIAS["descricao"])
    return Vaga(
        id=Vaga.gerar_id(url, titulo, empresa),
        titulo=titulo or "(sem título)",
        empresa=empresa or "(empresa não informada)",
        local=local,
        url=url,
        descricao=descricao,
        fonte=fonte,
    )


def _substituir(template: Any, vars: dict[str, Any]) -> Any:
    """Substitui {query}/{location}/{rows} recursivamente no input do actor."""
    if isinstance(template, str):
        try:
            return template.format(**vars)
        except (KeyError, IndexError, ValueError):
            return template
    if isinstance(template, list):
        return [_substituir(x, vars) for x in template]
    if isinstance(template, dict):
        return {k: _substituir(v, vars) for k, v in template.items()}
    if isinstance(template, int) and "rows" in str(template):
        return template
    return template


def montar_input(cfg: Config) -> tuple[str, dict[str, Any]]:
    apify = cfg.apify
    actor_id = str(apify.get("actor_id", "")).strip()
    if not actor_id:
        raise ValueError(
            "Defina 'apify.actor_id' no perfil.yaml "
            "(ex.: 'misceres/indeed-scraper')."
        )
    busca = cfg.busca
    vars = {
        "query": busca.get("cargo", ""),
        "location": busca.get("local", ""),
        "rows": int(busca.get("max_vagas", 40)),
        "country": busca.get("pais", "BR"),
    }
    template = copy.deepcopy(apify.get("input", {}))
    run_input = _substituir(template, vars)
    return actor_id, run_input


def buscar(cfg: Config) -> list[Vaga]:
    """Roda o actor no Apify e devolve as vagas normalizadas."""
    if not cfg.apify_token:
        raise RuntimeError(
            "APIFY_TOKEN não definido. Crie sua conta em apify.com, "
            "pegue o token em Settings → Integrations e coloque no arquivo .env."
        )
    try:
        from apify_client import ApifyClient
    except ImportError as e:
        raise RuntimeError(
            "Pacote 'apify-client' não instalado. Rode: pip install -r requirements.txt"
        ) from e

    actor_id, run_input = montar_input(cfg)
    client = ApifyClient(cfg.apify_token)

    run = client.actor(actor_id).call(run_input=run_input)
    if run is None:
        raise RuntimeError("O Apify não retornou execução (run vazio).")
    dataset_id = run.get("defaultDatasetId")
    if not dataset_id:
        raise RuntimeError("Execução do Apify sem dataset de saída.")

    vagas: list[Vaga] = []
    vistos: set[str] = set()
    for item in client.dataset(dataset_id).iterate_items():
        vaga = normalizar_item(item, fonte=actor_id)
        if vaga and vaga.id not in vistos:
            vistos.add(vaga.id)
            vagas.append(vaga)
    return vagas
