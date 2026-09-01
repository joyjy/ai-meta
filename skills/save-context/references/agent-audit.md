# Asynchronous independent agent audit

Use this reference for Codex `save-context` and explicit audit follow-up. The audit has two lanes: execution friction and prompt / final-form / loop-ledger / execution fidelity. It does not review implementation quality or gate engineering exit. `save-context` is the only automatic dispatch owner; engineering-exit only hands off an exact ledger path. When save is omitted, an explicit audit follow-up may dispatch instead.

## Dispatch

Dispatch the audit through the Rollerskate Codex Steward with the active `@kimi` Agent as the admitted worker; do not start a conversation-history subagent and do not wait for the Run.

When `save-context` immediately follows engineering-exit, include the handed-off exact ledger with `--ll` in the single save audit. Do not create separate engineering-exit and save-context audits for the same completed work. If an exact receipt already covers the current execution revision, inspect that receipt later instead of redispatching it.

```bash
~/.ai/scripts/save-context-audit-rs \
  dispatch \
  --thread-id <exact-thread-id> \
  --cwd <exact-project-cwd> \
  --route <abbr:route> \
  [--ll <exact-ll-path>]
```

The helper derives a bounded recovery packet from the exact rollout, copies only that packet and the optional loop-ledger contract into an isolated Git-backed audit workspace, fixes `agent-audit.yaml` plus `audit-summary.json` as the only result files, and submits a minimal `RunIntent@1`. The intent names the stable audit participant and isolated workspace reference but does not provide raw Agent IDs, workspace grants, network authority, step budget, depth, or a Steward override; Rollerskate's Owner compiler resolves and fixes those execution facts before the Codex Steward starts. The Steward delegates the bounded task to Kimi, while the worker contract forbids further delegation. The participant and dispatch contract revision participate in audit identity, so switching workers or result contracts never reuses an older receipt. The write grant is intentionally non-interactive and limited to the isolated workspace. The helper derives summary `candidate_ids` from the authoritative lane order in `agent-audit.yaml`; workers author only the plain-language summary fields. The helper does not duplicate raw rollout JSONL and returns immediately with `run_id`, `receipt_path`, `workspace`, `output_path`, and `summary_path`; repeated dispatch of the same rollout revision, route, participant, and contract returns the same receipt.

The audit workspace is local runtime state under `~/.ai/audits/save-context/<audit-id>/`. Kimi has write access only to that isolated workspace. The main agent remains the only writer for source-of-truth files and the only caller allowed to settle objective events.

If Rollerskate, Kimi, the exact rollout, or dispatch is unavailable, report `独立 agent 审计：skipped（<原因>）` and continue saving. Do not replace it with main-context self-reflection. A successful dispatch is reported as `pending（run <id>；<output-path>）`; do not poll in the current save-context turn.

## Collect And Settle

At a later `save-context` or explicit audit follow-up, run `save-context-audit-rs status --receipt <receipt-path>` exactly once. It returns a compact status without waiting or printing Run trace. `ready` always reports `needs_settlement: true` and `cleanup_ready: false`; current-contract receipts additionally return a validated plain-language `audit_summary`. A live Run remains pending. A terminal failure without valid output writes a compact `inspection.json` and reports `recoverable: false`, `needs_discard: true`, and `cleanup_ready: false`; later status calls reuse this local terminal evidence instead of querying the Run again. Read candidates only when status is `ready`, use `audit_summary` as the user-facing review card, then verify every candidate against its cited evidence before settlement. The summary is not a disposition or execution authorization. Legacy receipts without `summary_path` remain readable under their original contract.

