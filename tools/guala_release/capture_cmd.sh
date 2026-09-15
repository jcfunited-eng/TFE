#!/usr/bin/env bash
# Capture the live body and world from the running container into S=<scratch>/live-capture-<NAME>/current.zip
# (a presigned S3 PUT from inside the container by `aws ecs execute-command`, then copied down).
# Usage: NAME=0915e S=/path/to/scratch bash capture_cmd.sh
set -euo pipefail
export AWS_PAGER=""
NAME=${NAME:?capture name, e.g. 0915e}
S=${S:?scratch directory}
HERE=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$S/live-capture-$NAME"
R=us-east-1; KEY=captures/$NAME/current.zip
PUT=$(python3 -c "
import boto3
from botocore.config import Config
s3 = boto3.client('s3', region_name='us-east-1', config=Config(signature_version='s3v4'))
print(s3.generate_presigned_url('put_object', Params={'Bucket': 'guala-incident-bench-20260831', 'Key': '$KEY'}, ExpiresIn=900))")
PUT_B64=$(printf '%s' "$PUT" | base64 -w0)
SCRIPT_B64=$(base64 -w0 "$HERE/capture_pair_remote.py")
TASK=$(aws ecs list-tasks --cluster tfe-web-cluster --service-name dsf-ai-service-lb --region $R --query 'taskArns[0]' --output text | awk -F/ '{print $NF}')
timeout 400 aws ecs execute-command --region $R --cluster tfe-web-cluster --task "$TASK" --container dsf-ai --interactive \
  --command "sh -c 'echo $SCRIPT_B64 | base64 -d > /tmp/capture_pair.py && cd /app && python3 /tmp/capture_pair.py $PUT_B64 2>&1 | tail -2'" 2>&1 \
  | grep -v "^$\|Starting session\|Exiting session\|Cannot perform\|Session Manager" | head -3 | tee "$S/live-capture-$NAME/capture.log"
aws s3 cp "s3://guala-incident-bench-20260831/$KEY" "$S/live-capture-$NAME/current.zip" --only-show-errors && unzip -l "$S/live-capture-$NAME/current.zip" | tail -2
