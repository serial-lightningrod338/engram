"""Engram CLI — Persistent memory for AI agents."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from engram import __version__
from engram.config import VALID_PROVIDERS, Config
from engram.llm.base import LLMClient
from engram.wiki.store import WikiStore

app = typer.Typer(
    name="engram",
    help="Persistent memory for AI agents. They learn once, remember forever.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
console = Console()
logger = logging.getLogger(__name__)

# ── Global option for JSON output ────────────────────────────────────────

_json_mode = False


@app.callback()
def main(
    output_json: bool = typer.Option(
        False, "--json", help="Output in JSON format (for agent consumption)"
    ),
) -> None:
    """Persistent memory for AI agents."""
    global _json_mode
    _json_mode = output_json


def _out(data: dict) -> None:
    """Output data as JSON (if --json) or do nothing (Rich handles it)."""
    if _json_mode:
        console.print_json(json.dumps(data))


def _load_config() -> Config:
    """Load config, checking for local .engram/ first, then global."""
    local = Path.cwd() / ".engram"
    if (local / "engram.toml").exists():
        return Config.load(home=local)
    return Config.load()


def _get_llm(config: Config) -> LLMClient:
    """Get LLM client from config."""
    from engram.llm import create_client

    return create_client(config.llm)


def _get_wiki(config: Config) -> WikiStore:
    """Get wiki store from config."""
    return WikiStore(config.wiki_dir, config.log_path)


def _handle_error(exc: Exception) -> None:
    """Display a clean error message and exit."""
    if _json_mode:
        console.print_json(json.dumps({"error": str(exc)}))
    else:
        console.print(f"  [red]✗[/] {exc}")
    raise typer.Exit(1)


# ── init ─────────────────────────────────────────────────────────────────

@app.command()
def init(
    provider: str = typer.Option("claude", help="LLM provider: claude, openai, ollama"),
    model: str = typer.Option("", help="Model name (default depends on provider)"),
    local: bool = typer.Option(False, "--local", help="Create .engram/ in current directory"),
) -> None:
    """Initialize a new Engram knowledge base."""
    if provider not in VALID_PROVIDERS:
        _handle_error(ValueError(
            f"Unknown provider: {provider!r}. Must be one of: {', '.join(VALID_PROVIDERS)}"
        ))

    default_models = {
        "claude": "claude-sonnet-4-6",
        "openai": "gpt-4o",
        "ollama": "llama3.1",
    }
    if not model:
        model = default_models.get(provider, "claude-sonnet-4-6")

    home = Path.cwd() / ".engram" if local else None
    config = Config() if home is None else Config(home=home)
    config.llm.provider = provider  # type: ignore[assignment]
    config.llm.model = model
    config.ensure_dirs()
    config.save()

    log_path = config.log_path
    if not log_path.exists():
        log_path.write_text("# Engram Log\n\n")

    index_path = config.index_path
    if not index_path.exists():
        index_path.write_text("# Engram Wiki Index\n\n*No articles yet.*\n")

    if _json_mode:
        _out({
            "status": "initialized",
            "provider": provider,
            "model": model,
            "location": str(config.home),
            "scope": "local" if local else "global",
        })
    else:
        scope = "project-local" if local else "global"
        api_hint = ""
        if provider == "claude":
            api_hint = "\n\n  Set ANTHROPIC_API_KEY env var to start."
        elif provider == "openai":
            api_hint = "\n\n  Set OPENAI_API_KEY env var to start."
        elif provider == "ollama":
            api_hint = "\n\n  Make sure Ollama is running (ollama serve)."

        console.print(Panel(
            f"[bold green]Engram initialized![/] ({scope})\n\n"
            f"  Provider: [cyan]{provider}[/]\n"
            f"  Model: [cyan]{model}[/]\n"
            f"  Location: [dim]{config.home}[/]"
            f"{api_hint}",
            title="engram",
            border_style="green",
        ))


# ── save ─────────────────────────────────────────────────────────────────

@app.command()
def save(
    memory: str | None = typer.Argument(
        None, help="The information to save (or pipe via stdin)"
    ),
) -> None:
    """Save a piece of knowledge to the wiki."""
    # Support stdin
    if memory is None:
        if not sys.stdin.isatty():
            memory = sys.stdin.read().strip()
        if not memory:
            _handle_error(ValueError("No input provided. Pass text as argument or pipe via stdin."))
            return

    config = _load_config()
    config.ensure_dirs()

    try:
        llm = _get_llm(config)
        wiki = _get_wiki(config)

        from engram.core.compress import compress_wiki, needs_compression
        from engram.core.save import save_memory

        if not _json_mode:
            with console.status("[bold cyan]Thinking...", spinner="dots"):
                article, summary = save_memory(memory, wiki, llm)
        else:
            article, summary = save_memory(memory, wiki, llm)

        compressed = False
        if needs_compression(wiki, config.compress):
            if not _json_mode:
                console.print("\n  [yellow]⟳[/] Auto-compressing memory...")
                with console.status("[bold yellow]Compressing...", spinner="dots"):
                    before, after = compress_wiki(wiki, llm, config.compress)
            else:
                before, after = compress_wiki(wiki, llm, config.compress)
            compressed = True

        if _json_mode:
            result = {
                "status": "saved",
                "article": {"slug": article.slug, "title": article.title},
                "summary": summary,
            }
            if compressed:
                result["compressed"] = {"before": before, "after": after}
            _out(result)
        else:
            console.print(f"  [green]✓[/] [bold]{article.title}[/] ({article.slug}.md)")
            console.print(f"    {summary}")
            if compressed:
                console.print(f"  [green]✓[/] Compressed {before} → {after} articles")

    except (ValueError, ConnectionError, OSError) as exc:
        _handle_error(exc)


# ── ingest ───────────────────────────────────────────────────────────────

@app.command()
def ingest(
    source: str | None = typer.Argument(
        None, help="URL, file path, or text (or pipe via stdin)"
    ),
) -> None:
    """Ingest an external source (URL, file, text) into the wiki."""
    # Support stdin
    if source is None:
        if not sys.stdin.isatty():
            source = sys.stdin.read().strip()
        if not source:
            _handle_error(ValueError("No source provided. Pass URL/path or pipe via stdin."))
            return

    config = _load_config()
    config.ensure_dirs()

    try:
        llm = _get_llm(config)
        wiki = _get_wiki(config)

        from engram.core.ingest import ingest_source
        from engram.sources.text import parse_file, parse_text
        from engram.sources.url import fetch_url

        if not _json_mode:
            with console.status("[bold cyan]Fetching source...", spinner="dots"):
                if source.startswith(("http://", "https://")):
                    parsed = fetch_url(source)
                elif Path(source).exists():
                    parsed = parse_file(Path(source))
                else:
                    parsed = parse_text(source)
        else:
            if source.startswith(("http://", "https://")):
                parsed = fetch_url(source)
            elif Path(source).exists():
                parsed = parse_file(Path(source))
            else:
                parsed = parse_text(source)

        if not _json_mode:
            console.print(f"  [dim]Source: {parsed.origin} ({parsed.source_type})[/]")
            if parsed.title:
                console.print(f"  [dim]Title: {parsed.title}[/]")

        if not _json_mode:
            with console.status("[bold cyan]Synthesizing...", spinner="dots"):
                results = ingest_source(parsed, wiki, llm, config.sources_dir)
        else:
            results = ingest_source(parsed, wiki, llm, config.sources_dir)

        if _json_mode:
            _out({
                "status": "ingested",
                "source": parsed.origin,
                "articles": [
                    {"slug": a.slug, "title": a.title, "summary": s}
                    for a, s in results
                ],
            })
        else:
            for article, summary in results:
                console.print(f"  [green]✓[/] [bold]{article.title}[/] ({article.slug}.md)")
                console.print(f"    {summary}")

    except (ValueError, ConnectionError, OSError) as exc:
        _handle_error(exc)


# ── query ────────────────────────────────────────────────────────────────

@app.command()
def query(
    question: str = typer.Argument(..., help="Question to ask the knowledge base"),
) -> None:
    """Ask a question to your knowledge base."""
    config = _load_config()

    try:
        llm = _get_llm(config)
        wiki = _get_wiki(config)

        from engram.core.query import query_wiki

        if not _json_mode:
            with console.status("[bold cyan]Searching wiki...", spinner="dots"):
                answer = query_wiki(question, wiki, llm)
            console.print()
            console.print(Panel(answer, title="Answer", border_style="cyan"))
        else:
            answer = query_wiki(question, wiki, llm)
            _out({"question": question, "answer": answer})

    except (ValueError, ConnectionError, OSError) as exc:
        _handle_error(exc)


# ── lint ─────────────────────────────────────────────────────────────────

@app.command()
def lint() -> None:
    """Run a health check on the wiki."""
    config = _load_config()

    try:
        llm = _get_llm(config)
        wiki = _get_wiki(config)

        from engram.core.lint import lint_wiki

        if not _json_mode:
            with console.status("[bold cyan]Analyzing wiki...", spinner="dots"):
                issues = lint_wiki(wiki, llm)
        else:
            issues = lint_wiki(wiki, llm)

        if _json_mode:
            _out({
                "issues": [
                    {
                        "type": i.type,
                        "severity": i.severity,
                        "articles": i.articles,
                        "description": i.description,
                        "suggestion": i.suggestion,
                    }
                    for i in issues
                ],
                "count": len(issues),
            })
        else:
            if not issues:
                console.print("  [green]✓[/] No issues found. Wiki is healthy!")
                return

            table = Table(title=f"Wiki Health Report — {len(issues)} issues")
            table.add_column("Type", style="bold")
            table.add_column("Severity")
            table.add_column("Articles")
            table.add_column("Issue")
            table.add_column("Suggestion", style="dim")

            severity_colors = {"high": "red", "medium": "yellow", "low": "dim"}

            for issue in issues:
                color = severity_colors.get(issue.severity, "white")
                table.add_row(
                    issue.type,
                    f"[{color}]{issue.severity}[/]",
                    ", ".join(issue.articles),
                    issue.description,
                    issue.suggestion,
                )

            console.print(table)

    except (ValueError, ConnectionError, OSError) as exc:
        _handle_error(exc)


# ── compress ─────────────────────────────────────────────────────────────

@app.command()
def compress() -> None:
    """Manually compress and consolidate wiki articles."""
    config = _load_config()

    try:
        llm = _get_llm(config)
        wiki = _get_wiki(config)

        from engram.core.compress import compress_wiki

        articles_before = len(wiki.list_articles())
        if articles_before == 0:
            if _json_mode:
                _out({"status": "empty", "message": "Nothing to compress."})
            else:
                console.print("  [dim]Wiki is empty, nothing to compress.[/]")
            return

        if not _json_mode:
            console.print(f"  [dim]Current articles: {articles_before}[/]")
            with console.status("[bold yellow]Compressing...", spinner="dots"):
                before, after = compress_wiki(wiki, llm, config.compress)
            console.print(f"  [green]✓[/] Compressed {before} → {after} articles")
            console.print("  [dim]Backup saved in ~/.engram/backups/[/]")
        else:
            before, after = compress_wiki(wiki, llm, config.compress)
            _out({"status": "compressed", "before": before, "after": after})

    except (ValueError, ConnectionError, OSError) as exc:
        _handle_error(exc)


# ── status ───────────────────────────────────────────────────────────────

@app.command()
def status() -> None:
    """Show the current state of the knowledge base."""
    config = _load_config()

    if not config.home.exists():
        if _json_mode:
            _out({"error": "Not initialized. Run: engram init"})
        else:
            console.print("[yellow]Engram not initialized. Run:[/] engram init")
        raise typer.Exit(1)

    wiki = _get_wiki(config)
    articles = wiki.list_articles()

    total_size = sum(len(a.content.encode("utf-8")) for a in articles)
    all_tags: set[str] = set()
    all_sources: set[str] = set()
    for a in articles:
        all_tags.update(a.tags)
        all_sources.update(a.sources)

    if _json_mode:
        _out({
            "articles": len(articles),
            "total_size_kb": round(total_size / 1024, 1),
            "tags": sorted(all_tags),
            "sources_count": len(all_sources),
            "provider": config.llm.provider,
            "model": config.llm.model,
            "location": str(config.home),
            "recent": [
                {"slug": a.slug, "title": a.title, "updated": a.updated_at.isoformat()}
                for a in sorted(articles, key=lambda a: a.updated_at, reverse=True)[:5]
            ],
        })
    else:
        table = Table(title="Engram Status", border_style="cyan")
        table.add_column("Metric", style="bold")
        table.add_column("Value", justify="right")

        table.add_row("Articles", str(len(articles)))
        table.add_row("Total size", f"{total_size / 1024:.1f} KB")
        table.add_row("Tags", str(len(all_tags)))
        table.add_row("Sources", str(len(all_sources)))
        table.add_row("Provider", config.llm.provider)
        table.add_row("Model", config.llm.model)
        table.add_row("Location", str(config.home))

        console.print(table)

        if articles:
            console.print("\n[bold]Recent articles:[/]")
            recent = sorted(articles, key=lambda a: a.updated_at, reverse=True)[:5]
            for a in recent:
                age = a.updated_at.strftime("%Y-%m-%d %H:%M")
                console.print(f"  • {a.title} [dim]({age})[/]")


# ── export ───────────────────────────────────────────────────────────────

@app.command()
def export(
    fmt: str = typer.Option("markdown", "--format", "-f", help="Output format: markdown, json"),
    output: str | None = typer.Option(
        None, "--output", "-o", help="Output file (default: stdout)"
    ),
) -> None:
    """Export the entire wiki as a single document."""
    config = _load_config()
    wiki = _get_wiki(config)
    articles = wiki.list_articles()

    if not articles:
        if _json_mode or fmt == "json":
            result = json.dumps({"articles": [], "count": 0}, indent=2)
        else:
            result = "# Engram Wiki\n\n*No articles yet.*\n"
    elif fmt == "json":
        result = json.dumps({
            "articles": [
                {
                    "slug": a.slug,
                    "title": a.title,
                    "content": a.content,
                    "tags": a.tags,
                    "sources": a.sources,
                    "created": a.created_at.isoformat(),
                    "updated": a.updated_at.isoformat(),
                }
                for a in articles
            ],
            "count": len(articles),
        }, indent=2)
    else:
        parts = [
            "# Engram Wiki Export",
            "",
            f"*{len(articles)} articles*",
            "",
            "---",
            "",
        ]
        for a in articles:
            parts.append(f"## {a.title}")
            parts.append("")
            if a.tags:
                parts.append(f"*Tags: {', '.join(a.tags)}*")
                parts.append("")
            parts.append(a.content)
            parts.append("")
            parts.append("---")
            parts.append("")
        result = "\n".join(parts)

    if output:
        Path(output).write_text(result)
        if not _json_mode:
            console.print(f"  [green]✓[/] Exported {len(articles)} articles to {output}")
    else:
        console.print(result)


# ── forget ───────────────────────────────────────────────────────────────

@app.command()
def forget(
    slug: str = typer.Argument(..., help="Slug of the article to delete"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Delete an article from the wiki."""
    config = _load_config()
    wiki = _get_wiki(config)

    article = wiki.get_article(slug)
    if article is None:
        _handle_error(ValueError(f"Article not found: {slug}"))
        return

    if not force and not _json_mode:
        console.print(f"  About to delete: [bold]{article.title}[/] ({slug}.md)")
        confirm = typer.confirm("  Are you sure?")
        if not confirm:
            console.print("  [dim]Cancelled.[/]")
            return

    wiki.delete_article(slug)
    wiki.append_log("forget", f"Deleted: {article.title} ({slug})")

    if _json_mode:
        _out({"status": "deleted", "slug": slug, "title": article.title})
    else:
        console.print(f"  [green]✓[/] Deleted: {article.title}")


