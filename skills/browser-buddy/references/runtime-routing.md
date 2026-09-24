# Browser Runtime Routing

Use this reference when selecting or handing off an executor for a browser-buddy task. Read the selected executor's own skill or documentation for command mechanics; this reference owns only the cross-runtime contract.

## Route Selection

- Existing login state or a user-owned Chrome page: use Kimi WebBridge by default.
- Public content that does not need the user's session: use web fetch or HTTP.
- A supported product connector or CLI: use that owner entry and reserve the browser for the residual UI step.
- Visual-only state, canvas, a cross-origin frame that cannot be opened directly, or a task where the user must see and steer the exact page: use CUA after WebBridge stops issuing commands to that tab.
- Deterministic project regression or an isolated debugging profile: use project Playwright or `playwright-cli`; do not expect the isolated `--user-data-dir` profile to share the user's login.
- Jev is eligible only for a task-owned tab, common DOM/ARIA controls, a reversible micro-goal expected to take at most five atomic actions, and no login, upload, authorization, final submission, canvas, cross-origin frame, popup, or multi-tab reasoning.

Do not switch executors merely because the first call failed. First classify the failure as daemon unavailable, extension unavailable, stale target, unsupported page primitive, synthetic input ignored, or uncertain mutation outcome.

## WebBridge Session Parameters

- Create one stable session name per task: `bb-<task-slug>-<short-nonce>`. Use lowercase ASCII and hyphens, keep it unchanged across sites and turns, and register it in loaded context when the task will resume later.
- Use a short human-readable `group_title` in the user's language on the first navigation.
- A Live Copilot request to guide or watch the user's operation authorizes read-only borrowing of the active target. Resolve its expected URL or site from task evidence, use the executor's active-tab binding, and take the first snapshot. If the active tab does not match the exact target, ask the user to foreground or share that page before one retry. Other workflows default to a new task-owned tab unless the user explicitly refers to the current/open/visible page.
- Bind and report whether the current tab is task-owned or borrowed. Never close a borrowed tab. Call `close_session` only when the user explicitly asks to close the task's tabs.
- Treat the WebBridge daemon as shared runtime. Starting it idempotently is recovery; stopping, restarting, upgrading, or uninstalling it requires the user's explicit request.

## Action Budget And Readback

- Take a semantic snapshot before choosing an element and prefer its current element reference over CSS or JavaScript.
- After any navigation, or after at most five successful page mutations, pause for a new snapshot and task-relevant readback before continuing. Reads and screenshots do not consume this mutation budget.
- A successful tool envelope proves command transport, not page effect. Verify the expected rendered or application state separately.
- Never automatically repeat an externally meaningful mutation. If the command may have taken effect but readback is unclear, stop with an uncertain outcome.

## Click Escalation

1. Re-snapshot when the element reference is stale or the page changed.
2. Use semantic `click` or `fill` once and read back the expected state.
3. If a low-risk navigation or local UI action is proven to have had no effect, one CDP trusted-input attempt is allowed within the same WebBridge session.
4. Do not escalate a submit, send, purchase, authorization, deletion, consent, toggle with remote effects, or other potentially mutating action. Report the uncertain or unsupported state instead.
5. If trusted input still fails, hand control to the user or CUA; do not loop through reconnections or alternate executors.

## Single-Writer Handoff

- One tab has one mutating owner at a time: WebBridge, CUA, Playwright, or Jev.
- Before handoff, stop issuing commands from the outgoing executor and preserve the current URL plus the last verified page state. Do not pass its session ID, target ID, selector, or element reference to the next executor.
- The incoming executor rediscovers and verifies the exact tab. Chrome, daemon, extension, or tool restart invalidates every previously recorded session and target identity.
- One bounded rediscovery is allowed after a stale-target error. A second loss of identity ends that route for the task; switch only when another executor can bind the exact target safely.

## Completion

Stop network capture after collecting required details, keep the shared daemon running, and report the WebBridge session name, tab ownership, last verified state, retained tab group, and whether another executor took ownership.
