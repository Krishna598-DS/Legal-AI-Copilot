#!/usr/bin/env bash
set -euo pipefail
export PATH="/home/krishna/.nvm/versions/node/v20.20.2/bin:$PATH"
cd /home/krishna/legal-ai-copilot/web
node -v
npx --yes shadcn@latest add -y form
test -f src/components/ui/form.tsx && echo FORM_OK || echo FORM_MISSING
npm ls framer-motion react-hook-form zod @hookform/resolvers @tanstack/react-query next-themes --depth=0
