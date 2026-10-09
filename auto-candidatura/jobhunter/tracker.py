"""Mini-CRM em SQLite: guarda vagas e o estado de cada candidatura."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from .modelos import Vaga, _agora

CAMINHO_DB_PADRAO = "dados/candidaturas.db"

_COLUNAS = [
    "id", "titulo", "empresa", "local", "url", "descricao", "fonte",
    "score", "motivo", "palavras_ok", "palavras_faltando",
    "contato_nome", "contato_email", "status", "notas",
    "criado_em", "atualizado_em",
]


class Tracker:
    def __init__(self, caminho: str = CAMINHO_DB_PADRAO):
        Path(caminho).parent.mkdir(parents=True, exist_ok=True)
        self.con = sqlite3.connect(caminho)
        self.con.row_factory = sqlite3.Row
        self._migrar()

    def _migrar(self) -> None:
        self.con.execute(
            """
            CREATE TABLE IF NOT EXISTS vagas (
                id TEXT PRIMARY KEY,
                titulo TEXT, empresa TEXT, local TEXT, url TEXT,
                descricao TEXT, fonte TEXT,
                score INTEGER DEFAULT 0, motivo TEXT,
                palavras_ok TEXT, palavras_faltando TEXT,
                contato_nome TEXT, contato_email TEXT,
                status TEXT DEFAULT 'novo', notas TEXT,
                criado_em TEXT, atualizado_em TEXT
            )
            """
        )
        self.con.commit()

    # ---- escrita ---------------------------------------------------------
    def upsert(self, vaga: Vaga) -> bool:
        """Insere vaga nova. Retorna True se inseriu, False se já existia
        (nesse caso NÃO sobrescreve — preserva score/status/notas seus)."""
        existe = self.con.execute(
            "SELECT 1 FROM vagas WHERE id = ?", (vaga.id,)
        ).fetchone()
        if existe:
            return False
        d = vaga.dict()
        cols = ", ".join(_COLUNAS)
        marc = ", ".join("?" for _ in _COLUNAS)
        self.con.execute(
            f"INSERT INTO vagas ({cols}) VALUES ({marc})",
            [d[c] for c in _COLUNAS],
        )
        self.con.commit()
        return True

    def salvar(self, vaga: Vaga) -> None:
        """Atualiza uma vaga existente por completo."""
        vaga.atualizado_em = _agora()
        d = vaga.dict()
        sets = ", ".join(f"{c} = ?" for c in _COLUNAS if c != "id")
        self.con.execute(
            f"UPDATE vagas SET {sets} WHERE id = ?",
            [d[c] for c in _COLUNAS if c != "id"] + [vaga.id],
        )
        self.con.commit()

    def atualizar_campos(self, vaga_id: str, **campos) -> int:
        campos["atualizado_em"] = _agora()
        sets = ", ".join(f"{k} = ?" for k in campos)
        cur = self.con.execute(
            f"UPDATE vagas SET {sets} WHERE id = ?",
            list(campos.values()) + [vaga_id],
        )
        self.con.commit()
        return cur.rowcount

    # ---- leitura ---------------------------------------------------------
    def obter(self, vaga_id: str) -> Vaga | None:
        row = self.con.execute(
            "SELECT * FROM vagas WHERE id = ? OR id LIKE ?",
            (vaga_id, vaga_id + "%"),
        ).fetchone()
        return Vaga.from_row(dict(row)) if row else None

    def listar(self, status: str | None = None, limite: int | None = None,
               ordem: str = "score") -> list[Vaga]:
        sql = "SELECT * FROM vagas"
        args: list = []
        if status:
            sql += " WHERE status = ?"
            args.append(status)
        col = "score" if ordem == "score" else "criado_em"
        sql += f" ORDER BY {col} DESC"
        if limite:
            sql += " LIMIT ?"
            args.append(limite)
        return [Vaga.from_row(dict(r)) for r in self.con.execute(sql, args).fetchall()]

    def contagem_por_status(self) -> dict[str, int]:
        rows = self.con.execute(
            "SELECT status, COUNT(*) n FROM vagas GROUP BY status"
        ).fetchall()
        return {r["status"]: r["n"] for r in rows}

    def close(self) -> None:
        self.con.close()
