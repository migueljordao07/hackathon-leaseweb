# CloudShrink: Autonomous FinOps & Zombie Resource Remediator

> For **cloud platform and DevOps engineers**, we help **identify and safely eliminate unattached storage, idle compute, and runaway NAT egress costs** using **AI-driven usage pattern analysis and human-in-the-loop remediation PRs**, improving **cloud cost efficiency without risk of breaking production workloads**.

**Proposed by:** Team · **Status:** Exploring  
**Theme:** AI-assisted operations

## 1. Problem and user

- **Who encounters this, and when?** DevOps engineers, SREs, and engineering managers running workloads across AWS, GCP, or multi-cloud environments where microservices, CI/CD runners, and temporary environments leave behind unattached persistent disks (EBS/PD), idle load balancers, and unmonitored cross-AZ NAT Gateway traffic.
- **What goes wrong today?** Millions of dollars are spent annually on "zombie resources" that generate invoices without providing any business value. Traditional FinOps dashboards (e.g. AWS Cost Explorer, Datadog) generate passive reports and graphs, but nobody has the time to manually track down owner tags, verify whether a volume is safe to delete, and write the Terraform code to clean it up.
- **Current workaround:** Periodic "cost-saving sprint" spreadsheets where engineers manually cross-reference cloud billing CSVs with active instances, or relying on aggressive cron scripts that occasionally delete critical unmounted data volumes by mistake.
- **Evidence:** FinOps Foundation research consistently highlights idle compute and unattached storage as top areas of cloud waste. Google Cloud Compute Engine documentation notes that standard recommendations rely strictly on static 8-day moving averages and struggle with intermittent peak workloads, leading engineers to ignore them.

## 2. Proposed solution and AI contribution

- **User workflow:** CloudShrink connects to cloud telemetry / billing logs (or parses an inventory report) $\rightarrow$ AI agent identifies unused or oversized resources, checks I/O history and dependency graphs $\rightarrow$ Generates an actionable natural language explanation with an executable Git pull request or CLI command to terminate/archive the resource safely.
- **What AI adds:** Contextual safety verification. Instead of a dumb threshold script that deletes any unattached volume after 7 days, the LLM analyzes naming conventions, last attached snapshots, CloudTrail logs, and related IaC files to explain *why* the resource exists (e.g., "This volume was detached from `staging-db-02` 14 days ago after a failed migration and has had 0 IOPS since") and generates the precise cleanup code.
- **Simple baseline:** A bash/python script querying AWS CLI `describe-volumes --filters Name=status,Values=available` and deleting them after X days.
- **Action boundary:** Read-only access to metrics and resource state; recommends actions and generates Git pull requests or staging scripts. Destructive actions require explicit human-in-the-loop confirmation.

## 3. Existing alternatives and difference

| Alternative or workaround | What it already solves | Our specific difference |
|---|---|---|
| AWS Cost Explorer / GCP Recommender | Flags underutilized EC2 instances and idle disks based on basic threshold heuristics | Passive dashboards require manual investigation; CloudShrink verifies context and outputs ready-to-merge Git/IaC pull requests. |
| Cloud Custodian | Open-source rule engine running scheduled YAML policies to filter and terminate resources | Requires writing and maintaining complex policy YAMLs; CloudShrink uses natural language reasoning and contextual awareness to prevent false-positive deletions. |

**Why would this user choose our approach?** Turns passive cost charts into safe, one-click automated cleanup actions with zero risk of deleting vital enterprise data.

## 4. Smallest working demo

**Demo story:** An engineer runs CloudShrink against an environment with 3 simulated zombie resources (an unattached 500GB SSD volume, an idle test VM, and an orphaned NAT Gateway route). CloudShrink analyzes the usage telemetry, explains the monthly waste in euros, and produces a cleanup script and Terraform diff that the operator approves with one keystroke.

1. **Before:** Cloud environment is incurring €420/month in idle resources. Dashboards show raw metrics but no clear action plan.
2. **Intervention:** Execute `cloudshrink scan --fixtures ./telemetry-sample/`. The AI agent correlates IOPS, network bytes, and tags, highlighting 3 safe-to-prune resources with high confidence.
3. **After:** CloudShrink outputs a clear impact summary ("Deleting these 3 resources saves €420/mo with 0% production risk") and generates the exact `terraform destroy` target commands or IaC diff.

- **Must build:**
  1. Telemetry ingestion engine (processing simulated AWS/GCP resource lists with IOPS, CPU, and network metrics).
  2. Contextual safety verification prompt engine.
  3. Interactive terminal / web UI with one-click approval to generate the remediation patch.
- **Out of scope today:** Live multi-cloud AWS/Azure API billing sync; automated snapshot archival to cold Glacier storage.
- **Success metric:** Accurately identifies 100% of zombie resources in test dataset with 0 false positives on legitimate backup volumes; generates valid remediation actions in < 10 seconds.
- **Failure case:** If confidence is low or telemetry is incomplete, the agent explicitly marks the resource as "Manual Review Required" and refuses to generate auto-deletion commands.
- **Demo fallback:** Pre-computed billing telemetry fixtures with deterministic agent outputs.

## 5. Feasibility on the supplied Linux VM

| Dependency | Proposed approach | Available / Unverified / Blocked |
|---|---|---|
| Data and telemetry | Synthetic JSON/CSV telemetry fixtures (disk IOPS, CPU history, network throughput) | Available |
| Model and inference | OpenAI / Anthropic API or local model on VM | Available |
| Infrastructure and permissions | Linux VM running Python 3.10+ | Available |
| Libraries and integrations | `pydantic`, `pandas`, `rich`, `fastapi` (optional UI) | Available (open-source) |

**Rough effort and split:**
- Telemetry simulation & data pipeline: 2 people (Francisco & Diogo)
- LLM reasoning & safety guardrails: 1 person (Miguel)
- CLI/Web dashboard & pitch demo: 2 people (Carolina & Ricardo)
- Hardest integration: Fine-tuning the prompt guardrails so the agent never marks an active disaster recovery snapshot or database replica as a zombie.

**Biggest blocker:** Hallucination of resource safety if telemetry data is sparse.

## 6. Fastest validation

- **Riskiest assumption:** That LLM safety reasoning can effectively distinguish between a temporary idle backup disk and an abandoned zombie volume.
- **Quick experiment:** Provide an LLM with 5 resource metadata snippets (2 active DR volumes with low IOPS, 3 truly abandoned volumes) and verify if it correctly flags the difference.
- **Continue if:** Model achieves 100% accuracy on differentiating DR volumes from abandoned volumes based on metadata and tags.
- **Simplify or park if:** Model fails to distinguish DR volumes, leading to unacceptable risk of data loss.

## 7. Team decision

| Criterion | Score | Reason |
|---|---|---|
| Innovation | 3.5/5 | FinOps is an established domain, but autonomous safe remediation is still cutting-edge. |
| Applicability | 5/5 | Every cloud user suffers from cloud bill shock and idle waste. |
| Technical complexity and quality | 3.5/5 | Solid data analysis and safety guardrails, though architecturally simpler than AST transpilation. |
| Presentation and clarity | 4.5/5 | "We saved €420 in 30 seconds" is universally understood by any judge. |
| **Total** | **16.5/20** | |

**Decision:** Shortlist  
**Reason and next action:** Great fallback if IaC transpilation proves too intricate; high applicability and intuitive pitch demo.
