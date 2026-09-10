"""Interface de linha de comando do Auto-Candidatura."""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .config import carregar, ConfigError, CAMINHO_PADRAO
from .coleta import buscar as coletar_vagas
from .qualifica import qualificar
from .escreve import gerar_rascunho
from .tracker import Tracker, CAMINHO_DB_PADRAO
from .util import out, ok, erro, aviso, ler_cv


def _tabela(vagas, titulo="Vagas"):
    try:
        from rich.table import Table
        from rich.console import Console
        t = Table(title=titulo)
        t.add_column("id", style="dim")
        t.add_column("score", justify="right")
        t.add_column("status")
        t.add_column("título")
        t.add_column("empresa")
        for v in vagas:
            cor = "green" if v.score >= 70 else ("yellow" if v.score >= 50 else "red")
            t.add_row(v.id, f"[{cor}]{v.score}[/{cor}]", v.status,
                      (v.titulo or "")[:45], (v.empresa or "")[:28])
        Console().print(t)
    except ImportError:
        out(f"\n{titulo}")
        for v in vagas:
            out(f"  {v.id}  {v.score:>3}  {v.status:<11}  {v.titulo[:40]:<40}  {v.empresa[:25]}")


# ---- comandos ------------------------------------------------------------
def cmd_buscar(cfg, tk: Tracker, args) -> int:
    out(f"[bold]Buscando vagas no Apify[/bold] — actor '{cfg.apify.get('actor_id', '?')}'…")
    vagas = coletar_vagas(cfg)
    novas = sum(1 for v in vagas if tk.upsert(v))
    ok(f"{len(vagas)} vagas coletadas · {novas} novas salvas · "
       f"{len(vagas) - novas} já existiam.")
    return 0


def cmd_qualificar(cfg, tk: Tracker, args) -> int:
    cv_texto = _cv(cfg)
    alvo = tk.listar(status="novo")
    if not alvo:
        aviso("Nenhuma vaga com status 'novo'. Rode 'buscar' antes.")
        return 0
    for v in alvo:
        qualificar(v, cfg)
        tk.salvar(v)
    qualificadas = [v for v in alvo if v.status == "qualificado"]
    ok(f"{len(alvo)} vagas avaliadas · {len(qualificadas)} qualificadas.")
    _tabela(sorted(qualificadas, key=lambda v: -v.score)[:15], "Top qualificadas")
    return 0


def cmd_escrever(cfg, tk: Tracker, args) -> int:
    cv_texto = _cv(cfg)
    pasta = cfg.get("saida", "pasta_rascunhos", padrao="saidas/rascunhos")
    limite = args.limite or int(cfg.get("saida", "max_rascunhos", padrao=15))
    alvo = tk.listar(status="qualificado", limite=limite, ordem="score")
    if not alvo:
        aviso("Nenhuma vaga 'qualificada'. Rode 'qualificar' antes.")
        return 0
    if cfg.tem_claude:
        out("[dim]ANTHROPIC_API_KEY detectada — escrevendo e-mails via Claude API.[/dim]")
    else:
        out("[dim]Sem chave da Claude API — gerando prompts prontos pro Claude grátis.[/dim]")
    caminhos = []
    for v in alvo:
        caminho = gerar_rascunho(v, cfg, cv_texto, pasta)
        if v.status == "qualificado":
            tk.atualizar_campos(v.id, status="rascunho")
        caminhos.append(caminho)
    ok(f"{len(caminhos)} rascunhos gerados em '{pasta}/'.")
    for c in caminhos:
        out(f"  • {c}")
    out("\n[bold]Próximo passo:[/bold] abra cada arquivo, revise o e-mail e envie. "
        "Depois marque como enviado:  [dim]python -m jobhunter marcar <id> --status enviado[/dim]")
    return 0


def cmd_listar(cfg, tk: Tracker, args) -> int:
    vagas = tk.listar(status=args.status, limite=args.limite, ordem="score")
    _tabela(vagas, f"Vagas{f' ({args.status})' if args.status else ''}")
    return 0


def cmd_marcar(cfg, tk: Tracker, args) -> int:
    from .modelos import STATUS
    if args.status not in STATUS:
        erro(f"Status inválido. Use um de: {', '.join(STATUS)}")
        return 1
    v = tk.obter(args.id)
    if not v:
        erro(f"Vaga '{args.id}' não encontrada.")
        return 1
    campos = {"status": args.status}
    if args.nota:
        campos["notas"] = ((v.notas + " | ") if v.notas else "") + args.nota
    if args.email:
        campos["contato_email"] = args.email
    if args.contato:
        campos["contato_nome"] = args.contato
    tk.atualizar_campos(v.id, **campos)
    ok(f"'{v.titulo} — {v.empresa}' → {args.status}.")
    return 0


