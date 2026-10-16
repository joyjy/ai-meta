# Evidence Comparison Modes

Read only after `agent-assignment` selects a comparison mode. These modes authorize bounded local read-only analysis and comparison artifacts, not networking, source writes, Git/remote writes, comments, task creation, or other effects.

## Broad Source Evidence

Use when the user asks to inventory source, trace call chains, list implementations or gaps, analyze multiple repositories/modules, or otherwise build a broad evidence index. A question answerable from roughly one to three files and a few directed searches stays direct.

- Send the same immutable input packet to Rollerskate `@kimi` and `@pi-deepseek`. Bind each repository to an exact revision and read-only workspace; keep scope, acceptance, and output budget equal while giving each artifact a distinct identity. Neither side reads the other before both first-pass artifacts are fixed.
- Prefer canonical Run Output rather than reports written into a source checkout. If a provider must write files, use exact isolated workspaces; do not share a writable checkout or silently serialize conflicting writers.
- After both artifacts are fixed, run one bounded symmetric challenge. Each side reports only disputed claims, missing evidence, invalid inference, corrected source anchors, and confidence; it does not rewrite the whole report. If one route produces no usable artifact, retain the other and report that comparison was unavailable rather than blindly retrying.
- The main session consumes a compact receipt: agreements, unresolved disputes, source anchors, and the highest-risk claims to sample. It owns sampling, cross-repository synthesis, business judgment, and completion; it does not repeat the full scan merely to appear independent.

## Independent Codex And RS Output

When the user explicitly requests independent Codex and Rollerskate outputs, freeze the shared input and dispatch the asynchronous Run before starting the Codex-local output. Do not let either side read the other before both artifacts are fixed unless the user requested sequential review or continuation. A Run started only after Codex finishes is not a parallel independent comparison.

## LLM Council

Use only when the user explicitly asks to run a council/deliberation, or when building a council primitive is itself the task. The reference implementation is `~/Documents/reference/llm-council/backend/council.py` ([GitHub fallback](https://github.com/karpathy/llm-council/blob/master/backend/council.py) if absent); take only its three-stage orchestration, not its provider, Web UI, or conversation shell.

- Use real isolated agents: homogeneous cold-start agents produce initial answers from the same packet, cold-start reviewers rank anonymized answers, then a cold-start chairman synthesizes. In Codex, use `fork_turns=none` and self-contained packets. Default to three initial agents, one reviewer, and one chairman unless the request sets another bounded shape.
- Never simulate several roles in one agent and claim that a council ran. If isolation is unavailable, report the capability gap.
- Return a `CouncilResult` in the current conversation with participant count, anonymized review, and chairman conclusion. Persist JSON/Markdown evidence or trace only when the user requests it or a downstream recovery/audit contract requires it.
- Do not start `./start.sh`, a React/Vite UI, a long-lived local service, a network model, OpenRouter, or paid-provider route by default. Confirm only runner availability, prompt, rounds, and any requested artifact location.
