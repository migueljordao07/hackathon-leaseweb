# Migration, Portability, Sovereignty, and Leaseweb: Research Notes

Snapshot and access date: 20 November 2026. Primary sources only. These notes support the team briefing; proposed gaps and demo implications are research inferences, not validated customer demand. No infrastructure or model API was called.

## M1. Commercial AI migration: launch and maturity

- **Source:** [AWS Transform for VMware is now generally available](https://aws.amazon.com/about-aws/whats-new/2025/05/aws-transform-vmware-generally-available/).
- **Publication:** 15 May 2025. **Classification:** verified GA announcement; performance figures are vendor claims.
- **Evidence:** "now generally available" (opening paragraph; 3 quoted words).
- **Capability:** AI-assisted discovery, dependency mapping, network translation, migration planning, and EC2 optimization for VMware migration to AWS. Human review is part of the documented workflow.
- **Evaluation limitation:** AWS reports migration-wave planning for 500 VMs in 15 minutes and network translation up to 80 times faster; these are AWS's tests, not independent comparative measurements. Avoid presenting them as expected customer outcomes.
- **Inputs/dependencies:** source environment inventory and migration context; an AWS destination and its execution permissions are required for actual migration. This announcement does not establish a provider-neutral migration tool.

## M2. Commercial AI migration: changes through October 2026

- **Source:** [AWS Transform migration release notes](https://docs.aws.amazon.com/transform/latest/userguide/transform-vmware-release-notes.html).
- **Dates:** July and October 2026 entries. No later entries are used. **Classification:** documented capabilities, not measured outcomes.
- **Evidence:** "including VMware, Hyper-V, and other platforms" (July 2026; 8 quoted words).
- **Capability:** July broadens supported sources to virtual and bare-metal environments. October adds network generation from discovered inventory/connections and IaC-only landing-zone output when using a Delegated Administrator connector.
- **Boundary:** source diversity does not imply destination neutrality: the surrounding release notes remain about AWS landing zones, VPCs, EC2, and AWS storage targets.
- **Inputs/dependencies:** inventory and connection data, AWS account connectors, permissions, and region support. Generated artifacts still require review and deployment. No independent speed or correctness evaluation was found in these notes.

## M3. Open-source alternative: deterministic infrastructure management

- **Source:** [OpenTofu: getting started](https://opentofu.org/docs/intro/).
- **Date:** undated living documentation, accessed at snapshot. The exact release date of each documented detail is not established; no latest-version claim is made.
- **Evidence:** "Write" / "Plan" / "Apply" (core workflow; 3 quoted words total).
- **Capability:** declarative infrastructure configurations, provider plugins calling service APIs, plans describing proposed changes, and state tracking. This is a non-AI automation baseline.
- **Boundary:** a common orchestration workflow does not make provider APIs or managed services equivalent. Changing an IaC engine is different from replacing AWS-specific resources with another provider's resources; this is an inference from the provider-based architecture.
- **Inputs/dependencies:** CLI, configurations, provider plugins, state/backend access, and credentials to managed services. A plan shows intended infrastructure changes; it is not evidence of application-level migration correctness.

## M4. OpenTofu license verification

- **Source:** [OpenTofu repository LICENSE](https://raw.githubusercontent.com/opentofu/opentofu/main/LICENSE).
- **Date:** undated current repository file, accessed at snapshot; no commit-pinned historical assertion.
- **Evidence:** "Mozilla Public License, version 2.0" (license header; 6 quoted words).
- **Finding:** OpenTofu's source license is MPL-2.0, rather than assuming every infrastructure project uses Apache-2.0. This verification concerns the tool itself; providers, modules, container images, and bundled dependencies need their own license checks if selected for implementation. No legal compatibility conclusion is drawn here.

## M5. Leaseweb interfaces and access boundary

- **Source:** [Leaseweb API documentation](https://developer.leaseweb.com/docs/).
- **Date:** undated living reference, accessed at snapshot; exact introduction dates are not established. **Classification:** documented API surface, not tested event access.
- **Evidence:** "Get instance CPU metrics" (Public Cloud section; 4 quoted words).
- **Capability:** Public Cloud instance lifecycle endpoints and CPU metrics; the latter accepts instance ID, date range, and granularity. Authentication uses a Customer Portal-generated API key in `X-LSW-Auth`. The reference also labels the AWS-compatible Public Cloud interface beta and old GP VPS listing endpoints deprecated.
- **Boundary:** receiving Linux/SSH access to the hackathon VM does not establish access to the owning Leaseweb account, API credentials, product family, or resource permissions. This is an inference from the separate authentication requirements. Do not assume API CPU metrics or extra VM creation are available to the team.
- **Demo implication:** local OS/application telemetry can be the initial data source; a provider adapter is optional after actual access is confirmed.

## M6. Sovereignty is multidimensional

- **Source:** [European Commission Cloud Sovereignty Framework, version 1.2.1](https://commission.europa.eu/document/download/09579818-64a6-4dd5-9577-446ab6219113_en?filename=Cloud-Sovereignty-Framework.pdfben).
- **Publication:** October 2025; pages 2-3, objectives SOV-3, SOV-4, and SOV-6. This is a versioned procurement framework, not a claim that it is the latest legal requirement.
- **Evidence:** "the degree of autonomy customers retain over AI capabilities" (SOV-3; 10 quoted words).
- **Finding:** the framework distinguishes data/AI control, operational autonomy, supply-chain dependencies, and openness/interoperability of the technology stack. Thus EU data location alone does not establish all dimensions of sovereignty. For this briefing, assess where telemetry and prompts go, who operates the system, whether workloads can move, and which model/service dependencies remain.
- **Boundary:** this source supplies technical evaluation dimensions; it does not certify a provider or this prospective prototype.

## Evidence-backed problem areas to investigate

1. **Exit-readiness visibility.** Operators may need a comprehensible dependency and incompatibility report before moving a small workload to an alternative provider. M1-M2 show substantial AI investment in migration toward AWS; M3 shows that infrastructure tooling still exposes provider-specific resources. A provider-neutral explanation and validation workflow is a plausible gap, not proof that no competitor exists.
2. **Migration correctness.** Generated configuration and a successful infrastructure plan do not by themselves prove that the moved application preserves behavior. A small inventory/configuration translation followed by fixed functional tests could expose this distinction. Compare against a manual compatibility checklist; measure unsupported dependencies detected and tests passed, rather than announce a fully automated cloud exit.
3. **Sovereignty dependency visibility.** A locally hosted assistant can still send logs to an external model API. M6 suggests a concrete inventory of processing locations, operational dependencies, and replaceable components. An explainable dependency map is feasible to explore; a sovereignty/compliance certification is outside the evidence and demo scope.

## Practical handoff

Use a synthetic application inventory and a small, disclosed set of configurations if real account access is unavailable. A demo could inspect inputs, explain one incompatibility, propose an artifact, and validate its effect locally. Keep supported source/target scope explicit. Confirm VM CPU/RAM, package installation rights, outbound network access, model access, and any Leaseweb API permissions before choosing deployment dependencies. No VM specifications or actual permissions were established by this research.
