"""URL source fetcher with SSRF protection."""

from __future__ import annotations

import ipaddress
import logging
import socket
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from markdownify import markdownify as md

from engram.sources.text import ParsedSource

logger = logging.getLogger(__name__)

ALLOWED_SCHEMES = {"http", "https"}
BLOCKED_NETWORKS = [
    ipaddress.ip_network("169.254.0.0/16"),   # Link-local / AWS metadata
    ipaddress.ip_network("10.0.0.0/8"),        # Private
    ipaddress.ip_network("172.16.0.0/12"),     # Private
    ipaddress.ip_network("192.168.0.0/16"),    # Private
    ipaddress.ip_network("127.0.0.0/8"),       # Loopback
    ipaddress.ip_network("0.0.0.0/8"),         # Current network
    ipaddress.ip_network("::1/128"),           # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),          # IPv6 private
    ipaddress.ip_network("fe80::/10"),         # IPv6 link-local
]


def _validate_url(url: str) -> None:
    """Validate URL scheme and ensure it doesn't resolve to a blocked IP range."""
    parsed = urlparse(url)

    if parsed.scheme not in ALLOWED_SCHEMES:
        raise ValueError(f"URL scheme not allowed: {parsed.scheme!r}. Use http or https.")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError(f"URL has no hostname: {url!r}")

    try:
        resolved_ip = ipaddress.ip_address(socket.gethostbyname(hostname))
    except (socket.gaierror, ValueError) as exc:
        raise ValueError(f"Cannot resolve hostname: {hostname!r}") from exc

    for network in BLOCKED_NETWORKS:
        if resolved_ip in network:
            raise ValueError(
                f"URL resolves to blocked IP range ({resolved_ip}). "
                f"Internal/private network access is not allowed."
            )


def fetch_url(url: str) -> ParsedSource:
    """Fetch a URL and convert its content to markdown."""
    _validate_url(url)

    response = httpx.get(
        url,
        follow_redirects=True,
        timeout=30.0,
        headers={"User-Agent": "Engram/0.1 (knowledge-base builder)"},
    )
    response.raise_for_status()

    content_type = response.headers.get("content-type", "")

    if "text/html" in content_type:
        return _parse_html(response.text, url)
    else:
        return ParsedSource(
            content=response.text,
            source_type="url",
            origin=url,
        )


def _parse_html(html: str, url: str) -> ParsedSource:
    """Parse HTML into clean markdown."""
    soup = BeautifulSoup(html, "html.parser")

    title = ""
    title_tag = soup.find("title")
    if title_tag:
        title = title_tag.get_text(strip=True)

    for tag in soup.find_all(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()

    main = soup.find("main") or soup.find("article") or soup.find("body")
    if main is None:
        main = soup

    content = md(str(main), heading_style="ATX", strip=["img"])
    lines: list[str] = []
    blank_count = 0
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            blank_count += 1
            if blank_count <= 2:
                lines.append("")
        else:
            blank_count = 0
            lines.append(line)

    content = "\n".join(lines).strip()

    return ParsedSource(
        content=content,
        source_type="url",
        origin=url,
        title=title,
    )
