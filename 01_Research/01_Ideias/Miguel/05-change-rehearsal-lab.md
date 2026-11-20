# Change Rehearsal Lab

> For **operators testing an agent-proposed fix**, we help **observe side effects before touching the target service** using **AI to select relevant checks and explain an isolated rehearsal**, improving **detection of regressions in the supported test environment**.

**Proposed by:** AI-assisted team brainstorming; owner unassigned · **Status:** Exploring
**Theme:** AI-assisted operations / Security & data protection
**Date:** 20 November 2026

## 1. Problem and user

- **Who encounters this, and when?** A small infrastructure team evaluating a configuration change without confidence in its effect on consumers.
- **What goes wrong today?** A permission change removes unwanted access but also breaks a legitimate client. Reviewing configuration alone misses application behavior.
- **Current workaround:** A staging service, scripted integration tests, or manual testing on a disposable copy.
- **Evidence and source:** The [Reddit discussion: Why do you think AI agents are still so unreliable at cloud / infra ops?](https://www.reddit.com/r/Cloud/comments/1xo16db/why_do_you_think_ai_agents_are_still_so/) includes suggestions to rehearse changes in digital twins. Our proposal deliberately limits the experiment to a copied local service; it is not a claim to reproduce an entire cloud.

## 2. Proposed solution and AI contribution

- **User workflow:** Provide a supported service configuration, proposed patch, and intended behavior → reset an isolated fixture → AI selects checks from a reviewed catalogue → execute the patch and tests → explain differences with links to probe output.
- **What AI adds:** Map the intent to relevant checks and explain tradeoffs in observed results. The runner decides test outcomes; generated explanations cannot turn a failure into a pass.
- **Simple baseline:** A manually selected integration-test suite running on the same fixture.
- **Action boundary:** Changes apply only to the disposable rehearsal instance. The runner exposes fixed actions, excludes production credentials, and resets between cases. No promotion into a real environment in the MVP.

## 3. Existing alternatives and difference

| Alternative or workaround | What it already solves | Our specific difference |
|---|---|---|
| Staging environment plus integration tests | Executes changes and checks application behavior | Proposed: select intent-specific checks and explain the evidence in an operator-facing report. |
| [CloudOpsBench](https://github.com/CloudOpsBench/CloudOpsBench) | Cloud-operation tasks with setup and grading | Proposed: rehearse one supplied change in a narrow local fixture. Its repository requires a separate execution harness; reuse is optional. |

**Why would this user choose our approach?** Hypothesis: it makes a small rehearsal easier to configure and interpret. It must demonstrate useful AI selection beyond a fixed regression suite. No comprehensive competitor review has been performed.

## 4. Smallest working demo

**Demo story:** Tightening a local data service's permissions should block an unwanted client while preserving a legitimate consumer.

1. **Before:** A disposable service and two client identities reproduce an overly broad access policy.
2. **Intervention:** Rehearse an intentionally excessive fix. Show that the unwanted client is blocked but the legitimate consumer now fails too.
3. **After:** Rehearse a narrower patch; independent probes confirm both intended conditions. Display the evidence and a short AI explanation for each run.

- **Must build:** Resettable isolated fixture; patch/test runner; AI check selector and comparison report.
- **Out of scope today:** A general digital twin, production traffic replication, provider API emulation, and automatic deployment.
- **Success metric:** Proposed target: distinguish a valid fix, an excessive fix, and an ineffective fix; preserve fixture reset consistency. Measure selection accuracy and run latency against the fixed suite. These are goals, not observed results.
- **Failure case:** Unsupported patches, missing dependencies, or a failed reset produce an invalid rehearsal, never an assurance that the change is safe.
- **Demo fallback:** A prebuilt synthetic service and clearly labeled model-response replay; the isolated patches and client probes run live.

## 5. Feasibility on the supplied Linux VM

| Dependency | Proposed approach | Available / Unverified / Blocked |
|---|---|---|
| Data and telemetry | Synthetic policy, identities, requests, and expected outcomes | Unverified: fixture and checks must be built. |
| Model and inference | Structured check selection and evidence explanation | Unverified: API access, latency, budget. |
| Infrastructure and permissions | Containerized fixture if available; otherwise a bounded local process sandbox | Unverified: container rights, RAM, isolation, reset behavior. |
| Libraries and integrations | Python runner; optional container tooling and UI | Unverified: installation and chosen dependency licenses. |

**Rough effort and split:** Higher relative effort. Suggested split: fixture/isolation, reset/test runner, AI selector, report UI, and evaluation/pitch. Hardest integration: repeatable reset and sufficient behavioral fidelity. Owners unassigned.
**Biggest blocker:** Infrastructure work may consume the day before a meaningful AI contribution is demonstrated.

Use fixture-only data and credentials. The report must state what the rehearsal does and does not represent.

## 6. Fastest validation

- **Riskiest assumption:** A small reproducible environment captures useful failures and AI improves check selection or interpretation.
- **Quick experiment:** Build the service and three patch variants without AI first; confirm that deterministic tests distinguish them and that reset works repeatedly. Then compare AI-selected checks with the fixed suite.
- **Continue if:** The fixture is reliable, the failure is meaningful, and AI reduces a real selection or interpretation step.
- **Simplify or park if:** Reset/isolation remains unreliable or the AI adds only narration. Consider the [outcome verifier](./01-operation-outcome-verifier.md) as the smaller experiment.

## 7. Team decision

Initial AI assessment against the [official criteria](../../../00_Context/challenge-and-guidelines.md); provisional, not a team vote or proof of feasibility.

| Criterion | Score | Reason |
|---|---|---|
| Innovation | 3 | Rehearsal is established; intent-specific assistance needs validation. |
| Applicability | 4 | Tangible regression problem, with customer demand untested. |
| Technical complexity and quality | 4 | Isolation, reproducibility, probes, and model integration. |
| Presentation and clarity | 4 | Two client outcomes clearly reveal the tradeoff. |
| **Total** | **15/20** | Higher execution risk than the outcome verifier. |

**Decision:** Explore only after a quick fixture-feasibility check.
**Reason and next action:** Prove reset and the three patch cases before choosing this as the day's project; owner unassigned.
