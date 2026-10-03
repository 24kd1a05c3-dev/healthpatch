# Production deployment and release checklist

Status (2026-10-01): hardened deployment candidate for research monitoring. **Not cleared for clinical patient use or emergency dispatch.** Local tests do not establish clinical safety, regulatory approval, reliable hardware acquisition or third-party delivery.

Local verification: 59 backend tests and 9 frontend tests pass; lint, typecheck and production build pass. Live API/MongoDB checks include persisted recovery after an injected failure, patient isolation, real dataset replay, phone persistence, refresh rotation, alerts/acknowledgment/CSV and logout revocation. Production dependency scans report no known advisories as of this date. The hashed dependency set resolves for Linux x86_64/Python 3.12. Two upstream test deprecation warnings remain. Docker/TLS and real provider delivery are not verified here.

## Implemented controls

- Production startup requires a private 32+ character JWT secret, authenticated TLS MongoDB, explicit HTTPS CORS origins, restricted hostnames, TLS SMTP, HTTPS password-reset URL and a shared MongoDB rate limiter. Public API documentation is disabled in production.
- Sessions are server-revocable with rotating HttpOnly/Secure/SameSite cookies. Web Locks serialize browser cookie mutations on supported secure-context browsers; bearer tokens are not stored in browser storage. Session JWTs must contain expiry, subject and session ID.
- Request/audit correlation IDs, structured request metadata, no response caching, safe error responses, restricted proxy trust and security headers. Query-string access logs are disabled because current WebSocket credentials are in the handshake URL. Do not enable URL/query logging in a CDN, proxy or monitoring agent.
- Normalized telemetry stores its pending derivation in the same MongoDB document. A leased worker retries with bounded exponential backoff, including after a restart. Ten failed attempts move a record to the failed queue. Duplicate telemetry and alert keys remain unique; older telemetry cannot replace a newer twin. `/ops/status` and `/ops/telemetry/{record_id}/retry` are admin-only.
- Physical measurement submissions from a paired device also enter the normalized pipeline, with timezone/clock validation. This is authenticated application ingestion, **not cryptographic device attestation**. Physical hardware has not been tested.
- Production BIDMC replay verifies the installed record 01 against the committed SHA-256 manifest. Fingerprints attest to the reviewed local copy, not a cryptographically signed publisher release. Irregular sample cadence is rejected. Missing measured values remain missing. Dataset attribution and license must accompany deployments.
- Hashed backend dependency lockfile, production frontend lockfile, lint/typecheck/test/build/audit CI and container-build jobs. CI has been authored but has not run remotely in this workspace.

## Deploy on a Linux Docker host

Docker is not installed on the current machine. Container startup, Caddy certificate provisioning, browser cookie behavior under HTTPS and proxy forwarding still require a staging test. Do not open the local Vite server or MongoDB to the Internet.

Configure DNS for your real domain and ensure ports 80/443 reach the Docker host. Use a private authenticated MongoDB service with TLS, majority write concern, least-privilege application credentials and encrypted backups. Install a reviewed Docker/Compose version on the deployment host. The API uses one worker; producer state and WebSocket fan-out remain process-local.

From the project root in PowerShell:

```powershell
Set-Location D:\Documents\healthpatch
# Only on first setup; do not replace an existing deployment configuration.
Copy-Item deploy\.env.example deploy\.env
```

Edit `deploy/.env` locally or inject these values from your secret manager. Set the real domain, CORS origin, allowed hosts, MongoDB URI, JWT secret, SMTP sender/credentials and HTTPS reset URL. Do not put credentials in chat, commits or screenshots. Example credentials intentionally do not pass production validation.

```powershell
docker compose --env-file deploy/.env -f deploy/compose.yaml config --quiet
docker compose --env-file deploy/.env -f deploy/compose.yaml build
docker compose --env-file deploy/.env -f deploy/compose.yaml up -d
docker compose --env-file deploy/.env -f deploy/compose.yaml ps
```

The web image serves built assets with Caddy, strips `/api` before forwarding to the private API, and supports WebSocket upgrades. Only 80/443 are published; MongoDB is external and must not have an unrestricted public firewall rule. The API is non-root, read-only, has dropped capabilities and mounts datasets read-only. Caddy certificate state persists in named volumes. The private subnet is `172.30.91.0/24`; change the subnet, fixed proxy address and `FORWARDED_ALLOW_IPS` together if it conflicts with your host network. Never use wildcard proxy trust.

