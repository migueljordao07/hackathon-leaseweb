# Project Cleanup Planner

> For **operators retiring a project in shared infrastructure**, we help **separate removable, shared, and uncertain resources** using **AI to reconcile the request with ownership and dependency evidence**, reducing **accidental impact on other projects**.

**Proposed by:** AI-assisted team brainstorming; owner unassigned · **Status:** Exploring
**Theme:** AI-assisted operations / Security & data protection
**Date:** 20 November 2026

## 1. Problem and user

- **Who encounters this, and when?** A platform engineer asked to clean up an experiment, customer environment, or retired application.
- **What goes wrong today?** Names suggest that a storage resource belongs to one project, but it also contains another project's data. Removing the whole resource exceeds the request.
- **Current workaround:** Inspect tags, names, usage, references, and ownership; produce a manual cleanup checklist.
- **Evidence and source:** The [Reddit discussion: Why do you think AI agents are still so unreliable at cloud / infra ops?](https://www.reddit.com/r/Cloud/comments/1xo16db/why_do_you_think_ai_agents_are_still_so/) describes overly broad teardown behavior. The cleanup scenario and proposed product are our hypotheses, not a verified customer incident.

## 2. Proposed solution and AI contribution

- **User workflow:** Submit the retirement request and resource inventory → reconcile ownership evidence → propose remove, preserve, and ask-for-clarification groups → review exact targets → execute a bounded cleanup and verify preserved data.
- **What AI adds:** Interpret ambiguous project references, explain conflicting evidence, and formulate specific clarification questions. It may suggest classifications; unsupported ownership cannot authorize deletion.
- **Simple baseline:** A prefix/tag filter plus a manually reviewed target list.
- **Action boundary:** Use a reviewed allowlist of exact resource/object IDs. The demo archives disposable fixture objects instead of deleting real data. Shared or uncertain resources remain untouched; approved targets are revalidated before execution.

## 3. Existing alternatives and difference

| Alternative or workaround | What it already solves | Our specific difference |
|---|---|---|
| Tag/prefix cleanup script | Consistently labeled resources | Proposed: expose conflicting evidence and ask before treating naming as ownership. |
| [CloudOpsBench cleanup tasks](https://github.com/CloudOpsBench/CloudOpsBench) | Defined scenarios and automated grading for agent evaluation | Proposed: an operator-facing cleanup review workflow, not a new benchmark claim. |

**Why would this user choose our approach?** Hypothesis: it makes mixed-ownership cleanup easier to review. If explicit tags and rules cover the actual use case, the AI contribution may be unnecessary.

## 4. Smallest working demo

**Demo story:** Retire a pilot while preserving another application's objects in shared storage.

1. **Before:** A local object-store fixture contains pilot-only objects, unrelated objects, and one object with contradictory ownership metadata.
2. **Intervention:** Show a naive prefix plan beside an evidence-linked proposal that preserves shared data and asks about the ambiguous object.
3. **After:** Archive only approved objects; compare checksums and an application probe to show the other project's data still works.

- **Must build:** Resource/ownership fixture; classifier with evidence and clarification UI; allowlisted executor and preservation checks.
- **Out of scope today:** Production deletion, billing savings, automated account discovery, and arbitrary cloud resources.
- **Success metric:** Proposed target: zero unrelated objects changed, all ambiguous objects held for clarification, and all approved pilot objects archived across three fixture layouts. Not yet measured.
- **Failure case:** Conflicting evidence, a stale manifest, or a missing owner blocks the affected target rather than guessing.
- **Demo fallback:** A labeled filesystem-backed object-store simulation and replayed model output; target enforcement and checksums execute live.

## 5. Feasibility on the supplied Linux VM

| Dependency | Proposed approach | Available / Unverified / Blocked |
|---|---|---|
| Data and telemetry | Synthetic object catalogue, ownership metadata, and references | Unverified: fixtures must be authored. |
| Model and inference | Structured classification, evidence references, and questions | Unverified: API access, latency, budget. |
| Infrastructure and permissions | Local sandbox directory; object storage adapter optional | Unverified: VM environment; no provider API required. |
| Libraries and integrations | Python standard library and optional small UI | Unverified: stack and any added dependency licenses. |

**Rough effort and split:** Medium. Suggested split: fixture/catalogue, AI classifier, review UI, executor/checks, and evaluation/pitch. Hardest integration: enforcing approved ownership decisions independently of model output. Owners unassigned.
**Biggest blocker:** Fabricated ambiguity may make a compelling demo without representing a useful real workflow.

Use only disposable fixture data; keep account credentials out of the repository.

## 6. Fastest validation

- **Riskiest assumption:** Real cleanup tasks contain ambiguity that AI can help clarify beyond deterministic rules.
- **Quick experiment:** Compare a tag/prefix script and the proposed classifier on clean, shared, and contradictory ownership fixtures. Ask an available infrastructure engineer whether the cases resemble their work.
- **Continue if:** It helps clarify ambiguous cases while preserving the baseline's predictable behavior on clean cases.
- **Simplify or park if:** It merely renames tag filtering or cannot cite evidence for its classifications.

## 7. Team decision

Initial AI assessment against the [official criteria](../../../00_Context/challenge-and-guidelines.md); provisional and not a team selection.

| Criterion | Score | Reason |
|---|---|---|
| Innovation | 3 | Differentiation depends on useful ambiguity handling. |
| Applicability | 4 | Concrete retirement task; actual user demand unvalidated. |
| Technical complexity and quality | 3 | Bounded classification, execution, and preservation checks. |
| Presentation and clarity | 4 | Preserving another project's data provides a clear story. |
| **Total** | **14/20** | AI value is the main open question. |

**Decision:** Explore.
**Reason and next action:** Test whether ambiguity handling beats a tag-based baseline before adding a cloud adapter; owner unassigned.
