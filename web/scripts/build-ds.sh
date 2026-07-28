#!/usr/bin/env bash
set -euo pipefail
export PATH="/home/krishna/.nvm/versions/node/v20.20.2/bin:$PATH"
cd /home/krishna/legal-ai-copilot/web
./node_modules/.bin/next build 2>&1 | tee /tmp/next-build-ds.txt | tail -80
echo BUILD_EXIT:${PIPESTATUS[0]}
