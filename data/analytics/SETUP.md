# Analytics setup for dejaviewed.dev

Do these once. Each step says where to click and what to save. Never paste a token or key into chat,
a commit, or any file other than the two credential files named below.

Check progress at any time:

```bash
bash scripts/analytics_check.sh
```

## Cloudflare

1. **Turn on Web Analytics for the Pages project (real-visitor page views + Web Vitals).**
   Cloudflare dashboard → Workers & Pages → select the dejaviewed Pages project → Metrics tab →
   Web Analytics → Enable. This uses automatic injection, so no code change is needed.
   The beacon is added on the next deployment, so redeploy (push to main) after enabling.
   Alternative path: Analytics & Logs → Web Analytics → Add a site → `dejaviewed.dev` → choose
   "Enable with automatic setup" (works because the domain's DNS is on Cloudflare).

2. **Create a read-only API token.**
   Dashboard top-right profile icon → My Profile → API Tokens → Create Token →
   "Create Custom Token" → Get started.
   - Token name: `dejaviewed-analytics-read`
   - Permissions, three rows:
     - Account → Account Analytics → Read
     - Zone → Analytics → Read
     - Zone → Zone → Read
   - Account Resources: Include → your account.
   - Zone Resources: Include → Specific zone → `dejaviewed.dev`.
   - Leave IP filtering and TTL empty, or set a TTL if you want it to expire.
   - Continue to summary → Create Token. Copy the token. It is shown once.

3. **Save the token to the credential file.** In a terminal, not in chat:

   ```bash
   mkdir -p ~/.config/cloudflare
   ${EDITOR:-nano} ~/.config/cloudflare/dejaviewed.env
   ```

   Put exactly this line in the file, with your token after the equals sign:

   ```
   CLOUDFLARE_API_TOKEN=paste-token-here
   ```

   Optional lines, which the script otherwise looks up for you:
   `CLOUDFLARE_ZONE_ID=...` (dejaviewed.dev → Overview → right sidebar "Zone ID") and
   `CLOUDFLARE_ACCOUNT_ID=...` (same sidebar, "Account ID"). Then lock it down:

   ```bash
   chmod 600 ~/.config/cloudflare/dejaviewed.env
   ```

   The script refuses to read the file unless its mode is exactly 600.

## Google Search Console

4. **Add the domain property.** Go to https://search.google.com/search-console → property dropdown
   (top-left) → Add property → choose the left box, "Domain" → type `dejaviewed.dev` → Continue.
   Google shows a TXT record that starts with `google-site-verification=`. Copy it.
   If Google offers "Verify with Cloudflare" automatically, you can accept that and skip step 5.

5. **Verify via Cloudflare DNS.** Cloudflare dashboard → `dejaviewed.dev` → DNS → Records → Add record.
   - Type: `TXT`
   - Name: `@`
   - Content: the full `google-site-verification=...` string
   - TTL: Auto → Save.
   Back in Search Console, click Verify. If it fails, wait 5 minutes and retry.
   Leave the TXT record in place forever. Removing it un-verifies the property.

6. **Create a Google Cloud project and enable the API.** Go to https://console.cloud.google.com →
   project picker (top bar) → New Project → name `dejaviewed-analytics` → Create, then select it.
   Then APIs & Services → Library → search "Google Search Console API" → open it → Enable.

7. **Create a service account and download its key.**
   IAM & Admin → Service Accounts → Create service account.
   - Name: `dejaviewed-gsc` → Create and continue.
   - Skip the role and user-access steps → Done.
   - Click the new account → Keys tab → Add key → Create new key → JSON → Create. A .json file downloads.
   - Copy the account's email address. It looks like `dejaviewed-gsc@dejaviewed-analytics.iam.gserviceaccount.com`.

   Move the key into place and lock it down:

   ```bash
   mkdir -p ~/.config/google
   mv ~/Downloads/dejaviewed-analytics-*.json ~/.config/google/dejaviewed-gsc.json
   chmod 600 ~/.config/google/dejaviewed-gsc.json
   ```

8. **Grant the service account access to the property.** Search Console → select `dejaviewed.dev` →
   Settings (bottom-left) → Users and permissions → Add user → paste the service-account email →
   Permission: Full → Add.

9. **Submit the sitemap.** Search Console → Sitemaps (left menu) → "Add a new sitemap" field →
   type `sitemap.xml` → Submit. The full URL is https://dejaviewed.dev/sitemap.xml.

10. **Install the Python libraries the report needs.**

    ```bash
    pip install --user google-api-python-client google-auth
    ```

## Bing Webmaster Tools

11. **Import the site from Search Console.** Go to https://www.bing.com/webmasters → sign in →
    "Import your sites from GSC" → Import → sign in with the same Google account and allow access →
    tick `dejaviewed.dev` → Import. Sitemaps come across with it. Bing also consumes IndexNow, step 13.

## Run the report

12. **Run the report.**

    ```bash
    python3 scripts/analytics_report.py            # writes data/analytics/<date>.json + reports/analytics_<date>.md
    python3 scripts/analytics_report.py --dry-run  # shows what it would query, no network
    python3 scripts/analytics_report.py --only cf  # Cloudflare only; --only gsc for Search Console only
    ```

    Anything still missing prints as `missing: <what> -- do: <step>`. Search data lags about 3 days,
    and a brand-new property shows nothing for the first few days.

## IndexNow after each deploy

13. **Ping Bing, Yandex, and Seznam after every deploy.** The key is public by design and is committed
    as `data/seo/indexnow.key` and `site/<key>.txt`. The script refuses to submit until the key file is
    live on the site.

    ```bash
    python3 scripts/indexnow.py --init-key     # once; then commit + deploy
    python3 scripts/indexnow.py --dry-run      # preview the URL list
    python3 scripts/indexnow.py                # after each deploy: submit all sitemap URLs
    python3 scripts/indexnow.py --changed-since 2026-10-20   # only works once the sitemap carries <lastmod>
    ```

    Response codes: 200/202 accepted, 403 key not found or invalid, 422 URLs don't match the host,
    429 too many submissions, so back off for a day.
