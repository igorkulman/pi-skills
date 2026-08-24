#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
  echo "usage: $0 <mr-number>" >&2
  exit 1
fi

MR_NUMBER="$1"

if command -v jq >/dev/null 2>&1; then
  glab api "projects/:id/merge_requests/${MR_NUMBER}/versions" | jq '.[0] | {base_commit_sha, head_commit_sha, start_commit_sha}'
else
  glab api "projects/:id/merge_requests/${MR_NUMBER}/versions"
fi
