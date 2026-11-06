# AnyDesk Web Bridge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Control an existing AnyDesk connection from a local browser using TI-LOCAL as the bridge.
**Architecture:** A loopback HTTP service and a window agent run in the approved interactive Windows session. Window-only capture is delivered through authenticated WebSocket frames, with exclusive input ownership and fail-closed focus guards. Start with window capture feasibility before adding the browser surface.
**Tech Stack:** Python 3.12, aiohttp, Pillow, pywin32, Windows window capture APIs, plain HTML/CSS/JS. Prefer tunnel-compatible frames for the first delivery; WebRTC optimization is deferred because this workflow already requires an SSH tunnel and must not open firewall ports.
**Spec:** `docs/specs/2026-11-05-anydesk-web-bridge-design.md`, approved in conversation.

## Global Constraints

- Windows TI-LOCAL 10.0.2.141, interactive ti-it session explicitly approved.
- Only selected AnyDesk window capture; never desktop capture fallback.
- Do not change AnyDesk binary, license, authentication, RDP policy or firewall.
- Local-only access through SSH tunnel; separate application credential, no secrets in source.
- One controller; no arbitrary command execution, clipboard, file transfer or audio.
- Detect and report real states; remote acceptance is not implied by successful process launch.
- Existing workspace is not a Git repo: isolate new code in `anydesk-web-bridge/`, its own repository/branch. Parent design/plan remain local documents.

## Review Focus

1. Browser closes with held keys: release and owner lease cleanup (task 2).
2. Window moves/resizes or another app gets focus: reject stale coordinates/foreign targets (tasks 1/2).
3. Same-origin session theft through unauthenticated WebSocket or CSRF: origin, cookie and lease validation (task 2).
4. Slow browser/capture stall: bounded frames and input watchdog, no indefinitely held buttons (tasks 1/2).
5. Unknown AnyDesk session ownership: never kill unrelated process/session; expose truthful stop behavior (tasks 1/3).

## Task 1: Window agent and validation policy

Files: `bridge/policy.py`, `bridge/windows.py`, `tests/test_policy.py`, `scripts/probe_windows.py`, `requirements.txt`, `.gitignore`.
Interfaces: `validate_id(value)->str`, `validate_event(data)->dict`, `map_point(x,y,width,height)->tuple`; `WindowsAgent.status()->dict`, `frame()->bytes|None`, `connect(remote_id)->None`, `activate()->None`, `input(event)->None`, `release()->None`, `disconnect()->None`.

- [ ] Write policy tests for command injection, nonfinite/out-of-range coordinates, invalid event fields and supported keys; run unittest and confirm missing behavior.
- [ ] Implement strict parsing and mapping; verify tests pass.
- [ ] Write Windows integration probe that asserts selected process/session, nonempty window-only capture and image variation; run to record unavailable adapter before implementing.
- [ ] Implement adapter with PID/path identity, client-area capture, DPI awareness, bounded worker capture, focus/visibility/session guards and tracked input release; run probe in interactive task.
- [ ] Inspect captured artifact and verify no other windows are included. If PrintWindow cannot capture AnyDesk, use Windows Graphics Capture by exact verified window.
- [ ] Commit validated agent/policy. Capture and input are separate; no remote connection without user-supplied test target.

## Task 2: Authenticated service and lease

Files: `bridge/server.py`, `bridge/__main__.py`, `tests/test_server.py`.
Consumes: task 1 adapter. Produces: `create_app(agent, password, origin)->Application`; `/api/login`, `/api/status`, `/ws`, static browser assets.

- [ ] Add async integration tests using actual aiohttp server and fake OS boundary: unauthenticated requests, bad origin, login throttling, invalid IDs, exclusive controller, disconnect releases inputs, oversized and malformed messages, stale geometry.
- [ ] Run tests RED; implement cookie auth, CSRF/origin guard, bounded WS delivery and rate limits, monotonic lease expiry, input watchdog and shutdown cleanup.
- [ ] Run all tests GREEN; commit service.

## Task 3: Browser and deployment

Files: `web/index.html`, `web/app.js`, `web/style.css`, `scripts/start-windows.ps1`, `scripts/stop-windows.ps1`, `scripts/tunnel.sh`, `README.md`, `verification/`.
Consumes: task 2 API. Produces browser login/connect/view/control/disconnect workflow.

- [ ] Implement clear Portuguese UI with explicit focus activation, real transport states, keyboard/pointer mapping to current frame dimensions, pointer cancellation, blur cleanup and stale-frame prevention. Input confined to focused canvas.
- [ ] Run JavaScript syntax checks and browser checks against local fake OS boundary; check login and errors, no fabricated remote-success state.
- [ ] Deploy isolated dependencies and interactive task in Windows; server binds 127.0.0.1 only. Credential stored privately outside source.
- [ ] Open SSH tunnel, authenticate, fetch real frames and verify capture/focus guards. Test remote control only against supplied authorized target.
- [ ] Document exact start/stop, URL, capture transport limitations, active-session dependency and incomplete external tests.
- [ ] Run full suite and fresh whole-project code review; repair important findings with regressions, commit and report accurate result.
