# SovereignGuard: Cloud Sovereignty & GDPR IaC Auditing Agent

> For **European DevOps and compliance engineers**, we help **detect extraterritorial data exposure and non-sovereign dependencies in cloud configurations** using **contextual AI reasoning over Infrastructure-as-Code and data sovereignty policies**, improving **GDPR, EU Data Act, and DORA audit readiness while preventing vendor lock-in**.

**Proposed by:** Team · **Status:** Exploring  
**Theme:** Migration & sovereignty

## 1. Problem and user

- **Who encounters this, and when?** European DevOps engineers, cloud architects, and Data Protection Officers (DPOs) deploying infrastructure on AWS, Azure, or GCP under strict EU regulatory regimes (GDPR, EU Data Act, Schrems II, DORA, NIS2).
- **What goes wrong today?** Developers routinely provision resources (S3 buckets, Azure Blobs, BigQuery datasets, cross-region replication, CDN edge distributions) with configurations that route, replicate, or process EU personal data through infrastructure subject to the US CLOUD Act or hosted in non-EU jurisdictions without realizing the legal and technical blast radius.
- **Current workaround:** Manual spreadsheet compliance checklists, static linting rules (e.g. checkov / trivy regexes for regions), or expensive external legal/security audits conducted weeks after code has reached production.
- **Evidence:** European Commission Cloud Sovereignty Framework (v1.2.1, Oct 2025) emphasizes that EU data location alone is insufficient; data control, operational autonomy, and provider jurisdiction matter. The EU Data Act (2024–2027) mandates removing switching barriers, but operational lock-in and extraterritorial jurisdiction risks remain critical enterprise concerns.

## 2. Proposed solution and AI contribution

- **User workflow:** Developer submits a Terraform / OpenTofu configuration directory or pull request $\rightarrow$ SovereignGuard inspects the HCL code, resource locations, telemetry endpoints, and replication targets $\rightarrow$ AI generates a Sovereignty & GDPR Scorecard, highlights extraterritorial risks (e.g. US CLOUD Act exposure, US-managed KMS keys, unencrypted cross-border transit), and produces an executable remediation patch replacing proprietary services with European sovereign alternatives (e.g., Leaseweb S3-compatible storage or European compute).
- **What AI adds:** Contextual reasoning over complex IaC graphs that static linters miss—such as determining whether a specific data pipeline processes PII, correlating secondary replication targets with regulatory jurisdictions, and translating proprietary hyperscaler configurations into compliant European provider equivalents.
- **Simple baseline:** A deterministic Checkov or regex rule matching `region != "eu-west-1"` or grep for forbidden AWS services.
- **Action boundary:** Read-only inspection of IaC files; outputs audit reports and suggested Git patches (diffs). Does not deploy or modify live infrastructure without explicit human approval.

## 3. Existing alternatives and difference

| Alternative or workaround | What it already solves | Our specific difference |
|---|---|---|
| Trivy / Checkov / tfsec | Static regex and AST rule matching for known security misconfigurations and CVEs | Identifies geopolitical jurisdiction risks, US CLOUD Act exposure, and suggests direct code migration to European sovereign clouds (e.g. Leaseweb). |
| Cloud Health / CSPM tools (Wiz, Prisma) | Runtime cloud posture scanning and vulnerability alerting | Pre-deployment IaC focus with automated generative patching to sovereign European equivalents; runs locally without sending enterprise code to third-party US SaaS. |

**Why would this user choose our approach?** Developers get an immediate pre-commit audit showing exactly why their Terraform violates EU sovereignty rules along with an automated patch to deploy on a sovereign European provider.

## 4. Smallest working demo

**Demo story:** An engineer attempts to deploy an AWS Terraform stack that stores customer logs in a US-replicated S3 bucket using default AWS KMS keys. SovereignGuard audits the stack, explains the Schrems II / CLOUD Act violation, and outputs a clean Git diff targeting a European sovereign cloud setup (Leaseweb S3 / EU OpenStack).

