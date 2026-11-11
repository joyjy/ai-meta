---
name: loop-ledger
description: "Start or resume an authorized, recoverable Codex goal or Claude Code /goal backed by one loop-ledger file. Use for ll, /ll, a confirmed goal offer, or an exact loop-ledger-bound goal; also use automatically for authorized execution needing durable phase tracking, progress reporting, or recovery across turns."
---

# loop-ledger

Turn an authorized task into one recoverable host goal backed by `~/.ai/loop/<session>.ll`.

## Admission

- Select this skill automatically when an authorized task needs durable phase checkpoints or recovery across turns, including sustained implementation/verification loops. Respect an explicit no-loop preference. Short answers, discussion, and bounded single-step work do not need a ledger; steps or tests alone are insufficient.
- Skill selection does not grant goal or side-effect authority. Check the active platform's goal-creation rules before compiling or dispatching. If explicit goal authorization is required and absent, explain that exact gate and request only permission to start a goal for the existing scope; never treat implicit selection or ordinary task authorization as that permission.
- Reuse an already authorized exact-bound goal. Preserve all scope, Git, deletion, remote-action, and delegation boundaries.

## Start

- Treat `/ll <task>`, an explicit user task-bearing invocation, or confirmation of the immediately preceding final-form offer to start a goal as authorization. Begin exactly: `先站起来活动一下身体，上个厕所喝点水；我开始 /loop。`
- Pause only when a missing choice changes scope, acceptance, destructive or remote action, data model, file layout, compatibility, responsibility, or dispatch target.
- Derive sparse Goal, Scope, Acceptance, and gate-required final-form fields. Do not display or reconfirm them without a blocker.
- Write `{"ff": <sparse final-form>}` to a temporary file; run `../../scripts/ll-compile <exact-path> --input <input.json>`; remove that exact file. Never handcraft the contract.
- Dispatch by host. Codex: pass the exact output of `../../scripts/ll-goal-objective <exact-path>` to the callable goal tool. Claude Code: the agent cannot run `/goal`, so print the exact output of `../../scripts/ll-goal-objective <exact-path> --host claude` and end the turn; the user pastes that line to start the run. Do not execute ledger work without an active goal. Any other host means `needs_human`, never an adapter fallback.
- An active `/goal` that names an exact ledger path binds that path. If the file does not exist, stop and tell the user; do not compile from the condition text.
- Never infer an active run from the newest file or create a global active pointer.

## Ordinary Turn

1. Recover the exact loop-ledger path from the active goal.
2. Run `../../scripts/ll-hot-block <exact-path>` and use only its eight projected lines.
3. Execute the bounded active Focus.
4. Produce the `ll-turn` result named by the hot block's `Reply:` line, preserving material decisions as described below, and run `../../scripts/ll-turn compile-reply <exact-path> --input <result.json>`.
5. Continue from the returned block. Completed children return to Root; only Root may terminate, with evidence.

On `ll-turn@2`, list each Root `done_when` item newly satisfied this turn in `acceptance_met[]` as `{index, evidence}`, using the `[n]` number from `Local done`. Claim an item only when the evidence shows it. `ll-turn` refuses to close Root while any item is open; report `blocked` or `needs_human` when an item cannot be met.

In Claude Code, write the first line of the latest hot block in the reply before ending a turn, because the goal evaluator reads only the conversation. The goal ends when the ledger leaves `active`. At a human gate, end the reply with the `--host claude` line so the user can restart the goal after deciding. See `references/runtime-control.md` for the `/goal` mechanics.

Send a concise progress update at each major phase transition, material finding, or blocker: verified progress, remaining work, any blocker, and next action. Keep platform-required update cadence during long phases; do not invent percentages or narrate routine tools. Progress reporting remains useful even while goal admission is pending; do not claim a ledger or goal has started before it has.

## Decision Trail

- On `ll-turn@2`, record a user decision that constrains remaining work (keeping or narrowing scope, choosing an approach, deferring an item) with `../../scripts/ll-turn human-decision <exact-path> --input <decision.json>` in the turn it is made. The `Decisions:` line then carries it across compaction. If that line shows `+N more in ledger`, read the hidden decisions from the ledger tail before acting on work they could constrain.
- At a meaningful agent choice, pivot, rejected approach, revert, or verification checkpoint, record what was chosen, why (including the evidence that triggered a change), and the observed result in the existing turn result's `summary`. Put resolvable evidence pointers in `evidence[]`; distinguish observed results from pending or inconclusive outcomes. Skip routine actions and do not invent a decision to fill a turn.
- Persist this through `ll-turn compile-reply` in the same exact ledger. Do not introduce a separate TSV, sidecar, event type, or duplicate entry when the existing reply already contains the decision. A correction appends a new reply identifying the earlier decision and corrected evidence; never rewrite the old account or let a narrative record substitute for an authorized state transition.
- In phase reports, surface the decision and reason only when they affect remaining work or what the user should review. At handoff, check this run's material decision records against their evidence pointers, disclose unresolved outcomes, and append corrections for unsupported claims. This bounded evidence check does not trigger a transcript audit or additional agent.

## Conditional References

- Read `../../docs/architecture/vertical-agent-ll.md` only when changing the contract, compiler, verifier, session format, or runtime adapter.
- Read `references/runtime-control.md` only for rejected compile/admission, missing or compacted recovery, human/safety gates, or non-ordinary corrections and transitions.
- Read `references/closeout.md` only for checkpoints, verification policy, feedback/friction disposition, final audit handoff/settlement, archive, or engineering-exit handoff.
- Do not load references for successful startup or ordinary turns. Helpers plus `../../scripts/verify-ll-contract` are authoritative.
