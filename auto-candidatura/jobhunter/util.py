"""Utilidades: leitura de CV, normalização de texto e saída no terminal."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path


# ---- terminal (usa rich se disponível, senão print puro) -----------------
try:
    from rich.console import Console
    _console = Console()

    def out(msg: str = "") -> None:
        _console.print(msg)
except ImportError:  # pragma: no cover
    def out(msg: str = "") -> None:
        # Remove marcações estilo [bold]…[/bold] quando não há rich.
        print(re.sub(r"\[/?[a-z0-9 #]+\]", "", msg))


def erro(msg: str) -> None:
    out(f"[bold red]erro[/bold red]  {msg}")


def aviso(msg: str) -> None:
    out(f"[yellow]aviso[/yellow] {msg}")


def ok(msg: str) -> None:
    out(f"[green]ok[/green]    {msg}")


# ---- texto ---------------------------------------------------------------
def normalizar(texto: str) -> str:
    """minúsculas, sem acento — pra casar palavras-chave com robustez."""
    texto = unicodedata.normalize("NFKD", texto or "")
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto.lower()


def contem_palavra(texto_norm: str, termo: str) -> bool:
    """Casa 'termo' como palavra/expressão dentro de texto já normalizado."""
    termo = normalizar(termo).strip()
    if not termo:
        return False
    # \b não lida bem com '+' em 'c++'/'node.js'; usa fronteira flexível.
    padrao = r"(?<![a-z0-9])" + re.escape(termo) + r"(?![a-z0-9])"
    return re.search(padrao, texto_norm) is not None


def ler_cv(caminho: str) -> str:
    """Lê o CV de .txt/.md (ou .pdf se pypdf estiver instalado)."""
    if not caminho:
        return ""
    p = Path(caminho)
    if not p.exists():
        raise FileNotFoundError(f"CV não encontrado em '{caminho}'.")
    if p.suffix.lower() == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError as e:
            raise RuntimeError(
                "Para ler CV em PDF instale 'pypdf' (pip install pypdf) "
                "ou exporte o CV para .txt/.md."
            ) from e
        reader = PdfReader(str(p))
        return "\n".join((pag.extract_text() or "") for pag in reader.pages)
    return p.read_text(encoding="utf-8", errors="ignore")


def trecho(texto: str, limite: int = 240) -> str:
    """Primeiro trecho legível de uma descrição (pra usar no e-mail)."""
    limpo = re.sub(r"\s+", " ", (texto or "")).strip()
    if len(limpo) <= limite:
        return limpo
    return limpo[:limite].rsplit(" ", 1)[0] + "…"
