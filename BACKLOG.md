# Drone Diagnostics Backlog

## Vision

Build a reliable tool for diagnosing an individual ArduPilot/MAVLink UAV and, later, monitoring configuration and health across a fleet. Start with a safe, useful local USB workflow; add history and fleet services only after the single-drone foundations are dependable.

## Current MVP status

The repository is at an early scaffold stage. `mavlink.connection.connect()` opens a pymavlink connection and waits for a heartbeat, but currently uses an unbounded wait and does not expose connection configuration or structured errors. `mavlink.parameters` implements single-parameter reads and parameter-list reads with timeouts; list completion is inferred from a quiet timeout, and parameter reads are not matched against a request sequence. The CLI connects to `/dev/ttyACM0`, downloads parameters, and writes a sorted JSON dictionary to `params_snapshot.json`.

Configuration, diagnostics, fleet, and storage modules currently contain no implementation. The `tests/` files are empty, and pytest currently collects no tests. Tasks below describe missing capabilities or explicit hardening of the partial MVP; they do not treat the existing parameter reads and JSON export as unstarted features.

## Priorities

- **P0** — foundation or safety/reliability blocker for the local MVP.
- **P1** — core single-drone MVP capability.
- **P2** — useful extension after the local MVP is dependable.
- **P3** — later fleet, analytics, API, and UI work.

Suggested labels: `feature`, `bug`, `refactor`, `tests`, `docs`, `mavlink`, `configuration`, `diagnostics`, `cli`, `storage`, `fleet`, `maintenance`, `api`, `ui`, `P0`, `P1`, `P2`, `P3`.

## Milestone 1 — MAVLink Core

Goal: make local connection and parameter operations configurable, bounded, testable, and safe to use.

### Bound and configure heartbeat connection

**Priority:** P0  
**Description:** Extend the existing serial connection helper with configurable device, baud rate, and heartbeat timeout. Handle connection failures with actionable domain errors and avoid printing from the library layer.

**Acceptance criteria**
- Callers can choose device, baud, and heartbeat timeout; defaults are documented.
- Missing heartbeat and serial/open errors terminate within a bounded time and identify the device and cause.
- Connection success exposes target system/component without library-level console output.
- Unit tests cover success, timeout, and open failure using a mocked pymavlink connection.

**Labels:** `feature`, `mavlink`, `P0`, `tests`  
**Depends on:** Existing `mavlink.connection.connect()`.

### Harden parameter reads and complete parameter-list downloads

**Priority:** P0  
**Description:** Keep the existing `get_param()` and `get_all_params()` APIs while making response matching, timeout behavior, and list completion explicit and reliable.

**Acceptance criteria**
- A single read returns only the requested parameter and has a documented timeout result/error contract.
- A list download uses `PARAM_VALUE` index/count information and a bounded overall deadline to detect completion and missing entries.
- Byte and string parameter IDs are normalized consistently; duplicate or out-of-order responses are handled.
- Tests cover timeout, unrelated messages/parameters, duplicates, and complete/incomplete lists.

**Labels:** `refactor`, `mavlink`, `P0`, `tests`  
**Depends on:** Bound and configure heartbeat connection.

### Add parameter writes with read-back verification

**Priority:** P1  
**Description:** Implement `set_param()` with `PARAM_SET`, type handling, a bounded acknowledgement/read-back flow, and clear failure reporting.

**Acceptance criteria**
- A caller can set a named parameter and receive the confirmed value.
- The implementation verifies the resulting `PARAM_VALUE` and reports mismatch or timeout clearly.
- Parameter type and encoding follow MAVLink requirements and are covered by tests.
- The CLI does not claim success before verification.

**Labels:** `feature`, `mavlink`, `configuration`, `P1`, `tests`  
**Depends on:** Harden parameter reads and complete parameter-list downloads.

### Add command/message request helpers and ACK handling

**Priority:** P1  
**Description:** Add reusable helpers for `MAV_CMD_REQUEST_MESSAGE`, `MAV_CMD_SET_MESSAGE_INTERVAL`, and `COMMAND_ACK`, with bounded waits and result mapping.

