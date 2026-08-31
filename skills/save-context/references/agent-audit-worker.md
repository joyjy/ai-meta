# Independent agent audit worker

Audit the supplied Codex run in two separate lanes. This is read-only analysis: do not edit source files, settle events, or create artifacts other than the requested `agent-audit.yaml` and `audit-summary.json` results.

## Evidence

Use `recovery-packet.md` as the only rollout evidence surface and read `effective-ll.md` when present. Omit any candidate when this bounded evidence does not prove the initial route, obstacle, recovery, user decision, generated contract, or impact. Do not infer missing transcript content or quote secrets.

## Execution friction

Find evidence-backed sequences where an initial tool, search scope, permission route, skill, command, or output was ineffective and a later fallback, retry, narrower query, parameter change, escalation, or regeneration imposed avoidable cost. Include quiet self-corrections. Exclude ordinary requirement changes, planned iteration, implementation-quality findings, task abort alone, repeated successful edits alone, and one-off programming mistakes without a reusable mechanism. Normalize signatures by mechanism; recurrence is `likely` only with independent repetition evidence.

## Prompt and contract fidelity

Compare visible user intent and decisions with displayed final-form, the effective loop-ledger contract when present, execution, and later correction. Report only consequential omissions, distortions, unsafe defaults, or execution drift. A later new requirement is not proof that the original prompt was bad. Choose the narrow fix target: source prompt, final-form compiler, loop-ledger contract, executor, or none.

## Output

Write only the following two output artifacts. Use an empty list when a lane has no evidence-backed candidate.

Write this schema to `agent-audit.yaml`:

```yaml
schema: agent.audit.v1
thread_id: <exact id>
execution_friction:
  - audit_id: <stable short id>
    evidence: [<exact rollout line, timestamp, tool call, or artifact path>]
    intent: <intended action>
    signature: <stable mechanism signature>
    initial_route: <first route>
    obstacle: <observed failure or avoidable cost>
    fallback: <successful recovery>
    impact: <retry, excess output, interruption, or degraded result>
    recurrence: likely | unclear | unlikely
    destination: global_friction | project_task | pitfall_watch | ignore
    suggested_disposition: promoted | resolved | ignored | deferred
    reason: <one sentence>
prompt_contract_gaps:
  - audit_id: <stable short id>
    evidence:
      request: <exact evidence>
      generated_artifact: <exact evidence>
      correction_or_impact: <exact evidence>
    gap_type: source_prompt | ff_compilation | ll_contract | execution_drift
    intended_outcome: <evidence-backed intent>
    generated_interpretation: <committed interpretation>
    gap: <material gap>
    downstream_impact: <consequence>
    current_task_status: corrected | still_affects_task | not_applicable
    recurrence: likely | unclear | unlikely
    fix_target: source_prompt | final_form | loop_ledger | executor | none
    destination: global_friction | project_task | report_only | ignore
    suggested_disposition: promoted | resolved | ignored | deferred
    reason: <one sentence>
```

Never invent a candidate merely because an objective event, final-form, loop-ledger contract, correction, or retry exists. Cite evidence sufficient for the main agent to verify each proposed disposition.

Write this plain-language JSON to `audit-summary.json`:

```json
{
  "schema": "save-context.audit-summary.v1",
  "thread_id": "<same exact id as agent-audit.yaml>",
  "object": "<short real project, route, or work object>",
  "finding": "<one plain-language sentence describing the most important finding, or that no evidence-backed finding exists>",
  "evidence": ["<up to three exact, useful anchors>"],
  "recommendation": "<one plain-language next action; say no action when there are no candidates>",
  "candidate_ids": ["<every audit_id from agent-audit.yaml, lane order, exactly once>"]
}
```

This summary is a review aid, not a settlement decision or execution authorization. Avoid internal lane counts, receipt mechanics, and unexplained IDs in `finding` and `recommendation`. When both lanes are empty, use an empty `candidate_ids` list and empty `evidence` list.
