"""Carrega o perfil (YAML) e as variáveis de ambiente (.env)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

try:
    from dotenv import load_dotenv
except ImportError:  # dotenv é conveniência, não obrigatório
    def load_dotenv(*_args, **_kwargs):  # type: ignore
        return False


CAMINHO_PADRAO = "perfil.yaml"


class ConfigError(Exception):
    pass


class Config:
    """Junta o perfil do YAML com os segredos do ambiente."""

    def __init__(self, dados: dict[str, Any]):
        self.dados = dados
        # Segredos SEMPRE vêm do ambiente, nunca do YAML (que vai pro git).
        self.apify_token = os.environ.get("APIFY_TOKEN", "").strip()
        self.anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()

    # ---- atalhos de leitura do perfil ------------------------------------
    def get(self, *chaves: str, padrao: Any = None) -> Any:
        no: Any = self.dados
        for chave in chaves:
            if not isinstance(no, dict) or chave not in no:
                return padrao
            no = no[chave]
        return no

    @property
    def perfil(self) -> dict[str, Any]:
        return self.dados.get("perfil", {})

    @property
    def busca(self) -> dict[str, Any]:
        return self.dados.get("busca", {})

    @property
    def apify(self) -> dict[str, Any]:
        return self.dados.get("apify", {})

    @property
    def email(self) -> dict[str, Any]:
        return self.dados.get("email", {})

    @property
    def tem_claude(self) -> bool:
        return bool(self.anthropic_key)

    @property
    def caminho_cv(self) -> str:
        return str(self.perfil.get("cv_arquivo", "")).strip()


def carregar(caminho: str | None = None) -> Config:
    """Lê o .env (se existir) e o perfil YAML."""
    load_dotenv()  # procura .env no diretório atual

    caminho = caminho or CAMINHO_PADRAO
    p = Path(caminho)
    if not p.exists():
        raise ConfigError(
            f"Perfil '{caminho}' não encontrado.\n"
            f"Copie 'perfil.exemplo.yaml' para '{caminho}' e edite com os seus dados."
        )
    try:
        dados = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        raise ConfigError(f"Erro lendo o YAML '{caminho}': {e}") from e
    if not isinstance(dados, dict):
        raise ConfigError(f"O perfil '{caminho}' precisa ser um mapa YAML (chave: valor).")
    return Config(dados)
