# AI for Cloud Infrastructure: Team Briefing

**InfraHack | 20 November 2026 | Reading time: 10-12 minutes**

## Executive Summary

AI-assisted cloud operations is already a product category. AWS DevOps Agent became generally available in March 2026; Google's investigation workflow remains Preview and access-restricted. Open-source HolmesGPT provides a comparable investigation pattern. A general chatbot that explains infrastructure errors therefore needs a more specific reason to exist. [2][3][4]

The central workflow is to collect operational evidence, connect symptoms to likely causes, propose a bounded change, and check the result. Today's products document useful investigation capabilities; their availability does not establish reliable autonomous repair. An independent current benchmark tests diagnosis from recorded incidents, with a leading score of 56.2% on its particular metric, rather than production incidents resolved. [2][3][5]

Our opportunity is to explore a narrow problem where AI improves an observable outcome: understanding an incident, reviewing a configuration fix, explaining a failed recovery, or assessing migration dependencies. These are brainstorming hypotheses. Existing scanners, cost engines, infrastructure tools, and recovery checks provide strong baselines. [7][9][10][11][14]

The practical questions are: **Who struggles with this task? What evidence can our prototype access? What does AI add? How will we prove it worked?** Favor a small, repeatable experiment on the supplied Linux VM, with a clear comparison and an honest failure case.

## Introduction: A Shared Mental Model

A **virtual machine (VM)** runs an operating system on virtual hardware. **Containers** package applications; **Kubernetes** coordinates containers across machines. **Infrastructure as code (IaC)** describes resources in files so tools can plan and apply changes. **Observability** uses evidence about system behavior: logs record events, metrics measure quantities over time, and traces follow requests through services. OpenTelemetry standardizes collection and export of these signals. [1][14]

For this discussion, **AIOps** means applying analytics or AI to operations. A **copilot** assists a person; an **agent** can repeatedly select tools and act on their results. **Retrieval-augmented generation (RAG)** supplies retrieved context to a language model. More autonomy increases the importance of permissions and validation. [4][8]

Keep this loop in mind: **observe → investigate → recommend → authorize → execute → verify**. We can build value in one step without automating every step.

## Main Analysis: What Exists and What Remains Difficult

### Operations and reliability

AWS's March 2026 launch describes an agent connecting telemetry, deployments, repositories, and runbooks, including Azure and on-premises environments. Its promised reduction from hours to minutes is a vendor claim, not an independently established result for our workload. [2]

Google's Gemini Cloud Assist investigations links observations to source data, proposes possible causes, and recommends next steps. It remains Preview; creating or editing investigations requires Premium Support or separately requested access. Google explicitly warns that some resources within supported products remain unsupported. [3]

HolmesGPT is an Apache-2.0 open-source alternative using a tool-driven investigation loop and multiple model providers. It can investigate VM environments without Kubernetes, although its background operator mode requires Kubernetes. A configured model and relevant telemetry access are still necessary. [4]

**Evidence check:** ITBench-AA evaluates 59 Kubernetes incident snapshots, with three repeats; 40 tasks are public and 19 held out. The inspected leaderboard's best score is **56.2% average precision at full recall**: missing a true causal entity scores zero, while extra entities reduce precision. This is offline diagnosis, not a repair-success percentage. We did not reproduce it. [5]

**Implication:** investigate a specific failure with cited evidence and an explicit “insufficient information” outcome. Compare against a fixed runbook, measuring diagnosis correctness, unsupported claims, time, and inference usage.

### Security and data protection

Microsoft Defender's Security Alert Triage Agent explains classifications and accepts analyst feedback. Its email/collaboration capabilities are generally available; cloud/identity triage remains Preview in documentation updated 12 November. It requires a Security Copilot workspace with capacity, applicable Defender licenses, and permissions. This is a managed workflow, rather than a component we can simply deploy on our VM. [6]

For an open-source baseline, Trivy already detects misconfigurations in Docker, Kubernetes, and Terraform files using predefined checks. AI's plausible contribution is explaining relevance or proposing a context-sensitive correction. A fluent patch should still face a rescan and application tests. Detection alone does not establish an AI advantage. [7]

