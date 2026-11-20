# Operation Outcome Verifier

> For **operators supervising infrastructure agents**, we help **detect incomplete or falsely reported changes** using **AI to translate intent into explicit verification checks**, improving **the proportion of completion claims backed by evidence**.

**Proposed by:** AI-assisted team brainstorming; owner unassigned · **Status:** Exploring
**Theme:** AI-assisted operations / Security & data protection
**Date:** 20 November 2026

## 1. Problem and user

- **Who encounters this, and when?** An operator reviewing an agent's claim that a configuration or credential change is finished.
- **What goes wrong today?** A signing key is updated, but an old key remains accepted or a legitimate consumer stops working. A successful update response does not test the intended behavior.
- **Current workaround:** A manually written checklist, application probes, and an engineer inspecting the change.
- **Evidence and source:** The [Reddit discussion: Why do you think AI agents are still so unreliable at cloud / infra ops?](https://www.reddit.com/r/Cloud/comments/1xo16db/why_do_you_think_ai_agents_are_still_so/) identifies inadequate state verification. This is a community-reported problem; the proposed workflow and customer demand remain hypotheses.

## 2. Proposed solution and AI contribution

- **User workflow:** Submit the intended operation and agent report → AI selects required checks from a reviewed catalogue → a deterministic runner executes them → show passed, failed, and unknown conditions with evidence.
- **What AI adds:** Interpret requests and identify which existing checks apply, including negative conditions such as an old credential no longer working. Explain failures without deciding pass/fail itself.
- **Simple baseline:** A fixed checklist for the same operation, plus an agent asked to verify its own work. Compare all approaches on identical fixtures.
- **Action boundary:** The verifier reads fixture state and invokes allowlisted probes. Only a separate, deliberately limited demo executor changes the disposable application. Unknown checks cannot turn into arbitrary generated shell commands.

## 3. Existing alternatives and difference

| Alternative or workaround | What it already solves | Our specific difference |
|---|---|---|
| Manual operational checklist | Explicit acceptance conditions for a known procedure | Proposed: select the right checks from a natural-language request and surface omissions. |
| [Conftest](https://www.conftest.dev/) | Policies against structured configuration | Proposed: connect the requested outcome to observed application behavior after the change. |

**Why would this user choose our approach?** Hypothesis: it reduces the effort of choosing and documenting the right checks across a small family of operations. If a fixed checklist performs equally well with less effort, narrow or reconsider the AI contribution.

## 4. Smallest working demo

**Demo story:** An agent reports a local signing-key rotation complete while the old key still works.

1. **Before:** A disposable webhook receiver accepts the old key; a scripted change updates a config but leaves the old validation path active.
2. **Intervention:** The AI selects checks for new-key acceptance, old-key rejection, and legitimate consumer continuity.
3. **After:** The runner rejects the completion claim, displays the failed old-key probe, then passes after a corrected change.

- **Must build:** Disposable receiver/consumer; intent-to-check selector; verification runner with a small evidence report.
- **Out of scope today:** General cloud verification, arbitrary generated tests, production secrets, and automatic repair.
- **Success metric:** Proposed target: detect all three deliberately incomplete fixture variants, accept the correct variant, and report unknown when a required probe is unavailable. These are acceptance goals, not measured results.
- **Failure case:** Malformed model output, missing probes, or timeouts produce an incomplete report, never a success verdict.
- **Demo fallback:** Replay a clearly labeled model response while executing the checks live against resettable fixtures.

## 5. Feasibility on the supplied Linux VM

| Dependency | Proposed approach | Available / Unverified / Blocked |
|---|---|---|
| Data and telemetry | Synthetic rotation variants with known expected outcomes | Unverified: fixtures must be built. |
| Model and inference | One model call producing validated check IDs | Unverified: API access, latency, and budget. |
| Infrastructure and permissions | Local Python processes; containers optional | Unverified: VM resources, Python, networking. |
| Libraries and integrations | Python standard library first; dependency licenses reviewed if added | Unverified: implementation stack. |

**Rough effort and split:** Medium relative effort. Suggested split: fixtures, runner, AI selector, report UI, and evaluation/pitch. Hardest integration: mapping intent to checks without silently omitting a required condition. Owners are not assigned.
**Biggest blocker:** A check catalogue too narrow to demonstrate useful AI selection.

Keep credentials local; a chat subscription does not establish model API access.

## 6. Fastest validation

- **Riskiest assumption:** AI chooses useful conditions more reliably or with less operator effort than a fixed operation checklist.
- **Quick experiment:** Write four fixtures and several differently worded requests; compare AI-selected checks with a human-authored expected checklist.
- **Continue if:** It exposes incomplete outcomes, includes necessary negative checks, and saves a meaningful manual selection step.
- **Simplify or park if:** The AI only restates an already fixed checklist or repeatedly misses critical conditions.

## 7. Team decision

Initial AI assessment against the [official criteria](../../../00_Context/challenge-and-guidelines.md); discussion aid only. No team vote or implementation result is implied.

| Criterion | Score | Reason |
|---|---|---|
| Innovation | 3 | Specific workflow; verification itself is established. |
| Applicability | 4 | Clear completion-review problem, with demand still unvalidated. |
| Technical complexity and quality | 4 | Connects intent interpretation, controlled probes, and evidence. |
| Presentation and clarity | 5 | Old credential still working makes a visible failure. |
| **Total** | **16/20** | Feasibility must be checked separately. |

**Decision:** Explore; proposed first candidate to validate.
**Reason and next action:** Test the four fixtures before choosing a UI or expanding operations; owner unassigned.