**Acceptance criteria**
- Requested message and message interval can be configured through typed helpers.
- `COMMAND_ACK` is matched to the requested command and accepted/in-progress/denied/unsupported outcomes are represented distinctly.
- Timeouts and unrelated ACKs are handled and tested.

**Labels:** `feature`, `mavlink`, `P1`, `tests`  
**Depends on:** Bound and configure heartbeat connection.

## Milestone 2 — Configuration Snapshots

Goal: save and load reproducible, identifiable snapshots while retaining a migration path from the current parameter-only JSON file.

### Define the DroneSnapshot model

**Priority:** P0  
**Description:** Add a versioned snapshot model containing parameter values, capture timestamp, and optional drone metadata such as UUID, serial number, MAVLink IDs, vehicle/platform, firmware, and source connection.

**Acceptance criteria**
- Snapshot schema has a version and validates required fields/types.
- Metadata fields can be absent when the vehicle does not provide them.
- Existing flat parameter JSON can be imported or a clear compatibility boundary is documented.
- Tests cover valid, invalid, and older-version input.

**Labels:** `feature`, `configuration`, `P0`, `tests`  
**Depends on:** Harden parameter reads and complete parameter-list downloads.

### Save and load snapshots as JSON

**Priority:** P0  
**Description:** Replace the CLI's ad hoc parameter dictionary export with reusable snapshot serialization and deserialization.

**Acceptance criteria**
- Snapshot JSON is stable, human-readable, sorted where appropriate, and written atomically.
- Loading validates schema/version and produces actionable errors for malformed files.
- The default output does not silently overwrite an existing snapshot.
- Tests cover round-trip fidelity and file errors.

**Labels:** `feature`, `configuration`, `P0`, `tests`  
**Depends on:** Define the DroneSnapshot model.

### Capture firmware and vehicle metadata

**Priority:** P1  
**Description:** Request/record `AUTOPILOT_VERSION` and available identification fields as snapshot metadata.

**Acceptance criteria**
- Firmware/vendor/autopilot and vehicle identity fields are recorded when supplied.
- Unsupported or unavailable metadata does not prevent a parameter snapshot.
- Units and raw MAVLink fields are documented and tested.

**Labels:** `feature`, `mavlink`, `configuration`, `P1`  
**Depends on:** Add command/message request helpers and ACK handling; Define the DroneSnapshot model.

## Milestone 3 — Configuration Diff & Golden Config

Goal: compare configurations in a reviewable way and support a trusted baseline.

### Compare two snapshots

**Priority:** P0  
**Description:** Implement a structured diff for added, removed, and changed parameters, with configurable numeric tolerance and severity classification.

**Acceptance criteria**
- Diff results identify parameter name, old/new value, and change kind.
- Numeric values support a configurable tolerance; non-numeric values compare deterministically.
- Results classify differences as `INFO`, `WARNING`, or `ERROR` through rules/configuration.
- Tests cover unchanged, changed, missing, added, tolerated, and severity cases.

**Labels:** `feature`, `configuration`, `P0`, `tests`  
**Depends on:** Define the DroneSnapshot model.

### Add parameter ignore lists and diff policy

**Priority:** P1  
**Description:** Allow users to exclude volatile or intentionally local parameters and configure severity policy without editing code.

**Acceptance criteria**
- Ignore patterns/list are loaded from a documented config format.
- Ignored parameters are visible as ignored in machine-readable output or summary counts.
- Invalid policy configuration fails with a useful message.
- Tests cover exact names, patterns, and policy precedence.

**Labels:** `feature`, `configuration`, `P1`, `docs`, `tests`  
**Depends on:** Compare two snapshots.

### Store and compare a golden configuration

**Priority:** P1  
**Description:** Add a named, versioned baseline workflow and compare a current snapshot against it.

