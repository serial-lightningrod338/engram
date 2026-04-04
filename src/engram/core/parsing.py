"""Shared LLM response parsing and validation."""

from __future__ import annotations

import json
import logging
import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


# ── Response schemas ─────────────────────────────────────────────────────

SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9\-]{0,79}$")


class ArticleResult(BaseModel):
    """Validated schema for save/ingest LLM responses."""

    action: Literal["create", "update"]
    slug: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=200_000)
    tags: list[str] = Field(default_factory=list)
    summary: str = Field(default="", max_length=500)

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        if not SLUG_PATTERN.fullmatch(v):
            raise ValueError(
                f"Invalid slug: {v!r}. Must be lowercase alphanumeric with hyphens."
            )
        # Block path traversal
        if ".." in v or "/" in v or "\\" in v:
            raise ValueError(f"Slug contains path traversal characters: {v!r}")
        return v

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list) -> list[str]:
        return [str(t).strip()[:50] for t in v if isinstance(t, str) and t.strip()][:20]


class LintIssueResult(BaseModel):
    """Validated schema for lint LLM responses."""

    type: Literal[
        "contradiction", "stale", "missing_xref", "stub", "orphan", "duplicate"
    ] = "stub"
    severity: Literal["high", "medium", "low"] = "low"
    articles: list[str] = Field(default_factory=list)
    description: str = Field(default="", max_length=500)
    suggestion: str = Field(default="", max_length=500)


# ── JSON extraction ──────────────────────────────────────────────────────

def extract_json(text: str) -> str:
    """Extract JSON from LLM response, handling code blocks and surrounding text."""
    text = text.strip()

    # Remove markdown code fences
    if text.startswith("```"):
        lines = text.splitlines()
        lines = [line for line in lines if not line.strip().startswith("```")]
        text = "\n".join(lines).strip()

    # If still not valid JSON, try to find JSON in the text
    if not text.startswith(("{", "[")):
        # Find first { or [
        obj_start = text.find("{")
        arr_start = text.find("[")
        if obj_start == -1 and arr_start == -1:
            return text  # Let json.loads fail with a clear error
        start = min(
            s for s in (obj_start, arr_start) if s != -1
        )
        text = text[start:]

        # Find matching closing bracket, respecting strings
        depth = 0
        opener = text[0]
        closer = "}" if opener == "{" else "]"
        in_string = False
        escape = False
        for i, ch in enumerate(text):
            if escape:
                escape = False
                continue
            if ch == "\\":
                escape = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == opener:
                depth += 1
            elif ch == closer:
                depth -= 1
                if depth == 0:
                    text = text[: i + 1]
                    break

    return text


def parse_article_response(text: str) -> ArticleResult:
    """Parse and validate a single article response from the LLM."""
    extracted = extract_json(text)
    try:
        data = json.loads(extracted)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"LLM returned invalid JSON. Raw response:\n{text[:500]}"
        ) from exc
    return ArticleResult.model_validate(data)


def parse_article_list_response(text: str) -> list[ArticleResult]:
    """Parse and validate a list of article responses from the LLM."""
    extracted = extract_json(text)
    try:
        data = json.loads(extracted)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"LLM returned invalid JSON. Raw response:\n{text[:500]}"
        ) from exc

    if isinstance(data, dict):
        data = [data]

    return [ArticleResult.model_validate(item) for item in data]


def parse_lint_response(text: str) -> list[LintIssueResult]:
    """Parse and validate lint issue responses from the LLM."""
    extracted = extract_json(text)
    try:
        data = json.loads(extracted)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"LLM returned invalid JSON. Raw response:\n{text[:500]}"
        ) from exc

    if isinstance(data, dict):
        data = [data]

    return [LintIssueResult.model_validate(item) for item in data]