AI also introduces an attack surface. OWASP documents indirect prompt injection through external content and recommends restricted privileges, deterministic validation, and checks around privileged actions. **Our application of that guidance:** treat logs and runbooks as untrusted input; enforce tool permissions in code. A malicious log should not acquire authority to execute commands. [8]

Data protection needs outcome checks too. AWS Backup already supports validation workflows after restoration, including application health checks. A completed restore is a different observation from a usable recovered service. AI might explain a failed recovery check, while deterministic tests decide whether recovery succeeded. [9]

### Cost and resource efficiency

Resource recommendations predate generative assistants. Compute Engine recommends VM sizes from eight days of CPU/memory observations; Google documents limitations for monthly peaks and brief spikes. A proposed saving can therefore conflict with a workload's actual needs. [10]

OpenCost offers an Apache-2.0 measurement and allocation engine, providing an open-source foundation rather than evidence of AI optimization. Its Kubernetes allocation deployment requires Kubernetes and Prometheus; do not add that setup to a one-VM demo without a reason. [11][17]

The FinOps Foundation's 2026 survey, covering 1,192 respondents, distinguishes **managing AI costs** from **using AI for cost management**. Requested capabilities include granular AI-spend visibility and architecture costing before deployment. This is evidence of practitioner priorities, not proof of savings or universal adoption. [12]

**Implication:** explore whether AI helps explain a cost anomaly or choose between constrained alternatives. Compare with a simple utilization rule; measure projected cost separately from observed latency/errors, and include the assistant's own usage. Avoid a savings percentage derived only from invented prices or unrepresentative traces.

### Migration, alternatives, and sovereignty

AWS Transform demonstrates commercial AI-assisted migration. Its 2026 release notes expand sources to Hyper-V and bare metal and add inventory-driven network generation and IaC outputs. The destination remains AWS infrastructure: broader source support does not make it a provider-neutral exit tool. [13]

OpenTofu supplies a non-AI foundation: declarative files, provider APIs, plans, and managed state. **Inference:** changing the orchestration tool does not translate provider-specific databases, identity rules, or network behavior. Generated configuration still needs functional validation. [14]

Sovereignty also involves more than location. The Commission's October 2025 framework separately considers data/AI control, operational autonomy, and technology dependencies. A locally hosted assistant can retain an external processing dependency when it sends telemetry to a remote model. Use these dimensions to inspect a design; this framework does not certify our prototype or any provider. [15]

Leaseweb documents Public Cloud lifecycle and CPU-metrics APIs authenticated with a Customer Portal API key. Access to the event VM does not establish access to its owning account or those endpoints. Begin with local application/OS evidence and add provider integration only after confirming actual access. [16]

## Synthesis: Problem Areas for Brainstorming

The recurring engineering problem is connecting **evidence, context, and independently checked outcomes**. This is our interpretation across the examples, not proof of an unoccupied market. [3][5][7][9][10][14]

| Problem area and user | Possible experiment | Non-AI baseline and outcome |
|---|---|---|
| VM operator cannot distinguish symptoms from causes | Diagnose a deliberately broken small service using logs, metrics, and recent changes; identify missing evidence. | Fixed runbook; correct diagnosis and unsupported conclusions. |
| Developer cannot assess a proposed security fix | Explain a scanner finding, propose a narrow patch, then rescan and test behavior. | Scanner guidance; issues removed without regressions. |
| Operator sees a restore complete but the application fails | Restore disposable data, run integrity/application checks, explain a seeded failure. | Scripted recovery checklist; failure detection and explanation correctness. |
| Team cannot assess exit readiness | Inspect a small inventory and explain dependencies blocking one declared target. | Compatibility checklist; known blockers found and functional tests passed. |
| Engineer cannot judge a resource recommendation | Explain a usage anomaly and compare options against a performance constraint. | Utilization threshold; estimated cost and measured service behavior. |

These are candidate workflows, not selected projects. Their AI contribution and usefulness still need testing.

## Limitations: What We Do Not Know Yet

This briefing verifies documented capabilities and research conditions; it does not test products, reproduce benchmarks, or establish customer demand. Product documentation demonstrates intended behavior, while vendor speed claims remain claims. The current benchmark is only partly public and does not test autonomous remediation. [2][5]