1. **Before:** Run `sovereign-guard audit ./terraform-sample/` on an AWS configuration containing a US-replicated bucket and US-based telemetry logging. Shows "NON-COMPLIANT: High Extraterritoriality Risk".
2. **Intervention:** The AI agent analyzes the resource dependencies, explains why the configuration violates sovereignty requirements, and drafts a remediation plan.
3. **After:** Agent outputs a `sovereignty-remediation.patch` that refactors the Terraform code into an EU-sovereign configuration (using European regions and S3-compatible endpoints on Leaseweb/MinIO). Re-running the audit yields 100% Sovereign Compliance.

- **Must build:**
  1. HCL parser / extractor that extracts provider, region, storage, and networking configurations.
  2. Sovereignty evaluation engine with LLM prompting grounded in the EU Cloud Sovereignty Framework.
  3. Patch generator that produces valid Terraform/OpenTofu code for sovereign EU targets.
- **Out of scope today:** Full live AWS account scanning via API; runtime data packet inspection; multi-tenant web portal.
- **Success metric:** 100% detection of seeded extraterritorial configurations in 3 sample Terraform modules; valid, syntactically clean HCL patch generated in < 15 seconds.
- **Failure case:** If LLM inference fails or returns invalid HCL, fall back to a deterministic rules-based sovereignty report and display raw detected policy violations.
- **Demo fallback:** Pre-recorded input files and cached local model responses ready to demonstrate offline.

## 5. Feasibility on the supplied Linux VM

| Dependency | Proposed approach | Available / Unverified / Blocked |
|---|---|---|
| Data and telemetry | Synthetic Terraform files (AWS S3, RDS, CloudFront with known non-sovereign configs) | Available (fixtures created locally) |
| Model and inference | External LLM API (Claude 3.5 Sonnet / OpenAI GPT-4o / Gemini) via API key, or local Ollama fallback | Available via team AI subscriptions / local Ollama |
| Infrastructure and permissions | Linux VM (Docker, Python 3.10+, OpenTofu/Terraform CLI installed) | Available on Leaseweb VM |
| Libraries and integrations | `python-hcl2`, `pydantic`, `rich` (CLI terminal formatting) | Available (open-source, PyPI) |

**Rough effort and split:** 
- Parser & synthetic fixtures: 1 person (Diogo/Ricardo)
- Prompt engineering & sovereignty scoring engine: 1 person (Miguel/Francisco)
- CLI / demo presentation interface: 1 person (Carolina)
- Hardest integration: Ensuring generated Terraform patches are syntactically valid and pass `tofu validate`.

**Biggest blocker:** Latency or connectivity issues with external LLM API endpoints during live demo.

## 6. Fastest validation

- **Riskiest assumption:** That LLM can reliably generate syntactically correct HCL patches rather than hallucinating provider parameters.
- **Quick experiment:** Test prompting Claude/GPT with an AWS S3 Terraform snippet to generate a Leaseweb/S3-compatible equivalent and validate with `terraform validate`.
- **Continue if:** Output passes `tofu validate` without manual syntax edits.
- **Simplify or park if:** Model produces persistent hallucinated attributes that break IaC parsing; fallback to reporting violations without auto-patching.

## 7. Team decision

| Criterion | Score | Reason |
|---|---|---|
| Innovation | 4/5 | Combines IaC security scanning with geopolitical sovereignty and GDPR compliance. |
| Applicability | 5/5 | High priority for European public sector, healthcare, and finance seeking hyperscaler independence. |
| Technical complexity and quality | 4/5 | AST parsing, multi-step LLM reasoning, and automated code generation/validation. |
| Presentation and clarity | 5/5 | Extremely clear problem, relatable "before vs after" story, strong alignment with Leaseweb and EU themes. |
| **Total** | **18/20** | |

**Decision:** Shortlist  
**Reason and next action:** High alignment with the Leaseweb hackathon theme; build a 3-file Terraform test fixture to validate HCL translation.
