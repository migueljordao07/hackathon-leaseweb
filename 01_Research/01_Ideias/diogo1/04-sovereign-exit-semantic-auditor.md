# Sovereign Exit Semantic Auditor

> For **engineering teams migrating services off US hyperscalers to European or sovereign infrastructure**, we help **surface hidden semantic lock-in and verify behavioral parity before cutover** using **AI to jointly analyze IaC, application SDK usage, and sovereignty dependencies**, improving **pre-migration blocker detection and parity confidence on the target stack**.

**Proposed by:** Diogo (`diogo1`) · **Status:** Exploring
**Theme:** Migration & sovereignty
**Date:** 20 November 2026

## 1. Problem and user

- **Who encounters this, and when?** A platform engineer or technical lead evaluating or planning an exit from AWS (or another US hyperscaler) to a European cloud provider (such as Leaseweb, Scaleway, OVHcloud, or Hetzner) or self-hosted open-source infrastructure due to cost predictability or EU regulatory drivers (GDPR, NIS2, DORA, CLOUD Act exposure).
- **What goes wrong today?** Swapping raw compute or S3-compatible object storage is relatively straightforward, so early migration estimates miss deeper **semantic and sovereignty lock-in**: application code quietly depends on AWS-specific semantics (SQS visibility timeouts and DLQ redelivery behavior, DynamoDB conditional writes and atomic counters, Lambda event-source bindings, IAM role assumptions) or leaks telemetry/AI requests to non-EU endpoints. Teams discover these mismatches late during rewrite or cutover.
- **Current workaround:** Manual architecture audits, grep-based SDK searches, spreadsheets mapping cloud services to open-source equivalents, and bespoke migration prototypes written by hand.
- **Evidence and source:** Recurring Reddit practitioner discussions on `r/devops` (*"Moving away from AWS lambda/SQS/SNS/Aurora, worth it?"*), `r/BuyFromEU` (*"Moving to EU cloud from AWS"*; *"Don't get fooled by 'European Sovereign Cloud' offerings"*), and `r/aws` / `r/eutech` emphasize that true lock-in is architectural/semantic rather than syntactic and that sovereignty spans data, observability, identity, and management planes—not just region selection. See also the [team briefing](../../ai-cloud-infrastructure-team-briefing.md) on OpenTofu's translation limits and the [European Commission Cloud Sovereignty Framework](https://commission.europa.eu/document/download/09579818-64a6-4dd5-9577-446ab6219113_en). Reddit threads supply practitioner pain signals, not validated commercial demand; direct Reddit permalinks were retrieved through search redirects and remain to be verified in a browser.

## 2. Proposed solution and AI contribution

- **User workflow:** Point the tool at a repository containing IaC (Terraform/OpenTofu/config) and application source code → deterministic parsers extract provider resources, SDK calls, and outbound endpoints → AI maps cross-file **semantic dependencies** and **sovereignty exposures** to a target open-source/EU stack → generate a prioritized exit report, target scaffold (OpenTofu/Docker Compose + thin adapter), and behavioral contract tests → run parity checks locally against the disposable sovereign stack.
- **What AI adds:** Connects IaC declarations to how application code *actually uses* proprietary primitives (distinguishing trivial S3 `put_object` calls from subtle SQS visibility-timeout or DynamoDB `ConditionExpression` semantics), explains sovereignty gaps across data/AI/operational dimensions, and drafts targeted adapter scaffolds and parity test cases. Deterministic parsers establish inventory; deterministic contract tests decide behavioral parity.
- **Simple baseline:** A static regex/keyword inventory script listing `aws_*` Terraform resources and `boto3` imports paired with a static AWS-to-OSS replacement lookup table.
- **Action boundary:** Strictly read-only on the source repository. Generated scaffolds, adapters, and parity tests run exclusively against disposable local containers/services on the Linux VM. No cloud credentials, no live production AWS writes, and no automatic cloud cutover.

## 3. Existing alternatives and difference

