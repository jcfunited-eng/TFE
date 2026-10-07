#!/usr/bin/env bash
# One supervisor and one caretaker. File existence never means a held lock.
set -eu
cd "$(dirname "$0")/.."
exec 9>guala_caretaker/.supervisor.lock
flock -n 9 || exit 0
while [ ! -e guala_caretaker/STOP ]; do
  if flock -n guala_caretaker/.lock true; then
    # Foreground child: supervise its real lifetime; exclude supervisor lock FD.
    python3 -m guala_caretaker.caretaker 9>&- >>guala_caretaker/caretaker.out 2>&1 || {
      printf '%s caretaker exited with failure; retained state will be retried\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >>guala_caretaker/caretaker.out
    }
  fi
  [ -e guala_caretaker/STOP ] || sleep 20
done
