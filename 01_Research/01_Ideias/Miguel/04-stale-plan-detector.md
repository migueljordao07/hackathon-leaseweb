# Stale Plan Detector

> For **operators collaborating with infrastructure agents**, we help **prevent execution based on outdated context** using **AI to explain state differences and revise a plan**, reducing **changes applied against invalid assumptions**.

**Proposed by:** AI-assisted team brainstorming; owner unassigned · **Status:** Exploring
**Theme:** AI-assisted operations
**Date:** 20 November 2026

## 1. Problem and user

- **Who encounters this, and when?** An operator reviewing an agent's plan while another person or process can modify the environment.
- **What goes wrong today?** The agent proposes a configuration replacement from an old snapshot and overwrites a newer setting it never saw.
- **Current workaround:** Refresh state, inspect a new diff, use version checks, and coordinate changes manually.
- **Evidence and source:** The [Reddit discussion: Why do you think AI agents are still so unreliable at cloud / infra ops?](https://www.reddit.com/r/Cloud/comments/1xo16db/why_do_you_think_ai_agents_are_still_so/) discusses persistent wrong assumptions and context quality. Concurrent state changes are our specific extension of that problem framing, not a measured finding from the thread.

## 2. Proposed solution and AI contribution

- **User workflow:** Bind the request and plan to a versioned snapshot → compare that version before execution → block stale plans → show the changed evidence → AI proposes a revised plan that preserves unrelated updates.
- **What AI adds:** Explain whether the new state changes the user's intended outcome and generate a constrained revised proposal. Detecting a version mismatch itself is deterministic.
- **Simple baseline:** A version/hash check that rejects stale writes and asks a human to replan.
- **Action boundary:** The executor accepts only the current version and an approved operation. Demo writes use an atomic compare-and-update boundary; the model cannot override a mismatch. Broader cloud concurrency guarantees are out of scope.

## 3. Existing alternatives and difference

| Alternative or workaround | What it already solves | Our specific difference |
|---|---|---|
| Version/hash guard | Detects that the observed state changed | Proposed: explain the relevant difference and suggest a valid revised change. |
| Manual refresh and diff review | Lets an operator preserve concurrent edits | Proposed: reduce replanning effort with evidence-linked assistance. |

**Why would this user choose our approach?** Hypothesis: it helps when a stale plan requires contextual revision. Existing concurrency controls already solve the basic rejection problem, so novelty depends on useful replanning.

## 4. Smallest working demo

**Demo story:** An agent plans a timeout change, but a teammate updates an unrelated retry setting before execution.

1. **Before:** The agent reads configuration version 1 and proposes a whole-document update.
2. **Intervention:** A second UI changes the retry setting, creating version 2. The executor rejects the old plan and shows the mismatch.
3. **After:** AI proposes a narrow timeout patch against version 2; the approved write preserves the retry update and passes application checks.

- **Must build:** Versioned configuration service; plan/version gate with deterministic diff; AI replanning view and fixture probes.
- **Out of scope today:** Full distributed locking, arbitrary resource drift discovery, and cross-provider transactions.
- **Success metric:** Proposed target: reject every seeded stale plan, preserve unrelated edits, and correctly classify an incompatible concurrent change as requiring clarification. No results yet.
- **Failure case:** Repeated drift or contradictory intent stops execution. Set a small retry limit; do not let an agent loop indefinitely.
- **Demo fallback:** Predefined version changes with a labeled model-response replay; compare-and-update behavior remains live.

## 5. Feasibility on the supplied Linux VM

| Dependency | Proposed approach | Available / Unverified / Blocked |
|---|---|---|
| Data and telemetry | Versioned synthetic configuration and change history | Unverified: local fixture not built. |
| Model and inference | One constrained replan/explanation call | Unverified: API access and budget. |
| Infrastructure and permissions | Local Python service and browser/CLI client | Unverified: VM runtime and network access. |
| Libraries and integrations | Standard-library storage/locking initially; optional UI | Unverified: dependency choices and licenses. |

**Rough effort and split:** Low-to-medium relative effort. Suggested split: config service, version gate, AI replanner, UI, and evaluation/pitch. Hardest integration: proving that a revised write preserves unrelated state. Owners unassigned.
**Biggest blocker:** The result may be a conventional version guard with little additional AI value.

Keep configuration fixtures free of real credentials; confirm model access independently.

## 6. Fastest validation

- **Riskiest assumption:** AI helps an operator replan after drift rather than merely describing a diff.
- **Quick experiment:** Introduce unrelated, relevant, and conflicting edits between planning and execution; compare a plain version guard with the AI-assisted path.
- **Continue if:** The revised plans preserve unrelated edits and surface genuine conflicts with less manual reconstruction.
- **Simplify or park if:** Version rejection plus a normal diff is just as useful or the AI silently drops concurrent updates.

## 7. Team decision

Initial AI assessment against the [official criteria](../../../00_Context/challenge-and-guidelines.md); provisional, with no team decision or measured outcome implied.

| Criterion | Score | Reason |
|---|---|---|
| Innovation | 2 | State/version checks are established; AI replanning must differentiate. |
| Applicability | 4 | Concrete concurrent-change failure, demand unvalidated. |
| Technical complexity and quality | 3 | Controlled state handling and constrained replanning. |
| Presentation and clarity | 4 | A visible concurrent edit makes the failure easy to explain. |
| **Total** | **13/20** | Could become a component of another proposal. |

**Decision:** Explore as a bounded feature or small standalone experiment.
**Reason and next action:** Validate replanning against the plain version-guard baseline; owner unassigned.
