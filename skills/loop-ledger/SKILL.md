---
name: loop-ledger
description: "Start or resume an authorized, recoverable Codex goal backed by one loop-ledger file. Use when the user says ll, loop, /ll, or confirms a final-form offer to start a Codex goal, and for an exact loop-ledger-bound goal."
disable-model-invocation: true
---

# loop-ledger

Turn an authorized task into one recoverable Codex goal backed by `~/.ai/loop/<session>.ll`.

## Start

- Treat `/ll <task>`, `/loop <task>`, a task-bearing invocation, or confirmation of the immediately preceding final-form offer to start a Codex goal as authorization. Begin exactly: `先站起来活动一下身体，上个厕所喝点水；我开始 /loop。`
- Pause only when a missing choice changes scope, acceptance, destructive or remote action, data model, file layout, compatibility, responsibility, or dispatch target.
- Derive sparse Goal, Scope, Acceptance, and gate-required final-form fields. Do not display or reconfirm them without a blocker.
- Write `{"ff": <sparse final-form>}` to a temporary file; run `../../scripts/ll-compile <exact-path> --input <input.json>`; remove that exact file. Never handcraft the contract.
- Pass the exact output of `../../scripts/ll-goal-objective <exact-path>` to the callable Codex goal adapter. Only `codex_goal` is dispatchable; unavailable goal tools mean `needs_human`, never an adapter fallback.
- Never infer an active run from the newest file or create a global active pointer.

## Ordinary Turn

1. Recover the exact loop-ledger path from the active goal.
2. Run `../../scripts/ll-hot-block <exact-path>` and use only its eight projected lines.
3. Execute the bounded active Focus.
4. Produce the `ll-turn@1` result requested by the hot block and run `../../scripts/ll-turn compile-reply <exact-path> --input <result.json>`.
5. Continue from the returned block. Completed children return to Root; only Root may terminate, with evidence.

Send a concise update when a major phase starts or a finding changes the plan: outcome and next action, without routine tool narration or contract text.

## Conditional References

- Read `../../docs/architecture/vertical-agent-ll.md` only when changing the contract, compiler, verifier, session format, or runtime adapter.
- Read `references/runtime-control.md` only for rejected compile/admission, missing or compacted recovery, human/safety gates, or non-ordinary corrections and transitions.
- Read `references/closeout.md` only for checkpoints, verification policy, feedback/friction disposition, final audit handoff/settlement, archive, or engineering-exit handoff.
- Do not load references for successful startup or ordinary turns. Helpers plus `../../scripts/verify-ll-contract` are authoritative.
