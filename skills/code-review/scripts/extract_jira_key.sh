#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
  echo "usage: $0 <text-file>" >&2
  exit 1
fi

perl -ne 'if (/\[([A-Z][A-Z0-9]+-[0-9]+)\]/) { print "$1\n"; exit } if (/\b([A-Z][A-Z0-9]+-[0-9]+)\b/) { print "$1\n"; exit }' "$1"