**Acceptance criteria**
- A baseline can be created from a validated snapshot and loaded later.
- Baseline metadata identifies platform/firmware scope and creation time.
- Comparison uses the shared diff policy and reports incompatible scope clearly.
- Tests cover baseline round trip, scope mismatch, and drift output.

**Labels:** `feature`, `configuration`, `P1`, `tests`  
**Depends on:** Save and load snapshots as JSON; Add parameter ignore lists and diff policy.

## Milestone 4 — Live Diagnostics

Goal: collect core ArduPilot health and pre-arm signals with bounded waits and normalized units.

### Run pre-arm checks and collect STATUSTEXT

**Priority:** P1  
**Description:** Trigger `MAV_CMD_RUN_PREARM_CHECKS` where supported and collect associated `STATUSTEXT` messages into a structured pre-arm report.

**Acceptance criteria**
- Command ACK status and emitted text are captured with timestamps/severity.
- Unsupported command, timeout, and no-failure-text outcomes are distinct.
- Pre-arm findings map to `OK`, `WARNING`, or `ERROR` without losing original text.
- Tests cover accepted, denied, timeout, and multiple text messages.

**Labels:** `feature`, `diagnostics`, `mavlink`, `P1`, `tests`  
**Depends on:** Add command/message request helpers and ACK handling.

### Collect system, GPS, EKF, and battery state

**Priority:** P1  
**Description:** Add bounded collection and normalized models for `SYS_STATUS`, `GPS_RAW_INT`, `EKF_STATUS_REPORT`, and `BATTERY_STATUS`.

**Acceptance criteria**
- Each signal has documented units, validity checks, and stale/missing-data handling.
- Raw MAVLink values remain available for troubleshooting.
- Collection uses configurable message rates/timeouts and does not wait forever.
- Tests cover healthy, degraded, unavailable, and stale messages.

**Labels:** `feature`, `diagnostics`, `mavlink`, `P1`, `tests`  
**Depends on:** Add command/message request helpers and ACK handling.

### Collect RC, servo, vibration, and IMU state

**Priority:** P2  
**Description:** Add optional collection for `RC_CHANNELS`, `SERVO_OUTPUT_RAW`, `VIBRATION`, and `RAW_IMU`/`SCALED_IMU`.

**Acceptance criteria**
- Each message family has typed fields, units/scaling documentation, and missing-data handling.
- Firmware or vehicle differences do not cause a full diagnostic run to fail.
- Tests cover decoding/scaling and unavailable streams.

**Labels:** `feature`, `diagnostics`, `mavlink`, `P2`, `tests`  
**Depends on:** Add command/message request helpers and ACK handling.

## Milestone 5 — Diagnostic Framework

Goal: make checks composable and produce consistent individual and aggregate status.

### Define DiagnosticResult and DiagnosticCheck

**Priority:** P1  
**Description:** Introduce the `DiagnosticCheck.run(state) -> DiagnosticResult` contract and result fields for check name, status, message, details, and timestamp.

**Acceptance criteria**
- Status is one of `OK`, `WARNING`, `ERROR` and results are serializable.
- Checks receive an immutable or clearly scoped state snapshot.
- Exceptions and missing input have a documented conversion/reporting policy.
- Tests validate result serialization and check contract.

**Labels:** `feature`, `diagnostics`, `P1`, `tests`  
**Depends on:** Collect system, GPS, EKF, and battery state.

### Implement initial health and readiness rules

**Priority:** P1  
**Description:** Implement checks for pre-arm result, GPS fix, EKF flags, battery state, and stale telemetry; aggregate them into `READY`, `WARNING`, or `NOT_READY`.

**Acceptance criteria**
- Each rule has documented thresholds and missing-data behavior.
- Aggregate status is deterministic: any blocking error yields `NOT_READY`; warnings yield `WARNING`; otherwise `READY`.
- Rule thresholds can be configured without changing check logic.
- Tests cover boundary values and aggregation precedence.

**Labels:** `feature`, `diagnostics`, `P1`, `tests`  
**Depends on:** Define DiagnosticResult and DiagnosticCheck; Run pre-arm checks and collect STATUSTEXT.

