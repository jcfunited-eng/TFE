#!/bin/bash
# Publishes exact channel-book snapshots when their authoritative files change.
# This process does not run a channel, mutate a book, or place an order.
cd "$(dirname "$0")/.." || exit 1
set -a
source .env 2>/dev/null
set +a

echo "[channel-book-publication] started $(date -u +%FT%TZ) pid $$"
while true; do
  python tools/publish_channel_books.py
  sleep 60
done
