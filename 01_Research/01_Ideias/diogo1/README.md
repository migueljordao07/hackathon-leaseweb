# Diogo's Hackathon Ideas (diogo1)

Ideas proposed by Diogo or developed from his prompts. Cards follow the [idea template](../Miguel/idea-template.md). Contribution identifies the idea's origin, not an assigned implementation owner.

Six idea cards based on recurring complaints found on Reddit and related practitioner discussions (HN, Server Fault, blogs), each checked against existing tools on 20 November 2026. "Not implemented" means no tool doing the full workflow was found in a quick search; significant parts of every idea already exist, and the closest precedents are listed in each card (second, deeper check done the same day).

| ID | Idea | Main question | Closest existing precedent | Initial assessment | Relative effort |
|---|---|---|---|---|---|
| 01 | [ExitDrill](./01-exitdrill.md) | Could we actually leave AWS for a European provider, and can we prove it? | EscapeCloud, eu-cloud-mcp (diagnosis only); Firefly, StackGen (translation between AWS/Azure/GCP); consultancies (manual) | 17/20 | Medium-high |
| 02 | [Legacy Server Passport](./02-legacy-server-passport.md) | What does this undocumented server really do, and can we rebuild it safely? | Google Migrate to Containers, AWS App2Container, Azure Migrate dependency analysis, Enroll (most steps exist; no AI purpose explanation) | 15/20 | Medium |
| 03 | [Sovereignty Kill-Switch Test](./03-sovereignty-kill-switch.md) | What breaks if every non-EU service we depend on disappears? | EgressProof hackathon project (generic egress, not jurisdiction-aware) | 16/20 | Medium |
| 04 | [Sovereign Exit Semantic Auditor](./04-sovereign-exit-semantic-auditor.md) | Which hidden SDK semantics and non-EU dependencies will break when leaving AWS for a sovereign stack? | Former2, OpenTofu, LocalStack, AWS Transform (syntax/emulation or AWS-inward only) | 17/20 | Medium |
| 05 | [App-to-Infra PR Reality Guard](./05-app-pr-infra-cost-guard.md) | Will this application PR silently trigger a NAT egress or logging bill explosion in our real cloud topology? | Infracost (IaC-only), Semgrep (topology-blind), OpenCost (post-deploy) | 17/20 | Medium |
| 06 | [Evidence-Backed CVE Reachability & Patch Verifier](./06-cve-reachability-vex-verifier.md) | Which Trivy CVE alerts are actually reachable in our running service, and does the fix work without breaking it? | Trivy + vexctl (manual VEX), govulncheck (Go-only), Kubescape (Kubernetes-only) | 16/20 | Medium |

Scores are preliminary AI-assisted assessments using the four equally weighted [official criteria](../../../00_Context/challenge-and-guidelines.md). They are discussion aids, not team votes or jury predictions.

Notes:

- Reddit threads were read through search results and mirrors; verify the original threads before quoting them in the pitch.
- Ideas 01, 03, and 04 can be combined (an IaC exit drill plus application-SDK semantic parity verification plus a jurisdiction kill-switch mode). Idea 01 also overlaps with Miguel's [Change Rehearsal Lab](../Miguel/05-change-rehearsal-lab.md) and [Operation Outcome Verifier](../Miguel/01-operation-outcome-verifier.md): all rehearse in a disposable environment and prove the outcome with evidence.
- Ideas 05 and 06 add distinct FinOps/PR-review and DevSecOps/CVE-reachability tracks not covered in `Miguel/` or cards `01`–`03`.
- All six remain **Exploring**; no project has been selected.
