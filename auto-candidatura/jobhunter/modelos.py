"""Estruturas de dados centrais do app."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any


# Estados possíveis de uma candidatura no funil (mini-CRM).
STATUS = ["novo", "qualificado", "rascunho", "enviado", "resposta", "descartado"]


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class Vaga:
    """Uma vaga coletada e o estado dela no funil de candidatura."""

    id: str
    titulo: str
    empresa: str
    local: str
    url: str
    descricao: str = ""
    fonte: str = ""                 # de qual actor/fonte veio
    # Enriquecido pela etapa de qualificação:
    score: int = 0
    motivo: str = ""                # por que combina (ou não) com o perfil
    palavras_ok: list[str] = field(default_factory=list)
    palavras_faltando: list[str] = field(default_factory=list)
    # Preenchido por você / pela pesquisa de contato:
    contato_nome: str = ""
    contato_email: str = ""
    # Funil:
    status: str = "novo"
    notas: str = ""
    criado_em: str = field(default_factory=_agora)
    atualizado_em: str = field(default_factory=_agora)

    @staticmethod
    def gerar_id(url: str, titulo: str, empresa: str) -> str:
        """ID estável a partir da vaga, pra deduplicar entre buscas."""
        base = (url or f"{titulo}|{empresa}").strip().lower()
        return hashlib.sha1(base.encode("utf-8")).hexdigest()[:12]

    def dict(self) -> dict[str, Any]:
        d = asdict(self)
        # Listas viram texto simples pra caber no SQLite.
        d["palavras_ok"] = ", ".join(self.palavras_ok)
        d["palavras_faltando"] = ", ".join(self.palavras_faltando)
        return d

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "Vaga":
        row = dict(row)
        for campo in ("palavras_ok", "palavras_faltando"):
            valor = row.get(campo) or ""
            row[campo] = [p.strip() for p in valor.split(",") if p.strip()]
        # Mantém só os campos conhecidos.
        conhecidos = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in row.items() if k in conhecidos})
