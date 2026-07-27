#!/usr/bin/env bash
set -euo pipefail
export PATH="/home/krishna/.nvm/versions/node/v20.20.2/bin:$PATH"
cd /home/krishna/legal-ai-copilot/web
./node_modules/.bin/tsc --noEmit 2>&1 | tee /tmp/tsc-auth.txt | tail -50
echo TSC_EXIT:${PIPESTATUS[0]}