- Treat execution-friction candidates and objective collector events as complementary; do not require one-to-one mapping.
- `promoted`: search the existing Open friction inbox first. Update a matching mechanism signature in place and increment recurrence by exactly one independent session/project occurrence; otherwise create a new local friction entry or preserve a user-confirmed follow-up final-form.
- Route project-only candidates to the owning project's backlog. Route first-occurrence engineering mistakes to `pitfall_watch`; promote only after independent recurrence.
- `resolved`: name the existing durable fix and verification anchor. `ignored`: state why the sequence was normal, non-recurring, or unavoidable. `deferred`: require a concrete missing fact and durable revisit trigger.
- Settle objective events with `agent-frictions settle` and the exact owner. Auditor-only candidates are settled through the save report and durable output; never fabricate event files.
- Correct a still-active final-form or loop-ledger contract before routing a reusable fidelity gap. Cross-project compiler/control defects go to global friction, project-only defects to the project task, and one-off source-prompt guidance to report-only unless the user chooses a durable preference.

Do not let a collected candidate disappear silently. Report `独立 agent 审计：frictions N；prompt/contract gaps N；promoted N / resolved N / ignored N / deferred N`. Pending audits remain named by exact run and output path; they do not block the current checkpoint.

Generate the exact candidate skeleton with `save-context-audit-rs settle --receipt <receipt-path> --template`, fill every disposition, then record it with `save-context-audit-rs settle --receipt <receipt-path> --input <settlement-json>`. Template mode is read-only and derives lane plus `audit_id` from `agent-audit.yaml`. The input uses schema `save-context.audit-settlement.v1` and must account for every candidate exactly once. Every item requires `lane`, `audit_id`, `disposition`, `destination`, and `reason`; `promoted`, `resolved`, and `deferred` also require a durable `durable_ref`. The helper writes `settlement.json`; subsequent status is `settled` with `cleanup_ready: true`. A ready result cannot become cleanup-ready without this complete marker. For a terminal failed Run with no valid output, explicitly write a `discarded` tombstone with `discard --receipt <receipt-path> --reason <reason>`; discard requires the matching terminal `inspection.json` and cannot trust a caller-supplied status.

When the receipt contains an exact `ll_path`, the same later `save-context` or explicit audit follow-up owns delayed ledger archive after settlement or discard. Re-read and verify that exact path; never select a latest or similar ledger. Archive `done` / `commit_ready` with no unresolved current-task feedback to `completed`; archive a terminal ledger with retained unabsorbed legacy feedback to `review`; keep `remote_write_ready`, `next_ff_ready`, `needs_human`, `blocked`, or `active` in place. A pending, ready-unsettled, failed-undiscarded, or source-mismatched audit never authorizes archive.

Audit workspaces persist until their result is settled/discarded, or an obsolete receipt is safely superseded. Do not auto-delete them during save-context. `prune --receipt <receipt-path>` accepts only those cleanup-ready tombstones, is dry-run by default, and lists exact removable paths plus the target archive path. After normal deletion authorization, `--yes` uses local `zstd` to package the fixed evidence whitelist into `~/.ai/audits/save-context/archived/YYYY-MM/<audit-id>.tar.zst`, writes a SHA-256 sidecar, verifies every member, and only then removes `workspace/` and `run.json`; failure preserves the original files. `receipt.json + settlement.json` remain as compact tombstones. Repeating an authorized prune verifies and reuses the same bundle.

When an old receipt was created by a superseded dispatch contract and has no valid output, use `save-context-audit-rs redispatch --receipt <old-receipt>` instead of replaying its raw Run request. The helper binds the frozen recovery packet plus its exact rollout anchor, route, participant and project cwd to the current `RunIntent@1` contract, creates a new audit identity, and records the predecessor on the successor receipt. The original rollout may already have expired, but the source workspace's immutable `recovery-packet.md` must exist. Only after the successor is `ready` or `settled`, mark the old receipt with `supersede --receipt <old> --successor-receipt <new> --reason <reason>`. Supersede is a source-owned, cleanup-ready tombstone: it requires matching source identity, preserves successor evidence in status, and does not reinterpret the old Run terminal result.

For historical cleanup, `save-context-audit-rs inventory` is always read-only. It lists every exact audit directory, byte count, cleanup paths, settlement eligibility, exclusion reason, and Rollerskate Run archive status. Inventory output is evidence for a later exact-path deletion confirmation; it is never deletion authorization and has no execute flag.
