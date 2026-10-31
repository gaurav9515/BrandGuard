# BrandGuard Production Keep-Alive & Liveness Configuration

This directory contains the automated heartbeat configuration designed to keep Render's free tier web services awake without spinning down after 15 minutes of inactivity.

---

## 1. GitHub Actions Keep-Alive Workflow

The [`keepalive.yml`](./keepalive.yml) workflow fires every 12 minutes (`*/12 * * * *`) via GitHub Actions cron, pinging `https://<YOUR_RENDER_URL>/healthz`.

### Setup Instructions:
1. Navigate to your GitHub repository -> **Settings** -> **Secrets and variables** -> **Actions**.
2. Click **New repository secret**.
3. Name: `RENDER_APP_URL`
4. Value: `your-backend-app.onrender.com` (e.g. `brandguard-backend.onrender.com`).
5. Click **Add secret**.

The workflow runs automatically in the background and can also be triggered manually using the **Run workflow** button in the GitHub Actions tab.

---

## 2. Alternative Free External Uptime Monitors

If you prefer external monitoring with automated SMS/email alerts, use either of the free services below:

### Option A: UptimeRobot (Free - 50 monitors, 5-minute intervals)
1. Sign up at [UptimeRobot.com](https://uptimerobot.com).
2. Click **Add New Monitor**.
3. **Monitor Type:** `HTTP(s)`
4. **Friendly Name:** `BrandGuard Backend`
5. **URL (or IP):** `https://your-backend.onrender.com/healthz`
6. **Monitoring Interval:** `5 minutes`
7. Click **Create Monitor**.

### Option B: cron-job.org (Free - 1-minute intervals)
1. Sign up at [cron-job.org](https://cron-job.org).
2. Click **Create Cronjob**.
3. **Title:** `BrandGuard Keep-Alive`
4. **URL:** `https://your-backend.onrender.com/healthz`
5. **Schedule:** `Every 10 minutes`
6. Click **Create**.

---

## 3. Endpoints Reference

| Endpoint | Probe Type | Purpose | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET /healthz` | **Liveness** | Ultra-lightweight `SELECT 1` DB probe for load balancers & keep-alive pings. Returns `200` or `503`. | **No** |
| `GET /readyz` | **Readiness** | Deep check of DB, unapplied migrations, background thread pool runner, and disk storage. Returns `200` or `503`. | **No** |
| `GET /api/health/` | **Diagnostic** | Detailed JSON status directory with ruleset version, latency, and endpoints. | **No** |

