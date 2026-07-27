#!/usr/bin/env bash
set -euo pipefail
export PATH="/home/krishna/.nvm/versions/node/v20.20.2/bin:$PATH"
cd /home/krishna/legal-ai-copilot/web
npm install -D tailwindcss@latest @tailwindcss/postcss@latest postcss@latest 2>&1 | tail -30
npm uninstall tw-animate-css 2>&1 | tail -5 || true
# keep tw-animate if shadcn needs it
npm install tw-animate-css 2>&1 | tail -10
ls node_modules/tailwindcss/package.json
node -e "console.log(require('tailwindcss/package.json').version)"
