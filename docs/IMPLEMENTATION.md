# Implementation audit and release status

Date: 2026-10-01. Scope: local workspace `D:\Documents\healthpatch` and the supplied production-grade brief. This is an implemented research prototype, **not completion of every requirement in that brief**. No Git metadata was present, so the change inventory below is descriptive rather than a Git diff.

## Repository audit

| Category | Findings and disposition |
| --- | --- |
| KEEP | React 19, TypeScript, Vite, Tailwind, Recharts, Lucide; FastAPI/Pydantic, MongoDB; existing assignment-based authorization and BIDMC adapter boundary. |
| REFACTOR | Registration state/validation, profile persistence, authentication sessions, replay ingestion, WebSocket cleanup, patient workspace and telemetry statistics. |
| REPLACE | Hardcoded dashboard/history/AI/alert screens with database-backed workspace; fabricated device pairing/profile/settings results with real API responses or explicit unavailable states. |
| ADD | Phone validation, persistent refresh sessions, normalized telemetry service, numerical scenario simulator, statistical twin, bounded CSV export, regression and live integration tests. |
| REMOVE | Active random physiological fallbacks, fabricated dashboard scores, fake emergency dispatch success, dead dashboard/history/insights/alert screens and inert header search. |
| SECURITY FIX | Public privilege escalation blocked, patient-scoped access checks preserved, emergency fan-out scoped, Argon2id hashing, memory-only access credentials, refresh rotation/revocation, WebSocket session validation, reset-token consumption, basic response headers. |
| PERFORMANCE FIX | Lazy screen bundles, bounded raw waveform buffers and chart decimation, bounded history/export reads, database indexes, WebSocket send timeouts, duplicate/reconnect cleanup. |
| UX FIX | Stable form components retain focus/caret; controlled fields persist across steps; India +91 default and international numbers; actual profile contacts; Signal Lab navigation; truthful sources and loading/error/empty states. |

Remaining legacy code includes the physical `health_measurements` pipeline, older analytics helpers and demo seed/generator files. They are not certified by the new normalized-stream tests. Some legacy APIs use unversioned routes. Do not infer production completeness from retained filenames or UI appearance.

## Implemented architecture

```text
Licensed BIDMC CSV --> Dataset adapter ---+
                                        |
Research scenario simulator ------------+--> Pydantic normalized packet
                                               |
                                               v
                                      MongoDB raw telemetry
                                               |
                         +---------------------+------------------+
                         v                                        v
                 Patient WebSocket                    Per-stream 1-second samples
                         |                                        |
                         v                                        v
                  Signal Lab                            Rolling statistical twin
                                                                  |
                                                     Sustained-deviation alert
                                                                  |
                                        Scoped REST/workspace + alert WebSocket
                                                                  |
                                           Patient/assigned clinician dashboard
                                                                  |
                                             Acknowledge / CSV export / audit

Legacy physical-device API --> health_measurements (not yet unified)
```

The waveform event is published after raw persistence. Derived statistics are then calculated per new original second. Failed WebSocket delivery does not roll back raw telemetry. This is not a transactional outbox: a failure after raw insertion can leave derivation incomplete, and a durable recovery worker is a release blocker.

## Authentication and authorization

- New passwords: Argon2id; legacy bcrypt hashes remain verifiable. Password length 12-128 characters. No automatic legacy rehash yet.
- Access JWT: 10-minute default, held in JavaScript memory, includes a database session ID. Server requests check revocation/expiry.
- Refresh credential: random opaque value, only a SHA-256 fingerprint persisted. HttpOnly, SameSite Strict cookie, Secure in the configured production mode, 7-day session expiry.
- Refresh rotates atomically; reuse of a spent credential revokes that session. Browser refresh is single-flight within one tab, not coordinated across tabs yet.
- Logout revokes the session; network failure now reports failure rather than pretending revocation succeeded. Reset consumes a single-use hashed token and revokes user sessions.
- Password-reset email returns unavailable when SMTP is not configured. Email verification, MFA and production delivery monitoring are not implemented.
- Roles remain `patient`, `doctor`, `caregiver`, `admin`. Public signup creates patients only. Assigned staff and administrators can access permitted patient resources. The requested de-identified researcher role is not implemented.
- Auth mutations enforce allowed Origin when present. Rate limiting is process-local. WebSocket tokens still use a query parameter: suppress query-string logging at proxies as well as Uvicorn.
- WebSocket sessions are revalidated every 15 seconds even with ongoing client pings; this is bounded revocation latency, not instantaneous disconnect.

## Database schema and indexes