## Milestone 6 — CLI

Goal: provide a predictable local workflow with machine-readable output.

### Build configurable command-line interface

**Priority:** P0  
**Description:** Replace the hard-coded script entry point with commands for `status`, `params`, `get`, `set`, `snapshot`, `diff`, `preflight`, and `diagnostics`, plus shared `--device`, `--baud`, and `--json` options.

**Acceptance criteria**
- Commands and options are discoverable in help; defaults are documented.
- Exit codes distinguish success, warning, not-ready/error, and usage/input errors.
- Human and JSON output are stable and contain no credentials.
- Unit tests exercise command parsing and mocked command behavior.

**Labels:** `feature`, `cli`, `P0`, `tests`  
**Depends on:** Bound and configure heartbeat connection; Save and load snapshots as JSON; Compare two snapshots.

### Add safe parameter-write confirmation

**Priority:** P1  
**Description:** Expose parameter writes in the CLI with verification and a deliberate confirmation path for changing flight-controller configuration.

**Acceptance criteria**
- `drone-tool set NAME VALUE` shows the verified resulting value.
- Invalid values, failed read-back, and timeout return nonzero status.
- Interactive confirmation or an explicit non-interactive confirmation option is documented.
- Tests cover confirmation, refusal, and verification failure.

**Labels:** `feature`, `cli`, `configuration`, `P1`, `tests`  
**Depends on:** Add parameter writes with read-back verification; Build configurable command-line interface.

## Milestone 7 — Persistence & History

Goal: move from files to a local queryable history before introducing a service backend.

### Add SQLite schema and migrations

**Priority:** P2  
**Description:** Create a versioned SQLite store for drone identities, snapshots, diagnostic runs/results, and timestamps.

**Acceptance criteria**
- Schema migrations create and upgrade the database reproducibly.
- Foreign keys and indexes support per-drone history queries.
- Database path is configurable and local by default.
- Tests cover fresh creation, upgrade, and integrity constraints.

**Labels:** `feature`, `storage`, `P2`, `tests`  
**Depends on:** Define the DroneSnapshot model; Define DiagnosticResult and DiagnosticCheck.

### Persist vibration and battery history

**Priority:** P2  
**Description:** Store timestamped vibration and battery observations with source and unit metadata for later trend analysis.

**Acceptance criteria**
- Observations can be queried by drone and time range.
- Missing sensors and firmware differences are represented explicitly.
- Retention/export behavior is documented and tested.

**Labels:** `feature`, `storage`, `diagnostics`, `P2`  
**Depends on:** Add SQLite schema and migrations; Collect system, GPS, EKF, and battery state; Collect RC, servo, vibration, and IMU state.

## Milestone 8 — Fleet Management

Goal: manage multiple identified vehicles and their health/configuration independently.

### Define Drone identity and fleet registry

**Priority:** P2  
**Description:** Add a `Drone` model and registry with application UUID, serial number, MAVLink system ID, platform model, and optional firmware metadata.

**Acceptance criteria**
- Application identity is stable even when MAVLink system IDs collide across separate links.
- Serial number and platform fields are optional and can be updated from verified metadata.
- Registry supports add/list/get/update with validation.
- Tests cover duplicate and incomplete identities.

**Labels:** `feature`, `fleet`, `P2`, `tests`  
**Depends on:** Add SQLite schema and migrations; Capture firmware and vehicle metadata.

### Introduce transport abstraction

**Priority:** P2  
**Description:** Define transport lifecycle and implement `SerialTransport`, `UDPTransport`, and `TCPTransport` behind a common interface.

**Acceptance criteria**
- MAVLink services depend on an interface rather than serial-specific setup.
- Serial, UDP, and TCP endpoints have validated configuration and bounded shutdown.
- Unit tests cover lifecycle and invalid endpoint settings.

**Labels:** `feature`, `fleet`, `mavlink`, `P2`, `tests`  
**Depends on:** Bound and configure heartbeat connection.

