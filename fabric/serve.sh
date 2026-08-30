#!/bin/bash
# Start (or restart) the door on 8765. Pidfile-based; safe to rerun.
cd "$(dirname "$0")"
PIDFILE=/tmp/fabric_door.pid
if [ -f "$PIDFILE" ]; then
  OLD=$(cat "$PIDFILE")
  kill "$OLD" 2>/dev/null
  sleep 1
fi
setsid nohup python3 door.py > /tmp/door.log 2>&1 < /dev/null &
echo $! > "$PIDFILE"
sleep 8
curl -s --max-time 5 http://localhost:8765/pulse >/dev/null \
  && echo "door open on 8765 (pid $(cat $PIDFILE))" \
  || { echo "door failed to open:"; tail -5 /tmp/door.log; exit 1; }