def cmd_status(cfg, tk: Tracker, args) -> int:
    cont = tk.contagem_por_status()
    total = sum(cont.values())
    out(f"\n[bold]Funil de candidaturas[/bold] · {total} vagas no total\n")
    from .modelos import STATUS
    rotulos = {
        "novo": "🆕 novas", "qualificado": "⭐ qualificadas", "rascunho": "✍️  com rascunho",
        "enviado": "📤 enviadas", "resposta": "🎉 com resposta", "descartado": "🗑️  descartadas",
    }
    for st in STATUS:
        out(f"  {rotulos.get(st, st):<18} {cont.get(st, 0)}")
    if cont.get("enviado") or cont.get("resposta"):
        base = cont.get("enviado", 0) + cont.get("resposta", 0)
        taxa = 100 * cont.get("resposta", 0) / base if base else 0
        out(f"\n  taxa de resposta: {taxa:.0f}%")
    return 0


def cmd_fluxo(cfg, tk: Tracker, args) -> int:
    out("[bold]═══ Fluxo completo: buscar → qualificar → escrever ═══[/bold]\n")
    r = cmd_buscar(cfg, tk, args)
    if r:
        return r
    out("")
    cmd_qualificar(cfg, tk, args)
    out("")
    cmd_escrever(cfg, tk, args)
    out("")
    return cmd_status(cfg, tk, args)


# ---- helpers -------------------------------------------------------------
def _cv(cfg) -> str:
    caminho = cfg.caminho_cv
    if not caminho:
        aviso("Nenhum CV configurado (perfil.cv_arquivo). O texto do CV melhora "
              "muito a qualificação e os e-mails.")
        return ""
    try:
        return ler_cv(caminho)
    except (FileNotFoundError, RuntimeError) as e:
        aviso(str(e))
        return ""


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="jobhunter",
        description="Auto-Candidatura — Apify coleta, o app qualifica e escreve, você envia.",
    )
    p.add_argument("--perfil", default=CAMINHO_PADRAO, help=f"arquivo de perfil (padrão: {CAMINHO_PADRAO})")
    p.add_argument("--db", default=CAMINHO_DB_PADRAO, help=f"banco SQLite (padrão: {CAMINHO_DB_PADRAO})")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("buscar", help="coleta vagas no Apify e salva").set_defaults(func=cmd_buscar)
    sub.add_parser("qualificar", help="pontua as vagas 'novas' contra o seu perfil").set_defaults(func=cmd_qualificar)

    pe = sub.add_parser("escrever", help="gera rascunhos de e-mail das vagas qualificadas")
    pe.add_argument("--limite", type=int, default=0, help="quantos rascunhos gerar")
    pe.set_defaults(func=cmd_escrever)

    pl = sub.add_parser("listar", help="lista as vagas salvas")
    pl.add_argument("--status", help="filtra por status")
    pl.add_argument("--limite", type=int, default=30)
    pl.set_defaults(func=cmd_listar)

    pm = sub.add_parser("marcar", help="atualiza o status/contato de uma vaga")
    pm.add_argument("id", help="id da vaga (prefixo basta)")
    pm.add_argument("--status", required=True, help="novo status")
    pm.add_argument("--nota", help="acrescenta uma nota")
    pm.add_argument("--email", help="define o e-mail do contato")
    pm.add_argument("--contato", help="define o nome do contato")
    pm.set_defaults(func=cmd_marcar)

    sub.add_parser("status", help="mostra o funil de candidaturas").set_defaults(func=cmd_status)

    pf = sub.add_parser("fluxo", help="roda buscar + qualificar + escrever de uma vez")
    pf.add_argument("--limite", type=int, default=0)
    pf.set_defaults(func=cmd_fluxo)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        cfg = carregar(args.perfil)
    except ConfigError as e:
        erro(str(e))
        return 2
    tk = Tracker(args.db)
    try:
        return args.func(cfg, tk, args)
    except RuntimeError as e:
        erro(str(e))
        return 1
    except KeyboardInterrupt:
        aviso("interrompido.")
        return 130
    finally:
        tk.close()


if __name__ == "__main__":
    sys.exit(main())