| Collection | Key fields and purpose |
| --- | --- |
| users | Mongo ID, unique normalized email, password hash, role, contact/profile fields, assignments, enrollment timestamp |
| sessions | unique sid, user_id, unique refresh_hash, spent hashes, revoked, expiry TTL |
| password_resets | unique token_hash, email, expiry TTL |
| devices | unique device_id, owner, firmware/status fields; existing device API |
| normalized_telemetry | user/device/stream, sequence, source, emission timestamp, vitals, optional waveforms, provenance; unique user+stream+sequence; 7-day raw TTL |
| telemetry_seconds | unique user+stream+original second, source, record, timestamp, vitals, optional quality |
| patient_twins | unique user+stream, source/record, latest vitals, statistical features, quality, update timestamp |
| digital_twins | existing replay device-state projection; separate from patient statistical state |
| alerts | patient, incident_key, source, reasons, severity, acknowledgment; unique incident_key when present |
| audit_events | actor, action, resource, result, timestamp; actor/time index |
| emergency_events | persisted review requests, not dispatched telephone calls |
| health_measurements | legacy physical measurement path; separate from normalized replay/simulator |

MongoDB indexes are created on startup. No destructive migration was applied. Back up and inspect existing duplicates before deploying new unique indexes. Raw TTL is active; second-level data, audit and account retention/deletion policies are still required. Minute/hour/day rollups and schema migration versioning are not implemented.

## API map

OpenAPI at `/docs` is authoritative for full schemas.

| Method | Route | Behavior |
| --- | --- | --- |
| POST | /auth/register, /auth/login | Patient signup or authenticate; create session |
| POST | /auth/refresh, /auth/logout | Rotate or revoke session |
| POST | /auth/forgot-password, /auth/reset-password | SMTP-dependent reset workflow |
| GET/PUT | /users/me | Read/update validated profile |
| GET | /users/patients | Authorized patient list |
| POST | /users/ | Admin-created account |
| POST/DELETE | /users/{staff_id}/patients[/patient_id] | Existing admin assignment API |
| GET/POST | /devices/ | List/register devices under existing authorization |
| GET/POST | /devices/{id}, /devices/{id}/pair | Authorized lookup/pair |
| GET | /replay/datasets, /replay/status | Installed records / current replay |
| POST | /replay/start, pause, resume, stop, restart, seek, speed | Dataset controls |
| GET/POST | /api/v1/simulation | Scenarios/status and validated control actions |
| GET | /api/v1/workspace?user_id=... | Authorized twin, latest 300 samples, latest 50 alerts |
| GET | /api/v1/reports/telemetry.csv?user_id=... | Up to 10,000 samples from latest stream |
| GET/POST | /alerts/, /alerts/{id}/acknowledge | Existing alert query / persisted acknowledgment |
| POST | /emergency/ | Persist a scoped review request; no dispatch |
| WebSocket | /ws/{user_id}?token=... | Authenticated patient-scoped events |
| GET | /health, /ready | Liveness / database readiness |

There is no general-purpose normalized physical-ingestion endpoint yet. Internal dataset and simulator producers share `ingest_normalized`; do not advertise this as a completed hardware integration.

## Twin, simulator and alert algorithms

Each source run gets a stream ID. Statistics never combine one recording with another or with simulated data. Up to 300 original-second samples feed current/min/max/mean, trend, recent mean and baseline. With at least 60 valid samples, the baseline excludes the last 30 valid samples. The recent mean's difference from that baseline divided by baseline population standard deviation is an explainable z-score. A near-zero baseline standard deviation does not generate a z-score.

Alerts require |z| >= 3, 30 consecutive original seconds, available values for the contributing metric throughout that recent window, and no supplied low-quality value below 0.7 in that window. Unknown quality is explicitly unknown, not fabricated confidence. This is a research heuristic, not a clinical threshold or validated risk prediction. One incident is inserted per stream/5-minute bucket. Acknowledgment is recorded and audited; resolution, escalation, reminders and full episode state transitions are not implemented.

Simulator targets cover resting, walking, running, sleeping, stress, fever, tachycardia, bradycardia, low SpO2 and recovery. Each second moves 3.5% toward the selected target with small correlated deterministic sinusoidal noise. Start/pause/resume/stop, 1x/2x/5x, disconnect/reconnect and signal quality controls are implemented, with modeled battery drain. Runs stop at 3,600 simulated seconds. It does not generate ECG/PPG waveforms, CUSTOM inputs, HRV, steps, posture or clinical physiology. The real-recording Signal Lab is the waveform inspection surface.

## Change inventory

New frontend files: `components/FormField.tsx`, `components/PhoneInput.tsx`, `screens/PatientWorkspace.tsx`, `screens/SimulatorScreen.tsx`, `screens/PasswordResetScreen.tsx`, `screens/RegisterScreen.test.tsx`, `context/HealthDataContext.test.tsx`.

