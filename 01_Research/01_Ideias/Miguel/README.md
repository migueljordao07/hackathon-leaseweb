# Miguel's Hackathon Ideas

Ideas proposed by Miguel or developed from his prompts belong in this folder. Use the [idea template](./idea-template.md) for future cards, choose the next free numeric ID, and add each new card to this index. Contribution identifies the idea's origin, not an assigned implementation owner.

Five initial idea cards using the [idea template](./idea-template.md), derived from the [Reddit discussion about unreliable cloud/infra agents](https://www.reddit.com/r/Cloud/comments/1xo16db/why_do_you_think_ai_agents_are_still_so/). Every card links directly to that source and distinguishes the reported problem from our proposed solution.

| ID | Idea | Main question | Initial assessment | Relative effort |
|---|---|---|---|---|
| 01 | [Operation Outcome Verifier](./01-operation-outcome-verifier.md) | Did the operation actually achieve its intended outcome? | 16/20 | Medium |
| 02 | [Change Impact Reviewer](./02-change-impact-reviewer.md) | Does the change affect workloads outside the requested scope? | 15/20 | Medium |
| 03 | [Project Cleanup Planner](./03-project-cleanup-planner.md) | Which resources can be retired without affecting other projects? | 14/20 | Medium |
| 04 | [Stale Plan Detector](./04-stale-plan-detector.md) | Is the plan still valid after the environment changes? | 13/20 | Low-to-medium |
| 05 | [Change Rehearsal Lab](./05-change-rehearsal-lab.md) | What breaks when we try this patch in the supported disposable environment? | 15/20 | Higher |

Scores are preliminary AI assessments using the four equally weighted [official criteria](../../../00_Context/challenge-and-guidelines.md). They are discussion aids, not team votes, measured outcomes, or jury predictions. Effort estimates are relative; actual VM access, model access, and team capacity remain unverified.

Suggested first experiments: compare idea 01 against a fixed verification checklist, then idea 02 against a static scope allowlist. All five remain **Exploring**; no project has been selected. Each card contains its own validation experiment and conditions for simplifying or parking it.

The thread supplies problem signals, not representative customer research or proof of an unoccupied market. No prototype has been built or tested as part of these cards. See the [team briefing](../../ai-cloud-infrastructure-team-briefing.md) for broader context.
