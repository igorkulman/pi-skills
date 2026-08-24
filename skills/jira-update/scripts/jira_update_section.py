#!/usr/bin/env python3
"""Replace a named section in a Jira issue description.

This script intentionally uses only the Python standard library so it can run from
Pi without extra setup. It targets Jira Cloud/API v3 ADF descriptions and supports
limited Markdown input for common agent updates: paragraphs, headings, bullet
lists, simple pipe tables, inline code, and bold text.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

KEY_RE = re.compile(r"\b[A-Z][A-Z0-9]{1,9}-\d+\b", re.IGNORECASE)


@dataclass(frozen=True)
class Args:
    issue: str
    heading: str
    markdown_file: str
    base_url: str | None
    api_version: str
    append_if_missing: bool
    dry_run: bool


def first_env(names: list[str]) -> str | None:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return None


def extract_issue_key(value: str) -> str | None:
    decoded = urllib.parse.unquote(value)
    match = KEY_RE.search(decoded)
    return match.group(0).upper() if match else None


def infer_base_url(value: str, explicit_base_url: str | None) -> str:
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme and parsed.netloc:
        path = urllib.parse.unquote(parsed.path or "")
        base_path = ""
        if "/browse/" in path:
            base_path = path.split("/browse/", 1)[0]
        elif "/rest/api/" in path:
            base_path = path.split("/rest/api/", 1)[0]
        return f"{parsed.scheme}://{parsed.netloc}{base_path}".rstrip("/")
    if explicit_base_url:
        return explicit_base_url.rstrip("/")
    env_base = os.environ.get("JIRA_BASE_URL")
    if env_base:
        return env_base.rstrip("/")
    raise SystemExit("Could not infer Jira base URL. Pass a full Jira URL or set JIRA_BASE_URL.")


def build_auth_headers() -> dict[str, str]:
    headers = {"Accept": "application/json"}

    user = first_env(["JIRA_EMAIL", "JIRA_USER", "JIRA_USERNAME", "ATLASSIAN_EMAIL"])
    basic_token = first_env(["JIRA_API_TOKEN", "ATLASSIAN_API_TOKEN", "JIRA_PASSWORD", "JIRA_TOKEN"])
    bearer_token = first_env(["JIRA_BEARER_TOKEN", "JIRA_PAT", "ATLASSIAN_BEARER_TOKEN"])

    if user and basic_token:
        raw = f"{user}:{basic_token}".encode("utf-8")
        headers["Authorization"] = "Basic " + base64.b64encode(raw).decode("ascii")
    elif bearer_token:
        headers["Authorization"] = "Bearer " + bearer_token
    elif basic_token and not user:
        headers["Authorization"] = "Bearer " + basic_token

    return headers


def request_json(url: str, headers: dict[str, str], method: str = "GET", payload: Any = None) -> tuple[int, Any]:
    data = None
    req_headers = dict(headers)
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        req_headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, headers=req_headers, data=data, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
            return response.status, json.loads(body) if body else None
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")[:4000]
        raise RuntimeError(f"{method} {url} failed: HTTP {exc.code} {exc.reason}\n{body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"{method} {url} failed: {exc.reason}") from exc


def text_node(text: str, marks: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    node: dict[str, Any] = {"type": "text", "text": text}
    if marks:
        node["marks"] = marks
    return node


def inline_nodes(text: str) -> list[dict[str, Any]]:
    """Parse a tiny inline Markdown subset: `code` and **strong**."""
    nodes: list[dict[str, Any]] = []
    pattern = re.compile(r"(`[^`]+`|\*\*[^*]+\*\*)")
    position = 0
    for match in pattern.finditer(text):
        if match.start() > position:
            nodes.append(text_node(text[position : match.start()]))
        token = match.group(0)
        if token.startswith("`"):
            nodes.append(text_node(token[1:-1], [{"type": "code"}]))
        elif token.startswith("**"):
            nodes.append(text_node(token[2:-2], [{"type": "strong"}]))
        position = match.end()
    if position < len(text):
        nodes.append(text_node(text[position:]))
    return nodes or [text_node("")]


def paragraph(text: str) -> dict[str, Any]:
    return {"type": "paragraph", "content": inline_nodes(text)}


def heading(text: str, level: int) -> dict[str, Any]:
    return {"type": "heading", "attrs": {"level": level}, "content": inline_nodes(text)}


def bullet_list(items: list[str]) -> dict[str, Any]:
    return {
        "type": "bulletList",
        "content": [
            {"type": "listItem", "content": [paragraph(item)]}
            for item in items
        ],
    }


def split_table_row(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.strip() for cell in stripped.split("|")]


def is_table_separator(line: str) -> bool:
    cells = split_table_row(line)
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in cells)


def table_cell(text: str, header: bool) -> dict[str, Any]:
    return {
        "type": "tableHeader" if header else "tableCell",
        "attrs": {},
        "content": [paragraph(text)],
    }


def table(rows: list[list[str]]) -> dict[str, Any]:
    return {
        "type": "table",
        "attrs": {"isNumberColumnEnabled": False, "layout": "default"},
        "content": [
            {
                "type": "tableRow",
                "content": [table_cell(cell, header=index == 0) for cell in row],
            }
            for index, row in enumerate(rows)
        ],
    }


def parse_markdown(markdown: str) -> list[dict[str, Any]]:
    lines = markdown.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    nodes: list[dict[str, Any]] = []
    i = 0
    paragraph_lines: list[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph_lines
        if paragraph_lines:
            nodes.append(paragraph(" ".join(line.strip() for line in paragraph_lines).strip()))
            paragraph_lines = []

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            flush_paragraph()
            i += 1
            continue

        heading_match = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if heading_match:
            flush_paragraph()
            nodes.append(heading(heading_match.group(2).strip(), len(heading_match.group(1))))
            i += 1
            continue

        if stripped.startswith("- "):
            flush_paragraph()
            items: list[str] = []
            while i < len(lines) and lines[i].strip().startswith("- "):
                items.append(lines[i].strip()[2:].strip())
                i += 1
            nodes.append(bullet_list(items))
            continue

        if "|" in stripped and i + 1 < len(lines) and is_table_separator(lines[i + 1]):
            flush_paragraph()
            rows = [split_table_row(stripped)]
            i += 2
            while i < len(lines) and "|" in lines[i].strip() and lines[i].strip():
                rows.append(split_table_row(lines[i]))
                i += 1
            nodes.append(table(rows))
            continue

        paragraph_lines.append(stripped)
        i += 1

    flush_paragraph()
    return nodes


def node_plain_text(node: dict[str, Any]) -> str:
    result = ""
    for child in node.get("content") or []:
        if child.get("type") == "text":
            result += child.get("text", "")
        else:
            result += node_plain_text(child)
    return result


def heading_level(node: dict[str, Any]) -> int | None:
    if node.get("type") != "heading":
        return None
    return int((node.get("attrs") or {}).get("level") or 1)


def replace_section(content: list[dict[str, Any]], section_heading: str, new_nodes: list[dict[str, Any]], append_if_missing: bool) -> list[dict[str, Any]]:
    start = None
    start_level = 1
    for index, node in enumerate(content):
        if node.get("type") == "heading" and node_plain_text(node).strip() == section_heading:
            start = index
            start_level = heading_level(node) or 1
            break

    if start is None:
        if not append_if_missing:
            raise SystemExit(f"Heading not found: {section_heading}")
        appended = list(content)
        if appended and appended[-1].get("type") != "rule":
            appended.append({"type": "rule"})
        appended.append(heading(section_heading, 1))
        appended.extend(new_nodes)
        return appended

    end = len(content)
    for index in range(start + 1, len(content)):
        level = heading_level(content[index])
        if level is not None and level <= start_level:
            end = index
            break

    return content[: start + 1] + new_nodes + content[end:]


def parse_args() -> Args:
    parser = argparse.ArgumentParser(description="Replace a named Jira description section with limited Markdown content.")
    parser.add_argument("issue", help="Jira issue key or URL")
    parser.add_argument("--heading", required=True, help="Exact Jira description heading to replace content under")
    parser.add_argument("--markdown-file", required=True, help="File containing replacement section body in limited Markdown")
    parser.add_argument("--base-url", default=None, help="Jira base URL, e.g. https://example.atlassian.net")
    parser.add_argument("--api-version", default="3", help="Jira REST API version, default: 3")
    parser.add_argument("--no-append-if-missing", action="store_true", help="Fail if the heading is missing instead of appending it")
    parser.add_argument("--dry-run", action="store_true", help="Do not update Jira; print the JSON payload preview")
    ns = parser.parse_args()
    return Args(
        issue=ns.issue,
        heading=ns.heading,
        markdown_file=ns.markdown_file,
        base_url=ns.base_url,
        api_version=ns.api_version,
        append_if_missing=not ns.no_append_if_missing,
        dry_run=ns.dry_run,
    )


def main() -> int:
    args = parse_args()
    issue_key = extract_issue_key(args.issue)
    if not issue_key:
        raise SystemExit(f"Could not extract Jira issue key from: {args.issue}")
    base_url = infer_base_url(args.issue, args.base_url)
    headers = build_auth_headers()

    with open(args.markdown_file, "r", encoding="utf-8") as file:
        markdown = file.read()

    get_url = f"{base_url}/rest/api/{args.api_version}/issue/{urllib.parse.quote(issue_key, safe='')}?fields=description"
    _, issue = request_json(get_url, headers)
    description = (issue.get("fields") or {}).get("description") or {"type": "doc", "version": 1, "content": []}
    if description.get("type") != "doc":
        raise SystemExit("Issue description is not Atlassian Document Format; cannot safely update it.")

    new_nodes = parse_markdown(markdown)
    description["content"] = replace_section(
        list(description.get("content") or []),
        args.heading,
        new_nodes,
        args.append_if_missing,
    )
    payload = {"fields": {"description": description}}

    if args.dry_run:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    put_url = f"{base_url}/rest/api/{args.api_version}/issue/{urllib.parse.quote(issue_key, safe='')}"
    status, _ = request_json(put_url, headers, method="PUT", payload=payload)
    print(f"Updated {issue_key}: HTTP {status} ({base_url}/browse/{issue_key})")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