New backend files: `app/models/contact.py`, `app/services/session_service.py`, `app/services/telemetry_service.py`, `app/services/simulation_service.py`, `app/routers/workspace.py`, `app/routers/simulation.py`, `tests/test_registration_and_statistics.py`, `tests/run_live_checks.py`, `requirements-dev.txt`.

Principal modified files: `App.tsx`; auth/client/WebSocket API modules; Auth/HealthData contexts; registration, profile, doctor, settings, pairing, monitoring and Signal Lab screens; Sidebar, TopBar, EmergencyButton, DataSourcePanel, DigitalTwinPanel; backend config/security/database/main; user/telemetry models; auth/users/emergency/WebSocket/replay routers; BIDMC adapter/replay service/WebSocket manager; requirements, tests, package manifests and dataset docs.

Removed obsolete screens: `DashboardScreen.tsx`, `AIInsightsScreen.tsx`, `AlertCenterScreen.tsx`, `HealthHistoryScreen.tsx`. Added README, environment examples, ignore rules and this audit.

## Verification evidence

- Frontend TypeScript check and production Vite build passed. Screen code is lazy loaded. Main JS approximately 218 KB, chart chunk 351 KB, phone validation chunk 195 KB before gzip. Device image is still approximately 1.75 MB and can be optimized separately.
- Nine frontend regression tests passed: registration typing/focus/step persistence/payload/invalid phone; simulator packet updates/deduplication/patient isolation; missing waveform positions; server-backed simulator settings; refresh coordination and honest notification settings.
- The expanded backend suite covers authorization, contacts, Argon2, dataset fingerprints/cadence, statistics, simulator behavior, production configuration, correlation IDs, fail-closed rate limits, recovery workers, consent and signed telephone callbacks. See `docs/PRODUCTION.md` for the final release verification and infrastructure boundaries. The API and tests use `backend/.venv`.
- Live API/MongoDB checks passed: signup data persistence, international phones, HttpOnly cookie, refresh rotation, denied patient access, actual BIDMC replay, source metadata, twin derivation, duplicate rejection, sustained alert, acknowledgment audit, CSV, simulation controls and logout revocation. The script cleans its isolated patient data.
- Desktop browser registration typing and mid-word caret editing verified. Mobile registration checked at 390 x 844 with no horizontal overflow, and entered data survived back navigation. No browser console errors appeared during these registration checks. Browser verification is complementary to tests, not a load test.
- Browser sign-in, actual BIDMC five-channel streaming at 5x, pause/stop, mobile Signal Lab layout, simulator scenario changes, digital-twin source labeling, generated observations and acknowledgment were exercised using a disposable local QA account. The API test also checks UTC-aware timestamps. No physical telephone call was attempted.
- No lint toolchain, clinical validation, formal accessibility audit, Docker validation, backup restore exercise, multi-tab expiry soak or 10,000-patient load test has passed or is claimed.

## Production release blockers

1. Production infrastructure: HTTPS, same-site cookie/proxy verification, private database credentials/TLS, encrypted backups, retention/deletion policy and recovery drills. Production configuration now rejects short/default/placeholder JWT secrets and requires SMTP configuration; deployment and secret rotation remain operator responsibilities.
2. Identity: verified email, password-policy/account recovery review and independent security review. Shared MongoDB rate limits, Web Locks refresh coordination and correlated/redacted request logs are implemented; secure-context browser soak testing and provider verification remain necessary.
3. Telemetry reliability: pending derivation, leased retries, failed-record operations and older-twin guards are implemented. Producer synchronization, bounded session registries, resumable producer jobs, distributed WebSocket delivery and measured throughput remain. Use one API worker.
4. Product scope: researcher de-identification, clinician notes, admin UI, complete device lifecycle, physical hardware integration, advanced simulator metrics, alert resolution/escalation, historical windows/PDF reports and fully paginated APIs.
5. Data integrity: record 01 fingerprint/license manifest and cadence validation are implemented, along with subtraction of processing time from replay intervals. Other records, per-record channel discovery, longer-term aggregation and measured acquisition timing remain unverified.
6. Telephone integration: Twilio SMS/voice, number verification, per-channel opt-in, live-only dispatch, signed callbacks and delivery history are implemented and mock-tested. Provider credentials, public callbacks, country/sender approvals, opt-out configuration and real authorized-recipient tests remain required. No calls or messages were sent.
7. Quality gates: lint, typecheck/build, frontend/backend tests, dependency scans, recovery-failure integration tests and CI/container jobs are implemented. Docker/staging execution, clinician journeys, broader offline/load/concurrency tests, independent security review and accessibility/rendering checks remain.

Do not use this system to diagnose, determine care, or rely on emergency notifications. These gaps are not hidden behind placeholder success states.
