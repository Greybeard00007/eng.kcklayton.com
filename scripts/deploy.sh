#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DIR"

echo "=== [1/3] Building Astro site ==="
npm run build

echo "=== [2/3] Syncing dist to server:/srv/www/eng ==="
rsync -avz --delete "$DIR/dist/" server:/srv/www/eng/

echo "=== [3/3] Verifying live endpoint ==="
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" https://eng.kcklayton.com)
if [ "$HTTP_CODE" = "200" ]; then
    echo "✓ Production deployment verified: https://eng.kcklayton.com (HTTP 200 OK)"
else
    echo "⚠ Warning: Received HTTP $HTTP_CODE from https://eng.kcklayton.com"
fi
