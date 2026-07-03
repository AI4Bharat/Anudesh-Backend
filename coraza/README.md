# OWASP Coraza WAF (Core Rule Set)

This directory wires an [OWASP Coraza](https://coraza.io/) Web Application
Firewall running the [OWASP Core Rule Set (CRS)](https://coreruleset.org/) in
front of the Django backend, using the CRS-maintained
[`coraza-crs:nginx`](https://github.com/coreruleset/coraza-crs-docker) image.

## Why this design (and not a compiled nginx module)

Unlike ModSecurity, Coraza (written in Go) has **no drop-in module for stock
nginx** — the `ngx_http_coraza_module` connector is experimental and would
require rebuilding our `nginx` image from source against libcoraza. Instead we
run the maintained CRS image as a **reverse-proxy sidecar**, which leaves our
existing `nginx` + `certbot` (Let's Encrypt) stack completely untouched.

## Request path

```
Before:  client ──TLS──► nginx:443 ──http──► web:8000
After:   client ──TLS──► nginx:443 ──http──► coraza:8080 ──http──► web:8000
                          (TLS + certbot)     (Coraza + OWASP CRS)   (gunicorn)
```

nginx keeps terminating TLS and managing Let's Encrypt. It then hands decrypted
HTTP to Coraza, which inspects the request against the CRS and forwards clean
traffic to the app. Static files served directly by nginx bypass the WAF (fine —
they need no inspection and it keeps WAF load down).

## Files

| File | Purpose |
|------|---------|
| `custom-rules.conf` | Site-specific rules + false-positive exclusions. Mounted at `/opt/coraza/rules.d/999-custom-rules.conf`, loaded **alongside** the bundled CRS. |
| `README.md` | This document. |

WAF behaviour is otherwise controlled via environment variables on the `coraza`
service in `docker-compose-prod.yml` / `docker-compose-dev.yml` (see that block).

## ⚠️ Enabling the WAF is a TWO-part change

Adding the `coraza` service to compose is **additive and non-breaking** — by
itself it does **not** route any traffic through the WAF. It just starts an idle
container. To actually put the WAF in the request path you must **repoint the
server-side vhost** (the `./vhosts/<domain>.conf` files live on the server, not
in this repo):

```nginx
location / {
    proxy_pass http://coraza:8080;              # was: http://web:8000
    proxy_set_header Host              $host;
    proxy_set_header X-Real-IP         $remote_addr;
    proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
# keep `location /static/ { ... }` pointing at nginx — it bypasses the WAF
```

Passing `X-Real-IP` / `X-Forwarded-For` lets CRS rules and audit logs see the
real client IP instead of nginx's internal address.

## Rollout (do not skip)

The service ships with `CORAZA_RULE_ENGINE=DetectionOnly` — the WAF **logs** what
it *would* block but blocks nothing. Follow this order:

1. **Deploy in DetectionOnly** and repoint the vhost. Watch the WAF logs:
   `docker compose logs -f coraza`
2. **Exercise real flows** (LLM/streaming endpoints, file uploads, admin) and
   collect false positives (rule IDs + paths) from the audit log.
3. **Tune** — add exclusions to `custom-rules.conf`, then
   `docker compose up -d --force-recreate coraza`.
4. **Enable blocking** — set `CORAZA_RULE_ENGINE: "On"` and recreate the
   container. Only then consider raising `PARANOIA` to `2`.

## Project-specific things to verify in DetectionOnly first

- **Streaming / SSE**: this backend streams LLM responses. Confirm the WAF proxy
  does not buffer or break chunked / server-sent-event responses before enabling
  blocking.
- **Uploads**: check `SecRequestBodyLimit` (see the example in
  `custom-rules.conf`) against your file-upload endpoints so large uploads aren't
  rejected.

## Key environment variables

| Var | Default here | Meaning |
|-----|--------------|---------|
| `BACKEND` | `web:8000` | Upstream app (`host:port`, no scheme). |
| `PORT` | `8080` | Port the WAF listens on. |
| `CORAZA_RULE_ENGINE` | `DetectionOnly` | `On` = block, `DetectionOnly` = log-only, `Off`. |
| `PARANOIA` | `1` | CRS detection paranoia (higher = stricter, more false positives). |
| `BLOCKING_PARANOIA` | `1` | Paranoia level that actually blocks. |
| `ANOMALY_INBOUND` / `ANOMALY_OUTBOUND` | `5` / `4` | Anomaly-score block thresholds. |
| `CORAZA_AUDIT_LOG` | `/dev/stdout` | Audit log destination (visible via `docker logs`). |

See the [image documentation](https://github.com/coreruleset/coraza-crs-docker)
for the full list.