Live documentation can change; undated pages are snapshots of what was accessible today. We have not established the VM's CPU/RAM, GPU availability, package-installation rights, network access, model/API budget, or Leaseweb account permissions. Team chat subscriptions do not establish API availability. No cost, deployment-time, or production-reliability guarantee follows from this research.

## Recommendations: Start the Discussion

Take ten minutes to read, then let each teammate propose one **user + problem + AI contribution + measurable outcome**. Ask what a script already solves, what data we can obtain today, and which result would disprove the proposal.

Before choosing, confirm VM and model access. Scope a Linux demo around one input, one bounded workflow, and a visible before/after check. Use clearly labeled synthetic fixtures where needed; provide a replay path and distinguish replayed output from a live model call. Keep secrets local and inspect chosen dependencies and licenses.

Compare proposals against the four equally weighted [judging criteria](../00_Context/challenge-and-guidelines.md): innovation, applicability, technical quality/complexity, and presentation clarity. Prefer a demonstrable outcome we can explain within five minutes.

## Bibliography

All sources accessed **20 November 2026**. Dates below indicate publication/update when established; “living” means no reliable page publication date was established. Supplementary evidence is in the [research dossier](./sources/ai-cloud-infrastructure-2026-11-20/README.md).

[1] OpenTelemetry (2026). "Signals". [Documentation](https://opentelemetry.io/docs/concepts/signals/), modified 10 March.

[2] AWS (2026). "AWS DevOps Agent is now generally available". [Announcement](https://aws.amazon.com/about-aws/whats-new/2026/03/aws-devops-agent-generally-available/), 31 March.

[3] Google Cloud (2026). "Troubleshoot issues with Gemini Cloud Assist investigations". [Documentation](https://docs.cloud.google.com/cloud-assist/investigations), updated 10 November.

[4] HolmesGPT (living). "HolmesGPT README". [Repository](https://github.com/HolmesGPT/holmesgpt/blob/master/README.md).

[5] Artificial Analysis (living). "ITBench-AA Benchmark". [Evaluation and methodology](https://artificialanalysis.ai/evaluations/itbench-aa).

[6] Microsoft (2026). "Deploy AI agents in Microsoft Defender". [Documentation](https://learn.microsoft.com/en-us/defender-xdr/security-copilot-agents-defender), updated 12 November.

[7] Aqua Security (living). "Misconfiguration scanning". [Trivy documentation](https://trivy.dev/docs/latest/guide/scanner/misconfiguration/).

[8] OWASP (2025). "LLM01:2025 Prompt Injection". [Security guidance](https://genai.owasp.org/llmrisk/llm01-prompt-injection/).

[9] AWS (living). "Restore testing validation". [AWS Backup documentation](https://docs.aws.amazon.com/aws-backup/latest/devguide/restore-testing-validation.html).

[10] Google Cloud (2026). "Apply machine type recommendations to VM instances". [Documentation](https://docs.cloud.google.com/compute/docs/instances/apply-machine-type-recommendations-for-instances), updated 10 November.

[11] OpenCost (living). "FAQ". [Project documentation](https://opencost.io/docs/faq/).

[12] FinOps Foundation (2026). "State of FinOps 2026". [Original survey report](https://data.finops.org/).

[13] AWS (2026). "Release notes". [AWS Transform documentation](https://docs.aws.amazon.com/transform/latest/userguide/transform-vmware-release-notes.html), entries through October.

[14] OpenTofu (living). "What is OpenTofu?". [Documentation](https://opentofu.org/docs/intro/).

[15] European Commission (2025). "Cloud Sovereignty Framework". [Version 1.2.1](https://commission.europa.eu/document/download/09579818-64a6-4dd5-9577-446ab6219113_en), October, pp. 2-3.

[16] Leaseweb (living). "Developer API". [API reference](https://developer.leaseweb.com/docs/), Authentication and Public Cloud sections.

[17] OpenCost (living). "OpenCost Setup". [Installation requirements](https://opencost.io/docs/installation/install/).

## Methodology

Applied the [research plan](./ai-cloud-infrastructure-research-plan.md) through searches and direct reading of primary documentation, release notes, repositories, an original practitioner survey, and an independent evaluation. Checked recent product status against the 20 November cutoff. Separated capabilities, vendor claims, measured results, and team hypotheses; retained source locators and supporting records in the dossier. This is a focused briefing, not an exhaustive market survey or a project decision.
