#!/bin/sh
set -eu

if [ "$#" -ne 7 ]; then
  echo "usage: $0 <mr-number> <base-sha> <head-sha> <start-sha> <file-path> <new-line> <body-file>" >&2
  exit 1
fi

MR_NUMBER="$1"
BASE_SHA="$2"
HEAD_SHA="$3"
START_SHA="$4"
FILE_PATH="$5"
NEW_LINE="$6"
BODY_FILE="$7"

if [ ! -f "$BODY_FILE" ]; then
  echo "body file not found: $BODY_FILE" >&2
  exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required for $0" >&2
  exit 1
fi

COMMENTS_FILE="$(mktemp)"
cleanup() {
  rm -f "$COMMENTS_FILE"
}
trap cleanup EXIT INT TERM

jq -n \
  --arg file_path "$FILE_PATH" \
  --argjson new_line "$NEW_LINE" \
  --rawfile body "$BODY_FILE" \
  '[{path: $file_path, line: $new_line, body: $body}]' > "$COMMENTS_FILE"

python3 "$(dirname "$0")/post_inline_comments.py" \
  --mr "$MR_NUMBER" \
  --base-sha "$BASE_SHA" \
  --head-sha "$HEAD_SHA" \
  --start-sha "$START_SHA" \
  --comments-file "$COMMENTS_FILE"
