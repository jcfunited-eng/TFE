#!/usr/bin/env bash
set -euo pipefail

echo "ERROR: the isolated GualaLoom V7 bridge release path is retired." >&2
echo "       It cannot package or deploy repository source." >&2
echo "       Use tools/deploy_dsf_ai.sh for the reviewed Guala release." >&2
exit 64