Caddy references: [automatic HTTPS](https://caddyserver.com/docs/automatic-https), [separate SPA/API routes](https://caddyserver.com/docs/caddyfile/patterns).

## Automated SMS and voice

The implemented provider is Twilio. It remains disabled locally and in the example deployment. No external call/SMS was sent during implementation or tests. Unit tests mock provider calls; signed callbacks are tested with test-only credentials. Real delivery has not been validated.

Configure these environment values through your secret manager:

```text
NOTIFICATIONS_ENABLED=true
TWILIO_ACCOUNT_SID=<your account SID>
TWILIO_AUTH_TOKEN=<private auth token>
TWILIO_FROM_NUMBER=<registered E.164 sender>
TWILIO_VERIFY_SERVICE_SID=<Verify service SID>
NOTIFICATION_PUBLIC_BASE=https://your-domain/api
```

Then use Settings to verify the saved primary phone via SMS or a verification call, and opt into SMS and voice independently. Changing the primary number clears verification and consent. Turning consent off prevents subsequent queued sends. Verification itself sends to the provider and may incur charges; do it only with an authorized test recipient during staging.

New unacknowledged **LIVE_DEVICE statistical review alerts only** are eligible, up to 15 minutes old. Replay/simulator alerts never dispatch. Consent and verified-number matching are checked at dispatch. Each recipient/channel is limited to one attempt per UTC hour, in addition to verification limits. Messages contain a generic review notice, not physiological readings, diagnoses or emergency instructions. Provider acceptance does not mean delivery. Signed callbacks record actual provider status; terminal statuses do not regress on older callbacks.

A send timeout or process interruption after potential provider acceptance is marked `unknown` and is **not automatically retried**, to avoid duplicate calls. Operators must reconcile ambiguous attempts with the provider. The delivery history is visible to its patient in Settings; admin queue counts appear in `/ops/status`. In-flight calls cannot be recalled merely by unchecking consent.

Before enablement, configure provider opt-out handling, country/sender registration, permitted destination countries, spending limits, monitoring and a consent/retention policy. Complete real verification/SMS/voice tests with approved recipients, including provider rejection, invalid signature, delivery failure, revocation and network timeout. Do not rely on this integration for emergency response.

Twilio references: [verification](https://www.twilio.com/docs/verify/api/verification), [signed webhooks](https://www.twilio.com/docs/usage/webhooks/webhooks-security), [voice status callbacks](https://www.twilio.com/docs/voice/api/call-resource).

## Operations and approval

Monitor `/health` for liveness and `/api/ready` for MongoDB/worker readiness. Readiness is not a delivery guarantee or a throughput benchmark. Alert on failed derivations, growing pending queues, ambiguous notifications, database errors, disk usage and elevated HTTP latency/error rates. Audit events include request IDs; do not log request bodies, passwords, OTPs, phone numbers or health values.

Raw normalized waveform documents expire after seven days, including queue metadata; second-level history, twins, alerts, contacts and audits do not yet have an automated lifecycle policy. Establish retention, deletion and legal holds before collecting real patient information. Preserve/reconcile pending work before expiration. Encrypt backups and prove restoration into an isolated environment. Record recovery point/time objectives and repeat restore drills. Never run a restore directly against the production database as a test.

Promote an immutable tested image, keep the prior image for rollback, and validate data/index compatibility before rollback. Startup creates indexes; review existing duplicate records before deploying unique indexes. Old normalized rows without derivation metadata are not automatically backfilled. Restarted producer sessions must be started explicitly; the recovery worker recovers saved derivations, not the replay/simulation position.

Release remains blocked for real patient use pending staging/container/HTTPS verification, real SMTP and Twilio tests, clinical and independent security reviews, email verification/recovery review, hardware attestation, approved privacy/retention/backup procedures, browser accessibility/clinician journeys and measured load/reconnect tests. Horizontal scaling requires shared producer state and WebSocket routing. These are not satisfied by a successful build or a clean vulnerability scan.
