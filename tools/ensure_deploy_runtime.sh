#!/usr/bin/env bash
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive

need_update=0
need_install=()

if ! command -v aws >/dev/null 2>&1; then
  need_install+=(awscli)
  need_update=1
fi
if ! command -v jq >/dev/null 2>&1; then
  need_install+=(jq)
  need_update=1
fi
if ! command -v zip >/dev/null 2>&1; then
  need_install+=(zip)
  need_update=1
fi
if ! command -v unzip >/dev/null 2>&1; then
  need_install+=(unzip)
  need_update=1
fi

if [ "$need_update" -eq 1 ]; then
  apt-get update
  apt-get install -y --no-install-recommends "${need_install[@]}"
fi

aws --version
jq --version
zip -v | sed -n '1p'
unzip -v | sed -n '1p'

if [ -r /root/.aws/credentials ] || [ -r /root/.aws/config ]; then
  echo "aws_mount_status=present"
else
  echo "aws_mount_status=missing"
fi