# ── topics ───────────────────────────────────────────────────────────────

@app.command()
def topics() -> None:
    """Show all topics/tags in the wiki as a tree."""
    config = _load_config()
    wiki = _get_wiki(config)
    articles = wiki.list_articles()

    if not articles:
        if _json_mode:
            _out({"topics": {}, "count": 0})
        else:
            console.print("  [dim]Wiki is empty.[/]")
        return

    # Group by tag
    tagged: dict[str, list[str]] = {}
    untagged: list[str] = []
    for a in articles:
        if a.tags:
            for tag in a.tags:
                tagged.setdefault(tag, []).append(a.title)
        else:
            untagged.append(a.title)

    if _json_mode:
        data = {tag: titles for tag, titles in sorted(tagged.items())}
        if untagged:
            data["_uncategorized"] = untagged
        _out({"topics": data, "count": len(tagged)})
    else:
        tree = Tree("[bold cyan]Engram Wiki[/]")
        for tag in sorted(tagged.keys()):
            branch = tree.add(f"[bold]{tag}[/] ({len(tagged[tag])})")
            for title in tagged[tag]:
                branch.add(f"[dim]{title}[/]")
        if untagged:
            branch = tree.add(f"[bold yellow]uncategorized[/] ({len(untagged)})")
            for title in untagged:
                branch.add(f"[dim]{title}[/]")

        console.print(tree)


# ── version ──────────────────────────────────────────────────────────────

@app.command()
def version() -> None:
    """Show the current version."""
    if _json_mode:
        _out({"version": __version__})
    else:
        console.print(f"engram [bold]{__version__}[/]")


if __name__ == "__main__":
    app()
