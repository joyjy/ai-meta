# loop-ledger-runtime-control-gates

Read this reference only after the main skill's compile or goal-admission fast path is rejected, or for recovery, human/safety gates, and non-ordinary state correction or transition. Do not load it before a successful compile, initial dispatch, or ordinary turn. The single session file remains the runtime source of truth.

## final-form-compilation

Write `{"ff": <authorized sparse final-form>}` plus optional `id`, `project_abbr`, `project_root`, `gitlab_flow`, and `authorization_source` metadata to a short temporary JSON file, then run `~/.ai/scripts/ll-compile <exact-path> --input <ff.json>`. When `id` is absent the compiler derives it from the final-form revision hash. Do not copy or hand-edit `base_ll_contract.json`; the compiler owns fixed authorization, knowledge, linttest, blocker, provenance, and call-user controls. It maps:

- goal -> target outcome and runtime objective;
- include/exclude scope -> required artifacts and out-of-scope boundaries;
- acceptance plus verification-loop stop conditions -> done_when and runtime stop conditions;
- checks -> commands, state checks, or substitute evidence;
- constraints -> allowed side effects, ask-before, and call-user conditions;
- blocking question -> `needs_human` before execution;
- retained verification artifacts -> required artifacts, substitute evidence, or appended evidence events.

Existing capability inventory maps into the loop-ledger target. Important done conditions must carry provenance such as existing script, runtime state, runtime integration, domain model, user feedback, fixture, test, or explicitly supported inference. Missing coverage is an acceptance gap.

Set the runtime adapter to `codex_goal`. For a displayed final-form, preserve its confirmed goal verbatim and bind authorization to that revision. For an explicit loop-ledger invocation with a task, compile sparse final-form fields internally from that exact request plus visible context and bind authorization source `user_request`; do not introduce a second confirmation boundary. The current loop-ledger workflow does not dispatch manual, Symphony, or GTD runtimes.

Before writing, the compiler binds new runs to `runtime_binding.hot_packet` protocol `ll-turn@1`, normalizes whitespace, removes exact duplicate scope / acceptance items, and preflights the complete eight-line packet against a 1200-character soft target and 1800-character hard limit. The budget includes prefixes and fixed protocol text; fields share one pool rather than receiving independent limits. A normal compile returns the total and per-field contributions with the output path. Use `ll-compile <exact-path> --input <ff.json> --preflight` for the same JSON report without creating the ledger. If the packet remains over the hard limit, revise the largest source contribution or fixed protocol text; never truncate or drop scope and acceptance to make it fit. Existing `800/1200` contracts remain readable and keep enforcing their embedded legacy budget; contracts without a packet policy remain readable but do not gain a bounded-budget claim.

The compiler initializes and verifies `~/.ai/loop/<session>.ll`; remove the temporary final-form input afterward. `ll-workitem` is a compatibility wrapper over the same compiler. Do not create a separate brief, state, trajectory, or evidence file for the run; append those records to the ledger block. Existing legacy sidecars may be read during migration but are not the new write target.

## Appended Events

Use a short JSON event file and `ll-ledger append <exact-path> --event-file <file>`. Supported event types are:

- `checkpoint`: checkpoint id, new status, and optional evidence;
- `evidence`: evidence payload without control-state mutation;
- `exit`: state, next action, and relevant remote-write fields;
- `feedback`: one validated feedback item;
- `contract_patch`: a rare explicit correction to scope, acceptance, authorization, or runtime binding;
- `focus_added`, `focus_activated`, `focus_completed`, and `focus_superseded`: the bounded focus queue;
- `reply_compiled`: a structured turn result and optional next focus;
- `hot_rejected`, `human_decision`, `root_amendment`, and `session_rebind`: Symphony session and human-control transitions.

Events are append-only. The verifier derives the effective contract by applying them in order. Use contract patches only after user corrections or evidence-backed gate changes; ordinary progress uses checkpoint/evidence/exit events.

## Goal Gate

The current loop-ledger adapter supports only Codex goals. Legacy contracts for other adapters may remain verifier-compatible, but loop-ledger does not dispatch them. A Codex goal requires:

- unchanged authorized scope and acceptance, from either the explicit loop-ledger request or confirmed final-form;
- no blocking question;
- effective exit state `active` with next action `continue`;
- goal authorization source `user_request` or `user_confirmation` and objective source `verified_contract`;
- a passing exact file;
- callable create/get/update goal tools.

Render the goal with `ll-goal-objective`; render each automatic turn with `ll-hot-block` and compile its result with `ll-turn`. The renderer deterministically projects the append-only events into one active focus while preserving Root as final completion authority. Recovery and state transitions verify the file and inspect relevant tail events. Goal liveness never overrides contract scope or completion authority.

If the bound Codex goal is paused or blocked and the callable goal tools do not expose a resume transition, do not call `create_goal` to replace it or keep retrying permission variants. Preserve the verified loop-ledger file as `needs_human`, tell the user to run `/goal resume` in the same task, and continue from the projected hot block only after the goal becomes active again. A resumed goal does not grant new scope or authorization.

## Recovery And Human Gates

Recover in this order: exact path already bound to the session/dispatch/WorkItem/handoff, explicit loop-ledger request, visible confirmed final-form, context final-form, then return to final-form. Never scan for newest.

On resume after compaction or a terminal-ready user confirmation:

1. render the current hot block;
2. verify the single file;
3. read the latest relevant appended events;
4. continue the same scope when the user did not change it.

Ask only when an unresolved decision or missing authority affects scope, destructive or remote action, acceptance, business judgment, validation cost, or execution risk. Reuse still-valid authorization for the exact action. A correction that changes goal, scope, acceptance, authorization, architecture, or continuation semantics creates a new final-form revision. A goal-bound loop-ledger cannot be structurally rebound through `human_decision`, `root_amendment`, or `contract_patch`; initialize a new loop-ledger and bind a new Codex goal. Legacy non-goal adapters may append a verified contract patch.

A loop-ledger whose runtime projection is already `completed` is terminal and cannot be amended or reopened. If the user requests another loop-ledger run after completion, compile that request as a new final-form, initialize a new loop-ledger, and bind a new Codex goal. An ordinary follow-up returns to the caller workflow unless the user or an applicable project contract selects controlled execution. Do not append ordinary feedback, `root_amendment`, or `contract_patch` events to make the completed run active again. `root_amendment` remains only for non-terminal legacy adapters without a bound goal and cannot carry structural fields.

For explicit focus transitions, hot rejection, human decisions, session rebinding, or a user-authorized Root amendment, use the corresponding `ll-turn` subcommand. `ll-workitem` only compiles a dispatch-ready WorkItem final-form; it does not own runtime transitions.
