# Execution ledger — plan: ../docs/superpowers/plans/2026-11-05-anydesk-web-bridge.md

- User approved design and use of ti-it graphical session.
- Ruling: execute inline following existing approval; no extra execution-method approval needed under session autonomy instructions.
- Ruling: isolated new repository because parent is not a Git repository; no parent worktree can be created.
- Ruling: first delivery uses authenticated WebSocket JPEG frames over SSH instead of WebRTC, as permitted by design transport alternative. This avoids opening network ports and simplifies deployment; cost is lower frame rate/bandwidth efficiency.
- Ruling: host web service and adapter in one interactive process, eliminating IPC exposure; capture worker remains isolated to avoid blocking input watchdog.
- Pre-flight: task 2 consumes task 1 adapter; task 3 consumes task 2 endpoints. Signatures aligned. Exact origin includes tunnel port.
- Task 1: in progress.
- Task 1: policy tests RED→GREEN; interactive task confirmed session 1. PrintWindow produced an empty interior (native probe caught it after visual inspection); switched to WGC by exact HWND. Native validation still in progress.
- Task 2: 11 suite tests passed. Regression found aiohttp cancellation skipped input release when cleanup awaited the frame task first; synchronous release now precedes all awaits.
- Task 3: UI and one-off Windows task scripts implemented; testing underway. No external AnyDesk test ID supplied yet.
- Ruling: WGC dependency added after PrintWindow failed real content capture; exact HWND avoids ambiguous title matching and desktop fallback.

- Review: 5 Important findings, no Critical or deferred Minor findings. Fixed cached-frame timestamps, independent stale-frame watchdog, best-effort release/retry with guaranteed lease cleanup, removal of native-window ownership inference, and cooperative authenticated shutdown. Regressions observed RED→GREEN on Mac/Windows.
- Ruling: Disconnect always stops bridge capture/control and preserves native AnyDesk sessions; CLI/singleton HWND timing cannot prove ownership. Cost: users close remote connections through AnyDesk itself.
- Ruling: OS-specific native regressions run on Windows; Mac suite explicitly skips them. Native focus/capture still need actual GUI checks beyond mocks.
- Native validation: WGC captured the user-initiated remote Mac session; exact window screenshot inspected. Subsequent target reconnect displayed Device Offline. No claim of remote mouse/keyboard end-to-end success.
- Activation fix: scoped Windows input-queue attachment around explicit foreground activation; always detached. Live WS test confirmed armed=true, then explicitly released without sending remote keys/clicks.
- Deployment incident: one-time termination of the pre-shutdown-endpoint process tree also closed its AnyDesk child; user was informed and same user-selected destination re-requested. New cooperative stop/start was tested and preserved the native session.
- Deployment now uses pythonw to avoid leaving a console in the interactive session. UI includes explicit choice when multiple AnyDesk windows exist.
- Current external limitation: latest target response is Device Offline; user says macOS Accessibility is already enabled. Do not infer that permission is still missing.

- Static-frame regression: live 8-second stream stopped at 2.36s because WGC emits only changes. RED→GREEN fix refreshes the actual window capture session after 1s without a callback; cached timestamps remain unchanged. Live retest received 48 frames through 7.94s.
- Final verification: Windows suite 25/25; Mac suite 20 passed, 5 Windows-only skipped. Browser login/live canvas/logout/mobile layout passed with no JS exceptions. Listening address is 127.0.0.1:8765 only.
- Final verification: live activation armed=true, immediately released; no remote keys/clicks sent during that check. Cooperative server stop/start preserved the native AnyDesk window.
- Review declined native DPI/occlusion/lock/end-to-end guarantees: remain explicitly limited to checked scenarios; no whole-desktop fallback, no claim of complete remote-input validation.
- Task 1: implemented; live window capture and explicit activation verified. Full remote input awaits online target.
- Task 2: complete, authenticated transport and lifecycle regression suite green.
- Task 3: deployed locally on Windows with retained SSH tunnel and browser QA. End-to-end remote control remains pending target availability.
- No deferred Minor review findings. Changes retained on local feature branch; no remote repository or public publication.
