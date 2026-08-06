# NAB Customer Performance

Public static dashboard: wholesale customer movers (Resellers / End Users / OEM).

## Production URLs

| URL | Notes |
|-----|--------|
| **https://nab-customer-performance.wvvy.co** | Preferred. Requires Cloudflare A → `178.156.217.235` (DNS only). |
| **https://os1hqxqflxpfedhd25jwkygo.178.156.217.235.sslip.io** | Live now. No password. Share this until DNS/LE settle. |

- **Auth**: none (public)
- **Coolify app UUID**: `os1hqxqflxpfedhd25jwkygo`
- **Auto-deploy**: push to `main` → GitHub Action SSHs to Hetzner → Coolify force deploy

## Cloudflare DNS (one record)

```
Type: A
Name: nab-customer-performance
IPv4: 178.156.217.235
Proxy: DNS only (grey cloud) — needed for Let's Encrypt HTTP-01
TTL: Auto
```

After DNS propagates, wait ~2–10 min for Traefik LE cert (may be rate-limited for ~1h if prior failed attempts).

## Local present

```bash
open public/index.html
# or
python3 -m http.server 8080 --directory public
```

Features: 5 KPI cards, month From/To range, compare previous month/quarter/year, segment tabs, top 20 accelerate/decline.

## Rebuild embedded data

```bash
python3 scripts/build_dashboard.py
```

## Stack

- Static HTML + Chart.js CDN
- Nginx alpine (`Dockerfile`)
- Coolify on Hetzner `178.156.217.235`
- Repo: https://github.com/whoiskevinmeyer/nab-customer-performance
