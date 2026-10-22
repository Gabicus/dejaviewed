#!/usr/bin/env bash
# Analytics readiness checklist. Existence + mode checks ONLY; never reads secret values.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CF="$HOME/.config/cloudflare/dejaviewed.env"
GSC="$HOME/.config/google/dejaviewed-gsc.json"
ok(){ printf '  [x] %s\n' "$1"; }
no(){ printf '  [ ] %s\n' "$1"; }

echo "dejaviewed analytics checklist ($(date +%F))"
echo "Credentials:"
if [ -f "$CF" ]; then
  ok "Cloudflare env file exists: $CF"
  m=$(stat -c %a "$CF")
  [ "$m" = 600 ] && ok "Cloudflare env file mode 600" || no "Cloudflare env file mode is $m -- do: chmod 600 $CF"
  # key-name presence only (grep -q prints nothing)
  for k in CLOUDFLARE_API_TOKEN CLOUDFLARE_ZONE_ID CLOUDFLARE_ACCOUNT_ID; do
    if grep -qE "^(export )?$k=.+" "$CF" 2>/dev/null; then ok "$k line present"
    elif [ "$k" = CLOUDFLARE_API_TOKEN ]; then no "$k line missing (required)"
    else no "$k line missing (optional, auto-looked-up)"; fi
  done
else
  no "Cloudflare env file missing: $CF -- see data/analytics/SETUP.md steps 2-3"
fi
if [ -f "$GSC" ]; then
  ok "Search Console key exists: $GSC"
  m=$(stat -c %a "$GSC")
  [ "$m" = 600 ] && ok "Search Console key mode 600" || no "Search Console key mode is $m -- do: chmod 600 $GSC"
else
  no "Search Console key missing: $GSC -- see data/analytics/SETUP.md steps 4-8"
fi

echo "Python deps:"
for mod in googleapiclient:google-api-python-client google.oauth2:google-auth; do
  m=${mod%%:*}; p=${mod##*:}
  if python3 -c "import $m" >/dev/null 2>&1; then ok "$p"; else no "$p -- do: pip install --user $p"; fi
done

echo "IndexNow:"
if [ -f "$ROOT/data/seo/indexnow.key" ]; then
  k=$(tr -d '[:space:]' < "$ROOT/data/seo/indexnow.key")   # public key by design
  ok "key file data/seo/indexnow.key"
  [ -f "$ROOT/site/$k.txt" ] && ok "site/$k.txt present (deploy to serve)" || no "site/<key>.txt missing -- do: python3 scripts/indexnow.py --init-key"
else
  no "no key -- do: python3 scripts/indexnow.py --init-key"
fi

echo "Reports:"
last=$(ls "$ROOT"/data/analytics/????-??-??.json 2>/dev/null | sort | tail -1)
if [ -n "$last" ]; then ok "last report: $(basename "$last" .json)"; else no "no report yet -- do: python3 scripts/analytics_report.py"; fi
