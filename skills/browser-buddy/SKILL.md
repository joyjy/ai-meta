---
name: browser-buddy
description: Coordinate guarded browser collaboration in draft-fill, live-copilot, or distill-cli mode. Use to fill without submitting, guide while the user operates, or watch a live browser action and capture the interface or network requests it causes. Do not use for ordinary web research or deterministic project E2E.
---

# browser-buddy

Use browser UI only for work that requires rendered interaction, the user's established session, or browser-specific evidence. Prefer a service-specific connector, API, CLI, or plain HTTP when it can preserve the requested semantics. Route repeatable project regression to the project's Playwright or equivalent test entry rather than this skill.

## Modes

Select one mode from the user's requested division of labor. State it, then make the selected runtime's first target-binding attempt in the same turn. The mode becomes active after that attempt; when the exact target cannot be bound, report the failure and request the precise user positioning needed. A chat-only fallback is a separate user choice.

- **Draft Fill**: the agent fills an already-open form but never performs the final submit, publish, send, confirm, purchase, delete, or equivalent commit action. Read [references/draft-fill.md](references/draft-fill.md).
- **Live Copilot**: the user operates the page; the agent observes and generates current field content without clicking, typing, uploading, or submitting. Read [references/live-copilot.md](references/live-copilot.md).
- **Distill CLI**: watch a bounded user or agent action and capture the network or application interface it causes, then decide whether it can become a connector, CLI, browser-context helper, or repeatable browser test. Requests such as “观测/观摩我的操作并抓接口/请求” select this mode. Read [references/distill-cli.md](references/distill-cli.md).

If the user's request combines modes, preserve each mode's authority boundary and announce the transition. Do not silently switch from observing to editing or from drafting to submitting.

## Execution Runtime

For work in the user's real Chrome session, prefer Kimi WebBridge when its daemon and extension are healthy. Read its installed `kimi-webbridge` skill for call mechanics, then read [references/runtime-routing.md](references/runtime-routing.md) for session identity, action budget, single-writer handoff, escalation, and fallback. This preference does not override the connector, HTTP, or project-test routes below.

## Shared Contract

- Reuse an existing login state whenever it is still valid. A tool connection failure, stale tab/target, sandbox or Keychain access failure, or failed browser action does not by itself justify re-login. Start a login flow only when the site or the service's canonical auth-status check proves the session absent or invalid and the current task requires authentication.
- Login is human-only. When login is actually required, the agent may open the login page, then stops. It does not choose an account, click SSO/login, enter passwords or one-time codes, approve consent, or infer that saved credentials authorize login. Resume only after the user says login is complete.
- Honor the browser surface the user names. Otherwise use the most specific available browser skill or tool; this skill does not redefine Chrome, Browser Harness, CUA, CDP, selector, screenshot, or Playwright mechanics.
- Bind the exact browser, target/tab, source URL, permitted effects, stopping point, and completion oracle before acting. After Chrome, daemon, or browser-tool restart, discard the old target/session identity and rediscover it; never attach to a similar tab by guess.
- Treat typing sensitive data as transmission. Apply the active client's confirmation requirements at the moment of entry; a standing request to fill a form is not blanket permission to transmit unspecified sensitive data.
- Detect whether editing a field triggers autosave or another remote mutation. If it does, Draft Fill is not a no-write preview: disclose the effect and stop for authority or switch to Live Copilot.
- A model's `DONE`, a rendered success message, or an accepted request is not proof of the business outcome. Use the narrowest independent readback required by the task.
- Store long or traceable browser evidence in a task-specific temporary file. Report its exact path instead of regenerating it; retain it across turns only when registered in loaded context with purpose and cleanup condition. Remove agent-created temporary evidence at the authorized cleanup boundary.
- Stop bounded network capture and other task-owned observation at completion. Follow the selected executor's cleanup contract: WebBridge sessions or tabs close only when the user asks, borrowed tabs never close, and shared browser daemons remain running. Report retained runtime state rather than silently cleaning it up.

## Routing Boundaries

- Public content or a known URL readable over HTTP: use web fetch or HTTP first.
- GitLab, Feishu, GTD, storage, mail, calendars, and other products with a stable connector or CLI: use that owner entry for ordinary operations. When the user explicitly requests live observation or request capture, use the browser for that evidence and the owner entry for baseline or readback.
- Project UI regression, responsive checks, and repeatable golden flows: use project-native Playwright or equivalent automation.
- One-off autonomous navigation may use an available browser agent, but Draft Fill submission and login boundaries remain authoritative over its prompt or completion signal.

## Completion

Report the selected mode, target identity, actions or observations completed, unresolved ambiguities, evidence/readback, retained artifacts, and runtime cleanup state. For Draft Fill, explicitly say the final action remains for the user. For Distill CLI, distinguish a discovered request from a supported reusable interface.
