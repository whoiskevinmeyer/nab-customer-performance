# NAB Customer Performance

Public static dashboard: wholesale customer movers (Resellers / End Users / OEM).

## Production

- **URL**: https://nab-customer-performance.wvvy.co
- **Auth**: none (public)
- **Deploy**: Coolify on Hetzner (`178.156.217.235`), auto-deploy on push to `main`

## Local

Open `public/index.html` in a browser, or:

```bash
python3 -m http.server 8080 --directory public
```

## Rebuild data

Source Power BI extracts → rebuild embedded JSON in HTML:

```bash
python3 scripts/build_dashboard.py
```

## Stack

- Single static HTML + Chart.js CDN
- Nginx alpine container
- Coolify + Traefik + Let's Encrypt
- DNS: `nab-customer-performance.wvvy.co` → `178.156.217.235` (Cloudflare DNS only / proxy off for LE)
