# Challenge Review

Run one evidence-backed pass after implementation checks. Treat the current evidence as potentially validating the implementation's own abstraction rather than the user-visible outcome. Challenge the proof boundary in the real consumer path. This is not hostile roleplay, a second design phase, or a replacement for ordinary code, security, document, or architecture review.

## Inputs

- The user-visible goal and acceptance criteria.
- The fixed review target and affected runtime or consumer path.
- The checks already run and the evidence they actually produced.
- Any generated, installed, copied, configured, or deployed artifact used by the change.

## Review Prior And Questions

Begin with one change-specific failure prior: `I know this class of change often fails when ...`. Tie it to the current diff, consumer path, or lifecycle; generic skepticism does not qualify.

Always answer: `What would a confident agent incorrectly declare complete here, and which evidence fails to prove it?`

Then select one or two lenses that can materially change readiness:

1. What familiar last-mile failure remains possible across the real invocation, installed/generated artifact, permissions, dependencies, lifecycle, deployment, or first use?
2. Which claim still relies on source structure, a mock, fixture, convention, inference, or a constrained environment instead of direct observation?
3. Which result depends on human perception, business judgment, real credentials, production state, or an irreversible action that the agent cannot safely prove?
4. Did the change fix the owning source or contract with the simplest in-scope solution instead of patching a downstream symptom or adding speculative compatibility or process?

## Proof Boundary

Always state:

- `agent proved`: conclusions supported by direct evidence from this run;
- `agent did not prove`: remaining inference, constrained coverage, unavailable state, or judgment;
- `human verification before readiness`: exact action, expected signal, and why the agent cannot perform it, or `none` with direct evidence;
- `human verification after submission`: the same details for a non-blocking real-environment check, or `none`.

Do not write generic `manual testing recommended`. Do not delegate a check the agent can perform with available tools and authorization. If unperformed human verification determines an acceptance claim, report a `blocking challenge`.

## Findings

- `blocking challenge`: an acceptance, safety, data, integration, or real-consumer gap changes readiness.
- `current-scope improvement`: a small attributable correction strengthens the current result without changing goal or acceptance.
- `inspiration`: a useful improvement expands current scope and is advisory only.

Run one pass, answer the mandatory question, select at most two additional lenses, and report at most three material findings. End with `next_review.strategy: none` unless another atomic strategy has a concrete unresolved question; challenge never recommends itself.