| Alternative or workaround | What it already solves | Our specific difference |
|---|---|---|
| [Former2](https://github.com/iann0036/former2) / Terraformer | Reverse-engineers live AWS resources into AWS Terraform/CloudFormation syntax. | Proposed: targets *exiting* AWS by jointly inspecting IaC and application SDK semantics, not re-exporting AWS HCL. |
| [AWS Transform](https://docs.aws.amazon.com/transform/latest/userguide/transform-vmware-release-notes.html) | Commercial AI-assisted migration with inventory and IaC generation. | Proposed: provider-neutral exit *away* from hyperscalers toward European/open-source infrastructure (AWS Transform targets AWS as destination). |
| [OpenTofu](https://opentofu.org/docs/intro/) | Open-source declarative provisioning once target HCL is written. | Proposed: bridges the unautomated pre-OpenTofu gap—translating proprietary managed-service semantics and verifying behavioral parity before provisioning. |
| [LocalStack](https://docs.localstack.cloud/) | Local emulation of AWS APIs for testing AWS-coupled code. | Proposed: helps *decouple* from AWS APIs onto real open-source replacements (PostgreSQL, RabbitMQ/Valkey, MinIO) rather than emulating AWS indefinitely. |

**Why would this user choose our approach?** Hypothesis: no open-source tool currently audits both IaC and application code for hidden semantic and sovereignty lock-in while proving replacement behavior locally before a team commits engineering months to an exit. This differentiation is a hypothesis and remains unvalidated with external users.

## 4. Smallest working demo

**Demo story:** A European startup wants to move a small AWS-coupled order-processing service off AWS onto a sovereign Linux/open-source stack without breaking retry semantics or leaking customer telemetry outside the EU.

1. **Before:** Inspect a disposable Python microservice + Terraform fixture using S3, SQS (relying on visibility-timeout redelivery + DLQ), DynamoDB (`ConditionExpression` idempotency guard), and a hardcoded US telemetry/LLM endpoint. Show the non-AI grep/checklist baseline catching resource names while missing the conditional-write race condition, visibility-timeout behavior, and hidden non-EU endpoint.
2. **Intervention:** Run the Sovereign Exit Semantic Auditor. It produces an evidence-linked Semantic & Sovereignty Report (citing exact `.tf` and `.py` lines across European Commission sovereignty dimensions), maps services to local open-source equivalents (PostgreSQL JSONB, RabbitMQ or Redis/Valkey, local S3-compatible store), and generates a target adapter + contract test suite.
3. **After:** Run the live parity test harness on the Linux VM comparing a naive replacement (which fails on duplicate message redelivery / concurrent conditional write) against the semantics-aware sovereign adapter (which passes all parity checks and verifies zero non-EU outbound calls).

- **Must build:** (1) Deterministic repo/IaC/SDK/endpoint extractor; (2) AI semantic-lock-in & sovereignty analyzer generating structured mappings + adapter scaffold; (3) Local sovereign target fixture (`docker-compose` or local Linux processes) with automated parity contract tests.
- **Out of scope today:** Full multi-language AST support, live AWS account scraping, automated live data migration (DMS), Kubernetes multi-cluster orchestration, and legal/GDPR certification claims.
- **Success metric:** Proposed target: detect 100% of 5 seeded blockers (3 semantic + 2 sovereignty/egress) vs. <=40% for the static baseline, with zero fabricated file/line citations, and demonstrate a passing live parity test suite on the local sovereign target. These are acceptance targets, not measured results.
- **Failure case:** Unrecognized proprietary SDK patterns or ambiguous semantics are marked `manual_review_required` rather than silently emitting a broken adapter; model output failing schema or line-citation checks is rejected.
- **Demo fallback:** Resettable sample AWS-coupled repository + clearly labeled cached AI analysis JSON, while deterministic extraction, sovereignty checks, and live parity contract tests always execute live on the VM.

## 5. Feasibility on the supplied Linux VM

| Dependency | Proposed approach | Available / Unverified / Blocked |
|---|---|---|
| Data and telemetry | Synthetic AWS-coupled sample microservice (`.tf` + Python + config) with seeded semantic & sovereignty traps | Unverified: fixtures must be authored. |
| Model and inference | 1–2 structured LLM calls (semantic audit + adapter/test generation); optional local fallback note | Unverified: API key, latency, and budget (also note sovereignty paradox if calling a non-EU LLM API—explicitly document in demo). |
| Infrastructure and permissions | Local Linux VM running Python + PostgreSQL/SQLite + Redis/Valkey/RabbitMQ (containers optional) | Unverified: VM CPU/RAM, Docker availability, package install rights. |
| Libraries and integrations | Python standard library, `python-hcl2` (or lightweight HCL parser), `pytest`, FastAPI/HTML report UI; open-source licenses checked before adding | Unverified: installability on VM and license audit. |

**Rough effort and split:** Medium relative effort. Suggested split: sample AWS-coupled repo & seeded traps; deterministic extractor & sovereignty checker; AI semantic analyzer; local sovereign stack & parity harness; web/CLI report & pitch. Hardest integration: making the live parity failure between a naive swap and a semantics-aware adapter crystal clear inside a 5-minute demo. Owners unassigned.
**Biggest blocker:** Over-scoping the target services; keeping the MVP strictly focused on 2–3 iconic AWS primitives (SQS + DynamoDB + S3/egress) is critical to finish cleanly in one day.

Keep API keys in local `.env` out of Git. Explicitly note that sending source code to a remote non-EU model would itself touch a sovereignty dimension, so the architecture should support an EU-hosted or local model endpoint.

## 6. Fastest validation

- **Riskiest assumption:** The AI reliably distinguishes deep semantic dependencies (e.g., conditional writes, visibility timeout) from shallow API calls without hallucinating non-existent lock-in or missing real traps.
- **Quick experiment:** Author one 150-line Python + Terraform fixture with 5 known traps (3 semantic, 2 sovereignty) and 2 red herrings (portable S3 calls). Run both the static regex baseline and one structured LLM prompt over the extracted snippets; score precision, recall, and citation accuracy.
- **Continue if:** The AI catches semantic traps the static baseline misses with verifiable line citations and produces a valid parity test diff.
- **Simplify or park if:** It only restates a static AWS-to-OSS lookup table or hallucinates unsupported semantics; in that case narrow strictly to deterministic sovereignty egress auditing or pick another candidate.

## 7. Team decision

Provisional AI assessment against the [official criteria](../../../00_Context/challenge-and-guidelines.md); discussion aid only, not a team vote or jury prediction.

| Criterion | Score | Reason |
|---|---|---|
| Innovation | 4 | Directly tackles an unimplemented gap (semantic + sovereignty exit auditing with parity tests) rather than syntax-only IaC conversion. |
| Applicability | 4 | High strategic relevance to European teams and Leaseweb's sovereign cloud theme; real-world customer demand remains unvalidated. |
| Technical complexity and quality | 4 | Combines static IaC/AST extraction, semantic AI mapping, sovereignty scoring, and live parity verification. |
| Presentation and clarity | 5 | Compelling 5-minute arc: "Why naive cloud exit fails" → live parity failure → verified sovereign pass. |
| **Total** | **17/20** | Strongest direct fit with the sovereignty theme; scope discipline is essential. |

**Decision:** Shortlist candidate for quick validation experiment.
**Reason and next action:** Test the 150-line AWS fixture against the regex baseline and one structured model call before committing full build time; owner unassigned.
