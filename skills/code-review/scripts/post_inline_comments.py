#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


class GlabError(RuntimeError):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Post GitLab inline MR comments as draft notes, then publish them together "
            "as one review."
        )
    )
    parser.add_argument("--mr", required=True)
    parser.add_argument("--base-sha", required=True)
    parser.add_argument("--head-sha", required=True)
    parser.add_argument("--start-sha", required=True)
    parser.add_argument("--comments-file", required=True, help="JSON array of {path, line, body}")
    parser.add_argument(
        "--allow-existing-drafts",
        action="store_true",
        help=(
            "Continue even if this user already has pending draft notes on the MR. "
            "GitLab bulk_publish publishes all pending drafts for the user, including pre-existing ones."
        ),
    )
    return parser.parse_args()


def load_comments(path: str) -> list[dict[str, Any]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("comments file must be a JSON array")

    validated = []
    for index, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"comment {index} must be an object")
        for key in ("path", "line", "body"):
            if key not in item:
                raise ValueError(f"comment {index} missing key: {key}")
        if not isinstance(item["path"], str) or not item["path"]:
            raise ValueError(f"comment {index} has invalid path")
        if not isinstance(item["line"], int):
            raise ValueError(f"comment {index} has invalid line")
        if not isinstance(item["body"], str) or not item["body"].strip():
            raise ValueError(f"comment {index} has invalid body")
        validated.append(item)
    return validated


def glab_api(method: str, endpoint: str, payload: dict[str, Any] | None = None) -> subprocess.CompletedProcess[str]:
    command = ["glab", "api", "--method", method]
    payload_path = None

    if payload is not None:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
            json.dump(payload, handle)
            handle.flush()
            payload_path = handle.name
        command.extend(["--header", "content-type:application/json", "--input", payload_path])

    command.append(endpoint)

    try:
        return subprocess.run(command, capture_output=True, text=True)
    finally:
        if payload_path is not None:
            Path(payload_path).unlink(missing_ok=True)


def result_error(result: subprocess.CompletedProcess[str]) -> str:
    return (result.stderr or result.stdout).strip()


def parse_json_output(result: subprocess.CompletedProcess[str], context: str) -> Any:
    try:
        return json.loads(result.stdout or "null")
    except json.JSONDecodeError as error:
        raise GlabError(f"{context} returned non-JSON output: {error}: {result.stdout[:500]}") from error


def draft_notes_endpoint(args: argparse.Namespace, suffix: str = "") -> str:
    return f"projects/:id/merge_requests/{args.mr}/draft_notes{suffix}"


def list_draft_notes(args: argparse.Namespace) -> list[dict[str, Any]]:
    result = glab_api("GET", draft_notes_endpoint(args))
    if result.returncode != 0:
        raise GlabError(f"failed to list existing draft notes: {result_error(result)}")

    data = parse_json_output(result, "list draft notes")
    if not isinstance(data, list):
        raise GlabError("list draft notes returned unexpected JSON shape")
    return data


def describe_draft(draft: dict[str, Any]) -> str:
    position = draft.get("position") if isinstance(draft.get("position"), dict) else {}
    path = position.get("new_path") or position.get("old_path") or "MR overview"
    line = position.get("new_line") or position.get("old_line")
    location = f"{path}:{line}" if line else str(path)
    note = str(draft.get("note") or "").strip().splitlines()
    preview = note[0][:80] if note else ""
    return f"draft #{draft.get('id')} at {location}: {preview}"


def create_draft_note(args: argparse.Namespace, comment: dict[str, Any]) -> tuple[int | None, str]:
    payload = {
        "note": comment["body"],
        "position": {
            "base_sha": args.base_sha,
            "head_sha": args.head_sha,
            "start_sha": args.start_sha,
            "position_type": "text",
            "new_path": comment["path"],
            "old_path": comment["path"],
            "new_line": comment["line"],
        },
    }

    result = glab_api("POST", draft_notes_endpoint(args), payload)
    if result.returncode != 0:
        return None, result_error(result)

    data = parse_json_output(result, "create draft note")
    if isinstance(data, list) and data:
        data = data[0]
    if not isinstance(data, dict):
        return None, f"unexpected create draft note response: {result.stdout[:500]}"

    draft_id = data.get("id")
    if not isinstance(draft_id, int):
        return None, f"create draft note response did not contain an integer id: {result.stdout[:500]}"

    return draft_id, result.stdout.strip()


def delete_draft_note(args: argparse.Namespace, draft_id: int) -> bool:
    result = glab_api("DELETE", draft_notes_endpoint(args, f"/{draft_id}"))
    return result.returncode == 0


def cleanup_created_drafts(args: argparse.Namespace, draft_ids: list[int]) -> None:
    if not draft_ids:
        return

    print("Cleaning up draft notes created by this run after failure...", file=sys.stderr)
    for draft_id in draft_ids:
        if delete_draft_note(args, draft_id):
            print(f"CLEANED draft #{draft_id}", file=sys.stderr)
        else:
            print(f"FAILED to clean draft #{draft_id}; discard it manually in GitLab", file=sys.stderr)


def publish_draft_notes(args: argparse.Namespace) -> tuple[bool, str]:
    result = glab_api("POST", draft_notes_endpoint(args, "/bulk_publish"))
    if result.returncode == 0:
        return True, result.stdout.strip()
    return False, result_error(result)


def main() -> int:
    try:
        args = parse_args()
        comments = load_comments(args.comments_file)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"FAIL invalid input: {error}", file=sys.stderr)
        return 1

    if not comments:
        print("No comments to post.")
        return 0

    try:
        existing_drafts = list_draft_notes(args)
    except GlabError as error:
        print(f"FAIL {error}", file=sys.stderr)
        return 1

    if existing_drafts and not args.allow_existing_drafts:
        print(
            "FAIL this user already has pending draft notes on this MR. "
            "Publishing would include those drafts too. Submit/discard them first, or rerun with "
            "--allow-existing-drafts if that is intentional.",
            file=sys.stderr,
        )
        for draft in existing_drafts[:10]:
            print(f"- {describe_draft(draft)}", file=sys.stderr)
        if len(existing_drafts) > 10:
            print(f"- ... and {len(existing_drafts) - 10} more", file=sys.stderr)
        return 1

    created_draft_ids: list[int] = []
    created_comments: list[dict[str, Any]] = []

    for comment in comments:
        location = f"{comment['path']}:{comment['line']}"
        try:
            draft_id, output = create_draft_note(args, comment)
        except GlabError as error:
            print(f"FAIL {location}: {error}", file=sys.stderr)
            cleanup_created_drafts(args, created_draft_ids)
            return 1

        if draft_id is None:
            print(f"FAIL {location}: {output}", file=sys.stderr)
            cleanup_created_drafts(args, created_draft_ids)
            return 1

        created_draft_ids.append(draft_id)
        created_comments.append(comment)
        print(f"DRAFT {location} #{draft_id}")

    ok, output = publish_draft_notes(args)
    if not ok:
        print(f"FAIL bulk publish: {output}", file=sys.stderr)
        print(
            "Draft notes were created but not published. Submit or discard them manually in GitLab.",
            file=sys.stderr,
        )
        for draft_id in created_draft_ids:
            print(f"- draft #{draft_id}", file=sys.stderr)
        return 1

    print(f"PUBLISHED {len(created_comments)} inline comments as one GitLab review")
    for comment in created_comments:
        print(f"OK {comment['path']}:{comment['line']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
