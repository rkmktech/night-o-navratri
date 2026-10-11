# Published deployment smoke check

Run `pnpm test:deployment` for offline production-command and smoke-checker tests.
These tests never contact the deployment, launch real Streamlit, or sync assets.

After publishing, obtain the **actual published URL** from Replit's deployment
metadata (agents: read the deployment skill and call `getDeploymentInfo()`).
Do not substitute the workspace preview URL.

Opt in explicitly:

```sh
pnpm test:deployment:live --url https://YOUR-PUBLISHED-HOST
```

The command performs three bounded, unauthenticated GET requests:

- `/`: HTTP 200, HTML containing the Streamlit title.
- `/_stcore/health`: HTTP 200, plain-text `ok`.
- `/api/healthz`: HTTP 200, JSON `{"status":"ok"}`, proving this route is not
  being swallowed by the root Streamlit service.

It exits 0 only when all three pass; otherwise it exits 1 and reports each failed
route. Redirects (including access gates) fail. Default timeout is 30 seconds per
request; `--timeout` can override it up to 120 seconds. No automatic publishing,
retries, login, cookies, secret access, or ticket-data checks occur. Do not put
credentials or access tokens in `--url`; they are rejected.

A private or password-protected deployment cannot pass this **public-access**
check. The owner must decide whether to make it public; the checker deliberately
does not bypass access controls. A blocked check does not prove the services are
down, only that anonymous reachability is unverified.

## Latest live observation (2026-10-11)

Deployment metadata reported a successful autoscale build at
`https://NightONavrathri-app.replit.app`, with **private** visibility.
Unauthenticated requests to all three routes returned HTTP 307 to Replit's
access gate. Service health behind that gate remains unverified. No publishing
or visibility changes were performed.

The inspected production definitions keep Streamlit at `/` on port 8080 with
startup health `/_stcore/health`, and the API at `/api` on port 8083 with startup
health `/api/healthz`. `scripts/start-streamlit.sh` syncs guide assets before
launching Streamlit and forces port 8080. The live check complements, rather than
replaces, offline checks of that launch chain. An HTTP smoke check does not
exercise Streamlit's WebSocket session, dance inference, or ticket loading.
