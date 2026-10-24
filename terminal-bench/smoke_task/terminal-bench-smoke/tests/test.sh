#!/bin/bash
set -euo pipefail

if [[ -f /app/ready.txt ]] && [[ "$(cat /app/ready.txt)" == "ready" ]]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
