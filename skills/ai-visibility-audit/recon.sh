#!/usr/bin/env bash
# ai-visibility-audit recon: surface signals for a storefront, all public.
# Usage: ./recon.sh <domain> [product_handle]
#   ./recon.sh atlasskateboarding.com
# Prints the raw numbers the audit deck must trace back to. Tuned for Shopify;
# most checks still work on other platforms (counts may not).
set -uo pipefail
DOMAIN="${1:?usage: recon.sh <domain> [product_handle]}"
BASE="https://${DOMAIN#http*://}"; BASE="${BASE%/}"
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
W="$(mktemp -d)"; trap 'rm -rf "$W"' EXIT
get(){ curl -sS -A "$UA" -L --max-time 25 "$@"; }

echo "# Recon: $BASE   ($(date -u +%Y-%m-%dT%H:%MZ))"

get -o "$W/home.html" "$BASE/"
echo "## Homepage"
echo -n "platform shopify: "; grep -c -i "cdn.shopify.com" "$W/home.html"
echo -n "title: "; grep -o -i "<title>[^<]*</title>" "$W/home.html" | head -1
echo -n "meta desc: "; grep -o -i '<meta name="description" content="[^"]*"' "$W/home.html" | head -1
echo -n "h1 count: "; grep -o -i "<h1" "$W/home.html" | wc -l | tr -d ' '
echo -n "og:image: "; grep -o -i '<meta property="og:image"[^>]*>' "$W/home.html" | head -1
echo -n "homepage ld+json @types: "; grep -o -i '"@type"[ ]*:[ ]*"[^"]*"' "$W/home.html" | sort | uniq -c | tr '\n' ' '; echo
echo -n "pixels: "; grep -o -i "connect.facebook.net\|fbq(\|G-[A-Z0-9]\{8,\}\|AW-[0-9]*\|analytics.tiktok\|pintrk" "$W/home.html" | sort -u | tr '\n' ' '; echo
echo -n "meta system-user token (empty/dash = CAPI not wired): "; grep -o -i 'metaapp_system_user_token[^,}]*' "$W/home.html" | head -1; echo

echo "## AI / agent layer"
get -o "$W/robots.txt" "$BASE/robots.txt"
echo -n "robots references: "; grep -o -i "agents.md\|/ucp\|llms.txt" "$W/robots.txt" | sort -u | tr '\n' ' '; echo
get -o "$W/llms.txt" -w "llms.txt: HTTP %{http_code}, %{size_download} bytes (4-5KB generic = boilerplate)\n" "$BASE/llms.txt" >/dev/null

echo "## Catalog size (sitemaps)"
get -o "$W/sitemap.xml" "$BASE/sitemap.xml"
total=0
for sm in $(grep -o "$BASE/sitemap_products[^<]*" "$W/sitemap.xml" | sed 's/&amp;/\&/g'); do
  n=$(get "$sm" | grep -o "$BASE/products/" | wc -l | tr -d ' ')
  echo "  products sitemap -> $n"; total=$((total+n))
done
echo "products total: $total"
echo -n "collections: "; get "$BASE/collections.json?limit=250" | python3 -c "import json,sys;print(len(json.load(sys.stdin).get('collections',[])),'(page1, 250 cap)')" 2>/dev/null || echo "n/a"
echo -n "blog article URLs: "; get "$BASE/sitemap_blogs_1.xml" 2>/dev/null | grep -o "$BASE/blogs/[a-z0-9-]*/[a-z0-9-][^<]*" | wc -l | tr -d ' '

echo "## Product page schema"
HANDLE="${2:-}"
[ -z "$HANDLE" ] && HANDLE=$(get "$BASE/products.json?limit=1" | python3 -c "import json,sys;print(json.load(sys.stdin)['products'][0]['handle'])" 2>/dev/null)
if [ -n "${HANDLE:-}" ]; then
  get -o "$W/prod.html" "$BASE/products/$HANDLE"
  echo "handle: $HANDLE"
  echo -n "product ld+json @types: "; grep -o -i '"@type"[ ]*:[ ]*"[^"]*"' "$W/prod.html" | sort | uniq -c | tr '\n' ' '; echo
else
  echo "(no product handle; pass one as arg 2 for non-Shopify sites)"
fi
