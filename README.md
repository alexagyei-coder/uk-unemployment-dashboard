# UK Employment by Industry Dashboard

Interactive dashboard built on ONS EMP13 (Labour Force Survey).

**Live:** https://incandescent-buttercream-39cb44.netlify.app/

## Auto-updates

A GitHub Action runs on the 20th of each month, fetches the latest ONS EMP13
release, parses it, and commits an updated `data.json`. Netlify redeploys
automatically on every push to `main`.

ONS publishes EMP13 roughly quarterly (Feb, May, Aug, Nov).

## Files

| File | Purpose |
|------|---------|
| `index.html` | Dashboard — loads data from `data.json` |
| `data.json` | Employment data (auto-updated by Action) |
| `scripts/fetch_ons.py` | Fetches and parses the ONS XLS |
| `.github/workflows/update-data.yml` | Scheduled GitHub Action |

## Manual update

Trigger the Action manually from the **Actions** tab in GitHub anytime.

## Source

Office for National Statistics · EMP13 dataset · Labour Force Survey ·
United Kingdom · Not seasonally adjusted
