# Live Copilot

Use when the user wants to operate the page while the agent continuously prepares the content needed for the current step.

## Authority

- The user owns all browser input and navigation.
- The agent may read the explicitly shared target and relevant task sources, then generate suggestions in chat or another local, non-page surface.
- The agent does not click, type, paste, upload, change selection, copy suggestions into the system clipboard, or submit unless the user explicitly transitions to another mode and grants the required authority.

## Workflow

1. Treat a request to guide or observe while the user operates as authority for read-only binding to that target. Start or attach the selected runtime, bind the exact shared tab, take the initial snapshot, and state what is being observed. If one bounded binding attempt cannot identify the relevant tab, ask the user to foreground or share the exact page and retry after confirmation; the observation scope remains that tab only.
2. Read visible field labels, instructions, options, validation errors, and the current workflow step. Read existing values only when needed for the requested assistance.
3. Generate the next useful field value with its source, assumptions, format constraints, and unresolved choices. Keep suggestions easy to copy and update them when the page changes.
4. When the user navigates or the target identity changes, rebind from explicit evidence before continuing. Do not replay stale suggestions into a new step.
5. Stop observation when the user says the workflow is complete, the target disappears, or the requested scope ends.

Live Copilot entry is complete only with a runtime receipt, exact target identity, and first snapshot. Asking the user to transcribe visible fields is the explicitly selected chat-only fallback, not browser observation.

## Data Handling

Do not persist the user's typed values by default. Redact sensitive values from commentary and temporary evidence. If the task needs a durable artifact, save only the minimum structured result and report its exact path and cleanup condition.