### Support concurrent MAVLink systems and fleet health summary

**Priority:** P3  
**Description:** Track multiple systems/sessions without mixing messages and summarize per-drone health and configuration drift.

**Acceptance criteria**
- Each message is routed to the correct connection and system identity.
- Fleet summary reports per-drone `READY`/`WARNING`/`NOT_READY`, last-seen time, and stale/offline state.
- Fleet config drift links to the relevant snapshot diff.
- Tests cover isolation, disconnects, and summary aggregation.

**Labels:** `feature`, `fleet`, `diagnostics`, `P3`, `tests`  
**Depends on:** Define Drone identity and fleet registry; Introduce transport abstraction; Implement initial health and readiness rules.

## Milestone 9 — Predictive Maintenance

Goal: identify worsening trends from trustworthy, sufficiently long-running local history.

### Analyze vibration trends

**Priority:** P3  
**Description:** Establish per-drone and per-platform vibration baselines and flag sustained changes in relevant axes/frequencies.

**Acceptance criteria**
- Trend output includes window, sample count, units, baseline, and confidence/quality caveats.
- Alerts require configurable minimum data and persistence across samples.
- Synthetic tests cover normal noise, sustained increase, and sparse data.

**Labels:** `feature`, `maintenance`, `P3`, `tests`  
**Depends on:** Persist vibration and battery history; Define Drone identity and fleet registry.

### Analyze battery and propulsion degradation

**Priority:** P3  
**Description:** Detect changes in battery health and, where telemetry exists, ESC/motor behavior; compare only compatible platforms and operating conditions.

**Acceptance criteria**
- Battery indicators include capacity/voltage/current context and avoid unsupported health claims.
- ESC/propulsion checks are omitted cleanly when telemetry is unavailable.
- Comparisons disclose cohort size and platform/firmware compatibility.
- Tests cover missing telemetry, operating-condition differences, and trend detection.

**Labels:** `feature`, `maintenance`, `P3`, `tests`  
**Depends on:** Persist vibration and battery history; Define Drone identity and fleet registry.

### Detect fleet outliers and worsening trends

**Priority:** P3  
**Description:** Compare same-model drones and detect persistent deviations from peer and individual historical baselines.

**Acceptance criteria**
- Cohorts exclude incompatible vehicle/firmware/sensor data.
- Outlier reports identify contributing measurements and minimum sample requirements.
- A worsening trend is distinguished from a single anomalous sample.
- Tests cover compatible/incompatible cohorts and trend persistence.

**Labels:** `feature`, `maintenance`, `fleet`, `P3`, `tests`  
**Depends on:** Analyze vibration trends; Analyze battery and propulsion degradation; Support concurrent MAVLink systems and fleet health summary.

## Milestone 10 — API & Dashboard

Goal: expose the stabilized fleet and diagnostic capabilities to integrations and operators.

### Add FastAPI read API

**Priority:** P3  
**Description:** Expose REST endpoints for drone listing, per-drone health, diagnostic history, snapshots, and configuration diffs.

**Acceptance criteria**
- API schemas are versioned and documented with OpenAPI.
- Responses use the same status and diff models as the CLI.
- Errors, pagination, and database access are bounded and tested.
- Authentication/deployment assumptions are documented before network exposure.

**Labels:** `feature`, `api`, `P3`, `tests`  
**Depends on:** Add SQLite schema and migrations; Support concurrent MAVLink systems and fleet health summary.

### Build fleet and single-drone dashboards with alerts

**Priority:** P3  
**Description:** Add a fleet overview, per-drone diagnostic/configuration views, and actionable health alerts on top of the API.

**Acceptance criteria**
- Fleet view shows health, online/stale status, and drill-down to a drone.
- Drone view shows latest diagnostics, configuration diff, and history.
- Alerts link to the rule/evidence that triggered them and support acknowledgement.
- UI states for empty, loading, stale, and API failure are covered.

**Labels:** `feature`, `ui`, `fleet`, `P3`  
**Depends on:** Add FastAPI read API.
