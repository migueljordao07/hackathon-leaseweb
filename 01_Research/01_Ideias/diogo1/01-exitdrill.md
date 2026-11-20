# ExitDrill

> For **teams that depend on a US hyperscaler and must prove they could leave it**, we help **turn a paper exit plan into a tested exit to a European provider** using **AI to translate AWS infrastructure into an equivalent Leaseweb/open-source stack, run it, and document the evidence**, improving **the share of exit plans backed by an executed, timed test**.

**Proposed by:** Diogo (AI-assisted research) · **Status:** Exploring
**Theme:** Migration & sovereignty / AI-assisted operations
**Date:** 20 November 2026

## 1. Problem and user

- **Who encounters this, and when?** A platform or compliance lead at an EU company running on AWS who must show an auditor, regulator, or board that the company can actually leave its provider (DORA Art. 28(8) for financial entities; Data Act switching rights for everyone).
- **What goes wrong today?** The exit plan is a PDF that has never been executed. Nobody knows whether the workload would really start on another provider, which managed services block the move, or how long it would take.
- **Current workaround:** Consultancy engagements, manual rebuilds by senior engineers, or a lock-in score that stops at diagnosis.
- **Evidence and source:**
  - Community signal: Reddit threads about moving workloads off AWS, e.g. [r/hetzner: Transfer project from AWS to Hetzner](https://www.reddit.com/r/hetzner/comments/1eb4y94/transfer_project_from_aws_to_hetzner/), and backlash when a European company moved processing to AWS ([r/BuyFromEU: DeepL is shifting to AWS for processing](https://www.reddit.com/r/BuyFromEU/comments/1ry1irp/deepl_is_shifting_to_aws_for_processing/)). Read via search results and mirrors; verify the threads before quoting them in the pitch.
  - Practitioner write-up: [Show HN: We moved from AWS to Hetzner, saved 90%, kept ISO 27001](https://news.ycombinator.com/item?id=44335920).
  - Regulation: DORA requires exit plans that are documented and sufficiently tested ([Orbiq DORA exit template, Art. 28(8)](https://www.orbiqhq.com/templates/dora-exit-strategy-plan)); the EU Data Act bans switching charges, including migration egress, from 12 January 2027.
  - Untested assumption: buyers will value an automated drill over a consultant-led one.

## 2. Proposed solution and AI contribution

- **User workflow:** Upload a Terraform project (AWS) → inventory and lock-in score per resource → AI maps each resource to a Leaseweb or open-source equivalent and generates target IaC (Docker Compose + Leaseweb Terraform) → run the drill on a disposable target → automated smoke tests → tear down → exit report with timestamps and test evidence.
- **What AI adds:** Translating proprietary patterns that rules cannot cover (e.g. Lambda + DynamoDB + SQS into containers, Postgres, and a message broker), writing the migration notes, and drafting the exit plan narrative. A small local model sanitises secrets, account IDs, and IPs before anything is sent to a larger model.
- **Simple baseline:** A static lookup table (AWS resource type → equivalent) plus a hand-written Compose file and a manual checklist.
- **Action boundary:** Reads IaC only; never touches the source AWS account. Deploys only to a disposable target with fixture data. Generated IaC must pass `terraform validate` / `docker compose config` before it runs. Pass/fail is decided by deterministic probes, not by the model.

## 3. Existing alternatives and difference

| Alternative or workaround | What it already solves | Our specific difference |
|---|---|---|
| [EscapeCloud](https://www.getapp.com/finance-accounting-software/a/escapecloud/) (commercial) | Exit-readiness score, dependency inventory, regulatory reports | Diagnosis only; we execute and test the exit. |
| [eu-cloud-mcp](https://github.com/moveinfra/eu-cloud-mcp) (Apache-2.0) | Terraform lock-in scan, EU alternatives (UpCloud, Scaleway, Hetzner, OVH), price and egress estimates | Read-only, no code generation, no Leaseweb. Cite as related work; do not fork (we start from scratch). |
| [Cloudnovi](https://cloudnovi.com/sovereign-cloud/), [Deloitte + DEEP](https://www.deep.eu/en/ressources/articles-blog/cloud/actualites/exit-strategy) | Human-led exit tests and exit-as-a-service | Manual consulting; we automate the drill and make it repeatable. |
| [Codekeeper DORA Evidence Pack](https://codekeeper.co/solutions/dora-evidence-pack) | Builds escrowed supplier software and certifies it runs | Covers supplier software in escrow, not your own cloud infrastructure. |
| [Qovery](https://www.qovery.com/blog/sovereign-cloud-migration-7-tests-before-you-trust-it) | Advocates a timed exit drill; platform keeps portability testable | Their own platform; ours is open source and targets Leaseweb APIs. |
| [Firefly cloud migration codification](https://www.firefly.ai/blog/revolutionizing-cloud-migration-with-fireflys-innovative-iac-generation) (commercial), [StackGen migration engine](https://devops.com/stackgens-new-migration-engine-a-devops-game-changer-for-multi-cloud-transitions/) (commercial) | AI-assisted translation of cloud resources/IaC between providers | Translation already exists for AWS/Azure/GCP; no European/Leaseweb target, no executed drill, no exit evidence. Our AI translation step is not novel on its own. |
| [Qovery Migration AI Agent](https://github.com/qovery/qovery-migration-ai-agent) (open source) | Generates Terraform with an LLM to move Heroku/Render apps to AWS, GCP, Azure, or Scaleway | Different source (PaaS) and targets; no drill or evidence. |

**Why would this user choose our approach?** Hypothesis: it produces evidence (a passed drill) in minutes instead of weeks of consulting, and it is the only option found that targets Leaseweb. No exhaustive market review was done.

## 4. Smallest working demo

**Demo story:** A fintech running a small AWS app (EC2 + RDS Postgres + S3 + SQS) needs DORA exit evidence.

1. **Before:** Show the AWS Terraform and an untested exit-plan PDF; the lock-in score highlights SQS and RDS.
2. **Intervention:** ExitDrill generates the Leaseweb/open-source stack (app container, Postgres, MinIO, RabbitMQ), shows which parts were mapped by rules and which by AI, and runs the drill.
3. **After:** Independent probes confirm the app responds, data is present in Postgres and MinIO, and a queue message is processed. The report lists timings, test results, and remaining manual steps.

- **Must build:** (1) IaC parser + mapping catalogue + score; (2) AI generator with local sanitiser and validation; (3) drill runner (deploy, probes, teardown) + report.
- **Out of scope today:** Real production data migration, DNS cutover, multi-region, live AWS account access.
- **Success metric:** Target: the drill passes end-to-end for the sample app in under 10 minutes; at least 80% of resources mapped by catalogue or AI with validated output. These are goals, not measurements.
- **Failure case:** Unmappable resources are listed as manual steps; a failed probe marks the drill as failed with logs, never as "exit ready".
- **Demo fallback:** Pre-generated IaC and a recorded drill run, clearly labelled as replay; probes run live if the target is reachable.

## 5. Feasibility on the supplied Linux VM

| Dependency | Proposed approach | Available / Unverified / Blocked |
|---|---|---|
| Data and telemetry | Synthetic sample app and fixture data written by us | Unverified: sample app must be built. |
| Model and inference | Mistral API (EU) for translation; small local model via Ollama for sanitising, if RAM allows | Unverified: API key, free-tier limits (free tier may train on inputs, so synthetic data only), VM RAM. |
| Infrastructure and permissions | Docker on the VM as drill target; optional Leaseweb Public Cloud via [Terraform provider](https://github.com/leaseweb/terraform-provider-leaseweb) or [EC2-compatible API](https://developer.leaseweb.com/api-docs/awsec2wrapper_v1.html) | Unverified: Docker rights; Leaseweb API key (ask mentors). |
| Libraries and integrations | Python, python-hcl2, Streamlit, Docker Compose, OpenTofu/Terraform | Unverified: install on VM; all permissive licences. |

**Rough effort and split:** Parser/catalogue, AI generator + sanitiser, drill runner, UI + report, sample app + pitch. Hardest integration: making AI-generated IaC run reliably on the first try.
**Biggest blocker:** No Leaseweb API access; fallback is the VM as target, which still makes the drill real.

Keep credentials out of this file. Confirm API access separately from chat subscriptions or VM login access.

## 6. Fastest validation

- **Riskiest assumption:** AI-generated target IaC for a small but realistic AWS app runs and passes probes with little manual fixing.
- **Quick experiment:** Hand the sample Terraform to the model with the mapping catalogue; check whether the generated Compose file starts and passes three probes within 30 minutes.
- **Continue if:** The generated stack starts and passes probes with at most one manual fix.
- **Simplify or park if:** Generation is unreliable; fall back to catalogue-only mapping for a fixed resource set and use AI only for the report and explanations.

## 7. Team decision

Initial AI-assisted assessment against the [official criteria](../../../00_Context/challenge-and-guidelines.md); provisional, not a team vote.

| Criterion | Score | Reason |
|---|---|---|
| Innovation | 4 | Assessment and cross-cloud IaC translation exist; an automated, executed, open-source drill to a European target with exit evidence was not found. |
| Applicability | 5 | Regulatory pull (DORA, Data Act deadline) and direct fit with Leaseweb's sovereignty positioning. |
| Technical complexity and quality | 4 | IaC parsing, AI generation with validation, real deployment and probes. |
| Presentation and clarity | 4 | "From PDF to passed drill" is a clear five-minute story. |
| **Total** | **17/20** | |

**Decision:** Explore  
**Reason and next action:** Ask Leaseweb mentors whether exit/migration evidence is a real customer request and whether an API key is available; owner unassigned.
