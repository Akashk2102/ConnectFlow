# ConnectFlow Troubleshooting & Runbook

This guide covers real-world failure modes and operational triage steps for ConnectFlow.

---

## 1. Webhook Signature Verification Failures (HTTP 403)

### Symptom
Plivo logs display `HTTP 403 Forbidden: Invalid webhook cryptographic signature`.

### Root Causes & Fixes
1. **URL Mismatch**:
   - The provider signs the *exact* public URL it was configured to call (including protocol `https://` and port).
   - If using a reverse proxy (Nginx, AWS ALB, Cloudflare), ensure headers `X-Forwarded-Proto` and `Host` are forwarded so `request.url` matches the URL Plivo signed.
2. **Auth Token Mismatch**:
   - Verify that `PLIVO_AUTH_TOKEN` in `.env` matches your Plivo account's primary token.
3. **Local Testing Workaround**:
   - In local development or staging tests, pass header `X-Bypass-Signature: true` to bypass verification when `APP_ENV != "production"`.

---

## 2. API Rate Limiting Exceeded (HTTP 429)

### Symptom
Calls to `/api/v1/...` return:
```json
{
  "detail": "Rate limit exceeded: maximum 100 requests per 60s."
}
```

### Remediation
1. Inspect the `Retry-After` header in the HTTP response to know how many seconds to pause.
2. For high-volume enterprise clients, increase `requests_limit` in `app/core/rate_limiter.py` or configure tier-specific limits.

---

## 3. Webhook Retry Storms / Duplicate Processing

### Symptom
Telecom provider repeatedly calls `/api/v1/webhooks/inbound`.

### Solution
1. Ensure your webhook handler acknowledges within **3 to 5 seconds**.
2. ConnectFlow decouples processing: it stores the message, dispatches work to a `BackgroundTasks` queue, and immediately returns `HTTP 200 OK` in <50ms.
3. The built-in **Idempotency Guard** automatically detects repeated `MessageUUID` deliveries and returns:
   ```json
   {
     "status": "already_processed",
     "idempotent_skip": true
   }
   ```

---

## 4. Windows Event Loop (`asyncio`) Socket Pairing

### Symptom
Pytest or AsyncClient hangs indefinitely on Windows.

### Explanation & Fix
On Windows, Python's `asyncio` event loop creates an internal loopback socket pair (`socket.socketpair()`) to wake up its selector thread. If the environment blocks loopback sockets, the process freezes.
ConnectFlow includes `pytest.ini` with `asyncio_mode = auto` and `asyncio_default_fixture_loop_scope = function` to prevent event loop stalls.
