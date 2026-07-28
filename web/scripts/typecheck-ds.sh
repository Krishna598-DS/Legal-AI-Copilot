#!/usr/bin/env bash
set -euo pipefail
export PATH="/home/krishna/.nvm/versions/node/v20.20.2/bin:$PATH"
cd /home/krishna/legal-ai-copilot/web
node -v
npx tsc --noEmit 2>&1 | tee /tmp/tsc-ds.txt | tail -60
echo TSC_EXIT:${PIPESTATUS[0]}
