# Change Impact Reviewer

> For **operators approving agent-generated infrastructure changes**, we help **identify effects outside the requested scope** using **AI to connect user intent with a dependency graph and proposed change**, reducing **unnoticed effects on unrelated workloads**.

**Proposed by:** AI-assisted team brainstorming; owner unassigned · **Status:** Exploring
**Theme:** AI-assisted operations / Security & data protection
**Date:** 20 November 2026

## 1. Problem and user

- **Who encounters this, and when?** An operator reviewing a change proposed to fix one service in a shared environment.
- **What goes wrong today?** A plan removes a dependency used by both the target application and another workload. Fixing one problem creates an outage elsewhere.
- **Current workaround:** Read the diff, inspect dependencies, run policies, and ask an experienced colleague to review.
- **Evidence and source:** The [Reddit discussion: Why do you think AI agents are still so unreliable at cloud / infra ops?](https://www.reddit.com/r/Cloud/comments/1xo16db/why_do_you_think_ai_agents_are_still_so/) describes scope violations and discusses assessing change impact. This motivates the idea; it does not establish demand or complete dependency discovery.

## 2. Proposed solution and AI contribution

- **User workflow:** Enter the request, allowed resources, inventory, and proposed diff → compute affected dependencies → AI explains scope conflicts and proposes a narrower plan → code checks the revised proposal against explicit limits.
- **What AI adds:** Connect an informal request to infrastructure entities and explain why a technically valid change violates its intent.
- **Simple baseline:** A static rule forbidding changes outside an explicit resource list, plus manual diff review.
- **Action boundary:** Read-only analysis by default. A small executor can apply only approved operation types to disposable fixtures; graph and allowlist checks remain deterministic.

## 3. Existing alternatives and difference

| Alternative or workaround | What it already solves | Our specific difference |
|---|---|---|
| Manual dependency and diff review | Contextual impact assessment by an engineer | Proposed: make the reasoning and affected paths visible before approval. |
| [Conftest](https://www.conftest.dev/) | Explicit configuration policies | Proposed: combine policies with task intent and a bounded dependency graph. |

**Why would this user choose our approach?** Hypothesis: it helps a reviewer spot a shared dependency faster. It must add value beyond graph traversal and static ownership rules.

## 4. Smallest working demo

**Demo story:** Retiring application A must preserve application B, but the proposed plan removes their shared data service.

1. **Before:** Two small applications use a shared service. The intentionally overbroad plan includes removing that service.
2. **Intervention:** Show the dependency path to B, the request's allowed scope, and a blocked change with an explanation.
3. **After:** Apply a narrower approved operation that retires only A; a live probe confirms B remains operational.

- **Must build:** Explicit inventory/dependency graph; plan parser and policy gate; explanation/report with a constrained fixture executor.
- **Out of scope today:** Automatic discovery across arbitrary providers, comprehensive impact prediction, and production execution.
- **Success metric:** Proposed target: block all three seeded out-of-scope plans, permit two valid plans, and preserve the unrelated application's probe after permitted execution. These goals have not been tested.
- **Failure case:** Missing ownership or dependency information yields unknown impact and blocks demo execution pending clarification.
- **Demo fallback:** Use a clearly labeled synthetic inventory and stored model explanation; dependency checks and application probes still run live.

## 5. Feasibility on the supplied Linux VM

| Dependency | Proposed approach | Available / Unverified / Blocked |
|---|---|---|
| Data and telemetry | Small JSON inventory, dependency edges, and proposed operations | Unverified: fixtures must be built. |
| Model and inference | Structured scope interpretation and explanation | Unverified: model/API access and cost. |
| Infrastructure and permissions | Three local service processes; containers optional | Unverified: resources and process/network controls. |
| Libraries and integrations | Python graph traversal; small JSON schema; optional UI | Unverified: chosen dependencies and licenses. |

**Rough effort and split:** Medium. Suggested split: fixtures/graph, parser/gate, AI interpretation, UI, and evaluation/pitch. Hardest integration: consistent resource identity across the request, graph, and diff. Owners unassigned.
**Biggest blocker:** An incomplete inventory can hide the very impact the tool claims to explain.

Provider account access is optional for the local experiment; never assume it follows from VM login.

## 6. Fastest validation

- **Riskiest assumption:** Intent interpretation adds useful decisions beyond a resource allowlist.
- **Quick experiment:** Use five plans mixing valid changes, shared resources, and ambiguous scope; compare the static gate with the AI-assisted review.
- **Continue if:** Explanations identify concrete dependency paths and help produce valid narrower plans without weakening the gate.
- **Simplify or park if:** A few static rules solve every case or inferred dependencies are presented as facts.

## 7. Team decision

Initial AI assessment against the [official criteria](../../../00_Context/challenge-and-guidelines.md); provisional, without team agreement or measured implementation quality.

| Criterion | Score | Reason |
|---|---|---|
| Innovation | 3 | Intent-to-impact connection is the proposed differentiator. |
| Applicability | 4 | Clear shared-infrastructure scenario; demand unvalidated. |
| Technical complexity and quality | 4 | Combines graph reasoning, scoped operations, and independent probes. |
| Presentation and clarity | 4 | A protected unrelated application makes the impact tangible. |
| **Total** | **15/20** | Inventory completeness remains a separate feasibility risk. |

**Decision:** Explore; proposed second candidate to validate.
**Reason and next action:** Build the five-plan fixture and test the baseline before attempting automated discovery; owner unassigned.
