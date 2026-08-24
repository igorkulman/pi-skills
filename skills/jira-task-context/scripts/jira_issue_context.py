#!/usr/bin/env python3
"""Fetch Jira issue context and one-or-more hops of linked issues.

This script intentionally uses only the Python standard library so it can run from
Pi without extra setup.
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
from collections import deque
from dataclasses import dataclass
from typing import Any

# Jira project keys are usually 2-10 chars. Keeping the prefix bounded avoids
# treating long IDs or tokens in descriptions/comments as issue keys.
KEY_RE = re.compile(r"\b[A-Z][A-Z0-9]{1,9}-\d+\b", re.IGNORECASE)
DEFAULT_FIELDS = ",".join(
    [
        "summary",
        "status",
        "issuetype",
        "priority",
        "assignee",
        "reporter",
        "description",
        "labels",
        "components",
        "fixVersions",
        "versions",
        "parent",
        "subtasks",
        "issuelinks",
        "comment",
        "created",
        "updated",
        "resolution",
        "resolutiondate",
        "duedate",
        "timetracking",
    ]
)


class JiraHTTPError(RuntimeError):
    def __init__(self, url: str, code: int, reason: str, body: str):
        super().__init__(f"GET {url} failed: HTTP {code} {reason}\n{body}")
        self.url = url
        self.code = code
        self.reason = reason
        self.body = body


@dataclass(frozen=True)
class Args:
    issue: str
    base_url: str | None
    api_version: str | None
    depth: int
    max_issues: int
    comments: int
    follow_references: bool
    output_format: str
    max_text_chars: int


def eprint(*values: object) -> None:
    print(*values, file=sys.stderr)


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
        # Jira Cloud issue URLs under /jira/software/... still use the host root
        # as the REST API base URL. Jira Server/Data Center context paths are
        # handled by the /browse/ and /rest/api/ cases above.
        return f"{parsed.scheme}://{parsed.netloc}{base_path}".rstrip("/")
    if explicit_base_url:
        return explicit_base_url.rstrip("/")
    raise SystemExit(
        "Could not infer Jira base URL. Pass a full Jira issue URL or set JIRA_BASE_URL."
    )


def build_auth_headers() -> dict[str, str]:
    headers = {"Accept": "application/json"}

    user = first_env(["JIRA_EMAIL", "JIRA_USER", "JIRA_USERNAME", "ATLASSIAN_EMAIL"])
    basic_token = first_env(
        ["JIRA_API_TOKEN", "ATLASSIAN_API_TOKEN", "JIRA_PASSWORD", "JIRA_TOKEN"]
    )
    bearer_token = first_env(["JIRA_BEARER_TOKEN", "JIRA_PAT", "ATLASSIAN_BEARER_TOKEN"])

    if user and basic_token:
        raw = f"{user}:{basic_token}".encode("utf-8")
        headers["Authorization"] = "Basic " + base64.b64encode(raw).decode("ascii")
    elif bearer_token:
        headers["Authorization"] = "Bearer " + bearer_token
    elif basic_token and not user:
        # Useful for Jira Data Center PAT setups that accept Bearer tokens.
        headers["Authorization"] = "Bearer " + basic_token

    return headers


def request_json(url: str, headers: dict[str, str]) -> Any:
    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = response.read().decode("utf-8")
            return json.loads(payload)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")[:4000]
        raise JiraHTTPError(url, exc.code, exc.reason, body) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"GET {url} failed: {exc.reason}") from exc


class JiraClient:
    def __init__(self, base_url: str, api_version: str | None):
        self.base_url = base_url.rstrip("/")
        self.api_version = api_version
        self.headers = build_auth_headers()

    def issue_url(self, key: str) -> str:
        return f"{self.base_url}/browse/{urllib.parse.quote(key)}"

    def get_issue(self, key: str) -> dict[str, Any]:
        versions = [self.api_version] if self.api_version else ["3", "2"]
        last_error: JiraHTTPError | None = None
        for version in versions:
            params = urllib.parse.urlencode({"fields": DEFAULT_FIELDS})
            url = (
                f"{self.base_url}/rest/api/{version}/issue/"
                f"{urllib.parse.quote(key, safe='')}?{params}"
            )
            try:
                data = request_json(url, self.headers)
                data["_apiVersion"] = version
                return data
            except JiraHTTPError as exc:
                last_error = exc
                if self.api_version is None and exc.code in {404, 410}:
                    continue
                raise
        assert last_error is not None
        raise last_error


def clean_text(text: str) -> str:
    text = text.replace("\xa0", " ")
    lines = [line.rstrip() for line in text.splitlines()]
    cleaned = "\n".join(lines).strip()
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned


def render_adf(node: Any) -> str:
    """Render Atlassian Document Format or Jira Server text to plain text."""
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        return "".join(render_adf(item) for item in node)
    if not isinstance(node, dict):
        return str(node)

    node_type = node.get("type")
    attrs = node.get("attrs") or {}
    content = node.get("content") or []

    if "text" in node:
        text = str(node.get("text") or "")
        for mark in node.get("marks") or []:
            if mark.get("type") == "link":
                href = (mark.get("attrs") or {}).get("href")
                if href and href not in text:
                    text = f"{text} ({href})"
        return text

    if node_type == "hardBreak":
        return "\n"
    if node_type in {"mention", "emoji"}:
        return str(attrs.get("text") or attrs.get("shortName") or attrs.get("id") or "")
    if node_type == "status":
        return str(attrs.get("text") or "")
    if node_type in {"inlineCard", "blockCard", "embedCard"}:
        return str(attrs.get("url") or attrs.get("data", {}).get("url") or "") + "\n"

    child_text = render_adf(content)

    if node_type in {"doc"}:
        return child_text
    if node_type in {"paragraph", "heading", "blockquote", "panel", "codeBlock"}:
        return child_text.rstrip() + "\n\n" if child_text.strip() else ""
    if node_type == "rule":
        return "---\n\n"
    if node_type in {"bulletList", "orderedList"}:
        return child_text.rstrip() + "\n\n" if child_text.strip() else ""
    if node_type == "listItem":
        item = child_text.strip().replace("\n", "\n  ")
        return f"- {item}\n" if item else ""
    if node_type == "table":
        return child_text.rstrip() + "\n\n" if child_text.strip() else ""
    if node_type in {"tableRow", "tableCell", "tableHeader"}:
        return child_text.strip() + " | "

    return child_text


def truncate(text: str, limit: int) -> str:
    if limit <= 0 or len(text) <= limit:
        return text
    omitted = len(text) - limit
    return text[:limit].rstrip() + f"\n… [truncated {omitted} characters]"


def person_name(value: Any) -> str:
    if not isinstance(value, dict):
        return ""
    return (
        value.get("displayName")
        or value.get("name")
        or value.get("emailAddress")
        or value.get("accountId")
        or ""
    )


def named_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    result: list[str] = []
    for item in values:
        if isinstance(item, dict):
            result.append(str(item.get("name") or item.get("value") or item.get("key") or item))
        else:
            result.append(str(item))
    return result


def stub_info(stub: dict[str, Any]) -> dict[str, str]:
    fields = stub.get("fields") or {}
    status = fields.get("status") or {}
    issue_type = fields.get("issuetype") or {}
    return {
        "key": str(stub.get("key") or ""),
        "summary": str(fields.get("summary") or ""),
        "status": str(status.get("name") or ""),
        "issueType": str(issue_type.get("name") or ""),
    }


def collect_explicit_links(issue: dict[str, Any]) -> list[dict[str, str]]:
    fields = issue.get("fields") or {}
    links: list[dict[str, str]] = []

    parent = fields.get("parent")
    if isinstance(parent, dict) and parent.get("key"):
        info = stub_info(parent)
        info["relation"] = "parent"
        links.append(info)

    for subtask in fields.get("subtasks") or []:
        if isinstance(subtask, dict) and subtask.get("key"):
            info = stub_info(subtask)
            info["relation"] = "subtask"
            links.append(info)

    for link in fields.get("issuelinks") or []:
        if not isinstance(link, dict):
            continue
        link_type = link.get("type") or {}
        if isinstance(link.get("outwardIssue"), dict):
            info = stub_info(link["outwardIssue"])
            info["relation"] = str(link_type.get("outward") or link_type.get("name") or "links to")
            links.append(info)
        elif isinstance(link.get("inwardIssue"), dict):
            info = stub_info(link["inwardIssue"])
            info["relation"] = str(link_type.get("inward") or link_type.get("name") or "linked from")
            links.append(info)

    deduped: dict[tuple[str, str], dict[str, str]] = {}
    for link in links:
        key = link.get("key", "").upper()
        if key:
            link["key"] = key
            deduped[(key, link.get("relation", ""))] = link
    return list(deduped.values())


def collect_comments(fields: dict[str, Any], count: int, max_text_chars: int) -> list[dict[str, str]]:
    if count <= 0:
        return []
    comment_obj = fields.get("comment") or {}
    comments = comment_obj.get("comments") if isinstance(comment_obj, dict) else []
    if not isinstance(comments, list):
        return []
    comments = sorted(comments, key=lambda item: str(item.get("created") or ""))[-count:]
    result: list[dict[str, str]] = []
    for comment in comments:
        if not isinstance(comment, dict):
            continue
        body = truncate(clean_text(render_adf(comment.get("body"))), max_text_chars)
        if not body:
            continue
        result.append(
            {
                "author": person_name(comment.get("author")),
                "created": str(comment.get("created") or ""),
                "updated": str(comment.get("updated") or ""),
                "body": body,
            }
        )
    return result


def normalize_issue(
    issue: dict[str, Any], client: JiraClient, comments: int, max_text_chars: int
) -> dict[str, Any]:
    fields = issue.get("fields") or {}
    status = fields.get("status") or {}
    issue_type = fields.get("issuetype") or {}
    priority = fields.get("priority") or {}
    resolution = fields.get("resolution") or {}
    key = str(issue.get("key") or "").upper()
    description = truncate(clean_text(render_adf(fields.get("description"))), max_text_chars)
    normalized = {
        "key": key,
        "id": str(issue.get("id") or ""),
        "url": client.issue_url(key),
        "apiVersion": issue.get("_apiVersion"),
        "summary": str(fields.get("summary") or ""),
        "issueType": str(issue_type.get("name") or ""),
        "status": str(status.get("name") or ""),
        "priority": str(priority.get("name") or ""),
        "assignee": person_name(fields.get("assignee")) or "Unassigned",
        "reporter": person_name(fields.get("reporter")),
        "created": str(fields.get("created") or ""),
        "updated": str(fields.get("updated") or ""),
        "dueDate": str(fields.get("duedate") or ""),
        "resolution": str(resolution.get("name") or ""),
        "resolutionDate": str(fields.get("resolutiondate") or ""),
        "labels": fields.get("labels") or [],
        "components": named_list(fields.get("components")),
        "fixVersions": named_list(fields.get("fixVersions")),
        "versions": named_list(fields.get("versions")),
        "description": description,
        "comments": collect_comments(fields, comments, max_text_chars),
        "links": collect_explicit_links(issue),
    }
    return normalized


def referenced_issue_keys(issue: dict[str, Any]) -> list[str]:
    text_parts = [issue.get("description") or ""]
    for comment in issue.get("comments") or []:
        text_parts.append(comment.get("body") or "")
    found: list[str] = []
    for part in text_parts:
        for match in KEY_RE.finditer(part):
            key = match.group(0).upper()
            if key != issue.get("key") and key not in found:
                found.append(key)
    return found


def fetch_context(args: Args) -> dict[str, Any]:
    root_key = extract_issue_key(args.issue)
    if not root_key:
        raise SystemExit(f"Could not find a Jira issue key in: {args.issue}")

    base_url = infer_base_url(args.issue, args.base_url)
    client = JiraClient(base_url, args.api_version)

    issues: dict[str, dict[str, Any]] = {}
    queue: deque[tuple[str, int]] = deque([(root_key, 0)])
    enqueued = {root_key}
    skipped: list[str] = []
    fetch_errors: list[dict[str, str]] = []

    while queue and len(issues) < args.max_issues:
        key, depth = queue.popleft()
        try:
            raw_issue = client.get_issue(key)
        except JiraHTTPError as exc:
            if key == root_key:
                raise
            fetch_errors.append(
                {
                    "key": key,
                    "status": str(exc.code),
                    "reason": exc.reason,
                }
            )
            continue
        issue = normalize_issue(raw_issue, client, args.comments, args.max_text_chars)
        issues[key] = issue

        if depth >= args.depth:
            continue

        next_keys: list[str] = []
        for link in issue.get("links") or []:
            linked_key = str(link.get("key") or "").upper()
            if linked_key and linked_key not in next_keys:
                next_keys.append(linked_key)
        if args.follow_references:
            for referenced_key in referenced_issue_keys(issue):
                if referenced_key not in next_keys:
                    issue.setdefault("links", []).append(
                        {
                            "key": referenced_key,
                            "summary": "",
                            "status": "",
                            "issueType": "",
                            "relation": "referenced in text",
                        }
                    )
                    next_keys.append(referenced_key)

        for linked_key in next_keys:
            if linked_key in enqueued or linked_key in issues:
                continue
            if len(enqueued) >= args.max_issues:
                skipped.append(linked_key)
                continue
            enqueued.add(linked_key)
            queue.append((linked_key, depth + 1))

    return {
        "baseUrl": base_url,
        "rootKey": root_key,
        "depth": args.depth,
        "maxIssues": args.max_issues,
        "issues": list(issues.values()),
        "skippedIssueKeys": skipped,
        "fetchErrors": fetch_errors,
    }


def format_list(values: list[str]) -> str:
    return ", ".join(str(value) for value in values if value) or "-"


def issue_by_key(context: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {issue["key"]: issue for issue in context.get("issues") or []}


def markdown_for_issue(issue: dict[str, Any], fetched: dict[str, dict[str, Any]]) -> str:
    lines: list[str] = []
    title = f"## {issue['key']} — {issue.get('summary') or ''}".rstrip()
    lines.append(title)
    lines.append("")
    details = [
        ("URL", issue.get("url")),
        ("Type", issue.get("issueType")),
        ("Status", issue.get("status")),
        ("Priority", issue.get("priority")),
        ("Assignee", issue.get("assignee")),
        ("Reporter", issue.get("reporter")),
        ("Created", issue.get("created")),
        ("Updated", issue.get("updated")),
        ("Due", issue.get("dueDate")),
        ("Resolution", issue.get("resolution")),
        ("Resolved", issue.get("resolutionDate")),
        ("Labels", format_list(issue.get("labels") or [])),
        ("Components", format_list(issue.get("components") or [])),
        ("Fix versions", format_list(issue.get("fixVersions") or [])),
        ("Affects versions", format_list(issue.get("versions") or [])),
    ]
    for label, value in details:
        if value:
            lines.append(f"- **{label}:** {value}")

    description = issue.get("description") or ""
    if description:
        lines.extend(["", "### Description", "", description])

    links = issue.get("links") or []
    if links:
        lines.extend(["", "### Linked issues", ""])
        for link in links:
            linked_key = link.get("key") or ""
            fetched_issue = fetched.get(linked_key)
            summary = link.get("summary") or (fetched_issue or {}).get("summary") or ""
            status = link.get("status") or (fetched_issue or {}).get("status") or ""
            relation = link.get("relation") or "linked"
            url = (fetched_issue or {}).get("url") or f"{issue.get('url', '').rsplit('/browse/', 1)[0]}/browse/{linked_key}"
            suffix = f" — {summary}" if summary else ""
            status_text = f" [{status}]" if status else ""
            lines.append(f"- **{relation}:** [{linked_key}]({url}){suffix}{status_text}")

    comments = issue.get("comments") or []
    if comments:
        lines.extend(["", "### Recent comments", ""])
        for comment in comments:
            heading = f"- **{comment.get('author') or 'Unknown'}**"
            if comment.get("created"):
                heading += f" at {comment['created']}"
            body = (comment.get("body") or "").replace("\n", "\n  ")
            lines.append(f"{heading}:\n  {body}")

    return "\n".join(lines).rstrip()


def format_markdown(context: dict[str, Any]) -> str:
    fetched = issue_by_key(context)
    lines = [
        "# Jira issue context",
        "",
        f"- **Base URL:** {context['baseUrl']}",
        f"- **Root issue:** {context['rootKey']}",
        f"- **Follow depth:** {context['depth']}",
        f"- **Issues fetched:** {len(context.get('issues') or [])}",
    ]
    skipped = context.get("skippedIssueKeys") or []
    if skipped:
        lines.append(f"- **Skipped due to max issue limit:** {', '.join(skipped)}")
    fetch_errors = context.get("fetchErrors") or []
    if fetch_errors:
        formatted = ", ".join(
            f"{item.get('key')} ({item.get('status')} {item.get('reason')})" for item in fetch_errors
        )
        lines.append(f"- **Linked issues not fetched:** {formatted}")
    lines.append("")

    for issue in context.get("issues") or []:
        lines.append(markdown_for_issue(issue, fetched))
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> Args:
    parser = argparse.ArgumentParser(
        description="Fetch Jira issue details and follow linked Jira issues."
    )
    parser.add_argument("issue", help="Jira issue URL or key, for example https://jira/browse/ABC-123")
    parser.add_argument(
        "--base-url",
        default=first_env(["JIRA_BASE_URL", "ATLASSIAN_BASE_URL"]),
        help="Jira base URL. Required when passing only an issue key. Defaults to JIRA_BASE_URL.",
    )
    parser.add_argument(
        "--api-version",
        choices=["2", "3"],
        default=os.environ.get("JIRA_API_VERSION"),
        help="Jira REST API version. Defaults to trying 3 then 2.",
    )
    parser.add_argument("--depth", type=int, default=1, help="Link depth to follow. 0 = root only. Default: 1.")
    parser.add_argument("--max-issues", type=int, default=20, help="Maximum issues to fetch. Default: 20.")
    parser.add_argument(
        "--comments",
        type=int,
        default=5,
        help="Number of recent comments to include per issue. Use 0 to omit. Default: 5.",
    )
    parser.add_argument(
        "--follow-references",
        dest="follow_references",
        action="store_true",
        default=True,
        help="Also follow Jira issue keys/URLs referenced in descriptions and comments. Default: on.",
    )
    parser.add_argument(
        "--no-follow-references",
        dest="follow_references",
        action="store_false",
        help="Only follow explicit Jira issue links, parent, and subtasks.",
    )
    parser.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="Output format. Default: markdown.",
    )
    parser.add_argument(
        "--max-text-chars",
        type=int,
        default=6000,
        help="Maximum description/comment body characters per text block. Default: 6000.",
    )
    ns = parser.parse_args()
    return Args(
        issue=ns.issue,
        base_url=ns.base_url,
        api_version=ns.api_version,
        depth=max(ns.depth, 0),
        max_issues=max(ns.max_issues, 1),
        comments=max(ns.comments, 0),
        follow_references=ns.follow_references,
        output_format=ns.format,
        max_text_chars=max(ns.max_text_chars, 0),
    )


def print_auth_help() -> None:
    eprint("")
    eprint("Authentication hint:")
    eprint("  Jira Cloud: set JIRA_EMAIL and JIRA_API_TOKEN (or ATLASSIAN_API_TOKEN).")
    eprint("  Jira Data Center/PAT: set JIRA_BEARER_TOKEN or JIRA_PAT.")
    eprint("  Do not paste tokens into the Pi chat; export them in your shell or secret manager.")


def main() -> int:
    args = parse_args()
    try:
        context = fetch_context(args)
    except JiraHTTPError as exc:
        eprint(str(exc))
        if exc.code in {401, 403}:
            print_auth_help()
        return 1
    except Exception as exc:  # noqa: BLE001 - CLI should report concise errors
        eprint(str(exc))
        return 1

    if args.output_format == "json":
        print(json.dumps(context, indent=2, ensure_ascii=False))
    else:
        print(format_markdown(context), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
