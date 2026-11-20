# Operations and Reliability: Evidence Notes

Snapshot and access date: **2026-11-20**. Primary sources only. No product, benchmark, or deployment was executed. Live documentation and repository state were inspected on the access date; undated pages do not establish when every feature shipped.

## O1. AWS DevOps Agent: commercial availability

- **Source:** [AWS DevOps Agent is now generally available](https://aws.amazon.com/about-aws/whats-new/2026/03/aws-devops-agent-generally-available/), AWS, published **2026-03-31**.
- **Evidence:** "Now generally available" (opening sentence).
- **Verified documented capability:** the GA announcement describes investigations that combine telemetry, deployment history, repositories, and runbooks, with Azure and on-premises support as well as AWS.
- **Vendor claim:** AWS attributes faster incident resolution and prevention to this workflow. Its statement about reducing resolution from hours to minutes is not an independent measurement and should not become a general efficacy claim.
- **Implication:** a generic incident chatbot is already an established product category. A prototype needs a particular underserved workflow, better evidence, portability, or an explicit correctness test.

## O2. AWS DevOps Agent: access boundaries

- **Source:** [Limiting Agent Access in an AWS Account](https://docs.aws.amazon.com/devopsagent/latest/userguide/aws-devops-agent-security-limiting-agent-access-in-an-aws-account.html), AWS user guide, no publication date displayed in the retrieved result.
- **Evidence:** "IAM policies are the only way to truly limit" (opening paragraph).
- **Verified documented behavior:** resource topology shown by the product does not itself define the permissions boundary. IAM roles control discovery and investigation access; effective permissions intersect the role policies and AWS's session permission guardrail. The documented default investigation permissions are read-only.
- **Requirements:** an AWS account and configured roles and integrations. Multi-account operation needs additional account roles.
- **Inference:** data collection access is a significant part of the engineering work. A tool can fail to explain an incident because it cannot see a dependency, even when its reasoning is sound.

## O3. Gemini Cloud Assist investigations: commercial alternative

- **Source:** [Troubleshoot issues with Gemini Cloud Assist investigations](https://docs.cloud.google.com/cloud-assist/investigations), Google Cloud, last updated **2026-11-10**.
- **Evidence:** "As of April 10, 2026" (access restriction notice).
- **Verified documented status:** investigations are a **Preview** offering. Creating, running, or editing them requires Premium Support or access requested through an account team.
- **Workflow:** collect observations from configurations, metrics, and logs; link observations to source data; generate one or more root-cause hypotheses and recommended next steps; optionally transfer context to human support.
- **Documented limit:** a product being supported does not mean every resource is supported. Google asks users to check whether expected resources appear in observations.
- **Inference:** citations, competing hypotheses, and visibility into missing inputs are useful product behavior, not cosmetic additions. No independent speed improvement was verified.

## O4. HolmesGPT: open-source alternative

- **Source:** [HolmesGPT README](https://github.com/HolmesGPT/holmesgpt/blob/master/README.md), live repository documentation; no single publication date.
- **Evidence:** "HolmesGPT uses an agentic loop to query live observability data" (How it Works).
- **Verified documented capability:** it integrates telemetry tools and cloud APIs to investigate root causes, supports multiple model providers, and can operate with VMs or bare metal without Kubernetes. The README states Apache-2.0 licensing.
- **Requirements/limits:** a configured model and access to relevant toolsets/data. Its background operator mode runs in Kubernetes; this requirement should not be confused with the standalone investigation path. Integrations and capability claims were not tested.
- **Inference:** open source gives us a reference architecture, but neither removes model/inference dependencies nor demonstrates that the resulting diagnoses are reliable.

## O5. Original ITBench: reproducible research baseline

- **Source:** [ITBench paper, arXiv:2502.05352v1](https://arxiv.org/abs/2502.05352), Jha et al., IBM and University of Illinois, submitted **2025-02-07**.
- **Evidence:** "an initial set of 94 real-world scenarios" (abstract).
- **Research result:** that release reports 13.8% successful handling for SRE, 25.2% for compliance/security, and 0% for FinOps with the evaluated agents and models. These are **historical February 2025 results**, not a November 2026 capability ceiling. The paper's suite contains only two FinOps scenarios.
- **Reproducibility:** the original [ITBench repository](https://github.com/itbench-hub/ITBench) provides scenarios and baseline agents; repository execution was not attempted.
- **Inference:** evaluate outcomes against ground truth, not how convincing an explanation sounds. Do not compare these original resolution figures directly with the newer diagnosis metric below.

## O6. ITBench-AA: current diagnosis evaluation

- **Source:** [ITBench-AA benchmark and methodology](https://artificialanalysis.ai/evaluations/itbench-aa), Artificial Analysis; live leaderboard inspected **2026-11-20**. Launch context: [IBM research announcement](https://huggingface.co/blog/ibm-research/itbench-aa), **2026-05-27**.
- **Evidence:** "The headline score is the average precision at full recall" (Background).
- **Research result:** the inspected page lists GPT-5.6 Sol (Max) at **56.2%**, followed by Step 5 Preview at 55.6% and Gemini 3.8 Flash (High) at 52.5%.
- **Conditions:** 59 Kubernetes incident tasks, three repeats, an identical Stirrup harness, and **offline incident snapshots**. Forty tasks are public; 19 are held out. Missing any true root-cause entity yields zero for a repeat; extra entities reduce precision.
- **Limit:** this is neither a percentage of production incidents fixed nor a test of autonomous live remediation. The full held-out evaluation is not publicly reproducible. Secondary descriptions of live-system resolution misstate this implementation.

## Synthesis for the briefing

**Supported pattern:** commercial and open-source systems both join operational context with tool-using language models. The differentiation is increasingly about context coverage, evidence, access, integration, and outcome verification. This interpretation draws on O1-O4 rather than a market-share estimate.

**Example workflow:** an alert reports checkout failures; the assistant inspects recent changes, traces, logs, and configuration; it distinguishes a misconfigured upstream dependency from downstream symptoms; it produces a cited hypothesis and a bounded next step. A simple baseline is a fixed runbook or a rule that flags known configuration mistakes. Compare diagnosis accuracy, unsupported conclusions, time, and model/tool cost on the same scenarios.

**Problem areas to brainstorm (team hypotheses):** evidence-linked diagnosis for small VM deployments; explicit detection of missing/unsupported diagnostic inputs; replayable incident exercises with measurable correctness; a recommendation-to-fix loop that independently checks restored application behavior. These are opportunities to validate, not claims of absent competition.
