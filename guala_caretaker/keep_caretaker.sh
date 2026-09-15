#!/usr/bin/env bash
# Keeps the caretaker alive: every minute, if no caretaker holds its lock and no STOP
# file asks it to stop, start one. A cutover's minutes of 503s no longer leave her uncared for.
cd "$(dirname "$0")"
while true; do
  if [ ! -e STOP ] && flock -n .lock true 2>/dev/null; then
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) keep_caretaker: no caretaker holds the lock; starting one" >> caretaker.log
    nohup python3 caretaker.py >> caretaker.out 2>&1 &
    sleep 5
  fi
  sleep 60
done
