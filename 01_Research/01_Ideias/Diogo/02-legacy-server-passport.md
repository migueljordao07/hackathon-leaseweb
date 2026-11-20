# Legacy Server Passport

> For **engineers who inherit an undocumented server**, we help **understand what it really does, who depends on it, and whether it can be rebuilt** using **AI to interpret runtime evidence (processes, sockets, cron jobs, configs, logs) and generate a verified rebuild**, reducing **"scream tests" and surprises during migration or cleanup**.

**Proposed by:** Diogo (AI-assisted research) · **Status:** Exploring
**Theme:** AI-assisted operations / Migration & sovereignty
**Date:** 20 November 2026

## 1. Problem and user

- **Who encounters this, and when?** A sysadmin or platform engineer who takes over a "pet" server after the previous admin left, or who must migrate a legacy dedicated server to a new platform.
- **What goes wrong today?** Nobody knows what the box does. Turning a service off to see who complains (the "scream test") breaks something critical, e.g. a forgotten job that generates invoices or payroll.
- **Current workaround:** Manual archaeology with `ss`, `systemctl`, `crontab -l`, reading configs, asking around, and the scream test.
- **Evidence and source:**
  - Community signal: r/devops posts about inheriting undocumented environments and the "oh right, you also need to do X" knowledge that never reaches the docs, seen via the [r_devops Telegram mirror](https://t.me/s/r_devops/31865) and [another mirror page](https://t.me/s/r_devops/31843). Verify the original Reddit threads before quoting them.
  - Stories of the scream test breaking payroll after an unattended server was unplugged ([Server Fault: How can you tell what a server actually does?](https://serverfault.com/questions/697638/how-can-you-tell-what-a-server-actually-does)), and of an 11-year-old billing script disabled during "cleanup" ([legacy archaeology notes](https://grokdatum.github.io/grokdevops-wiki/library/topics/legacy-archaeology/street_ops)).
  - Untested assumption: Leaseweb has many dedicated-server customers with this problem when moving to cloud.

## 2. Proposed solution and AI contribution

- **User workflow:** Run a read-only collector on the server → upload the evidence bundle → AI produces a "passport": purpose of each service, inbound dependents (who connects to it), outbound dependencies, what each cron job and script does, risks (EOL OS, expiring certs, plaintext secrets) and a do-not-touch list → generate a containerised rebuild of the main workload → run it side by side and compare behaviour.
- **What AI adds:** Reading heterogeneous evidence (unit files, crontabs, shell/Perl/PHP scripts, vhost configs, log lines) and explaining business purpose in plain language; turning that understanding into a Compose file and checks.
- **Simple baseline:** A collector script plus [Enroll](https://enroll.sh) or [ansible-clone](https://github.com/jsf0/ansible-clone) to reproduce packages and configs, with a human reading the output.
- **Action boundary:** The collector is strictly read-only and never stops, restarts, or modifies services. Secrets found in configs are masked before leaving the server. Rebuilds run only in disposable containers; comparison probes are fixed and deterministic.

## 3. Existing alternatives and difference

| Alternative or workaround | What it already solves | Our specific difference |
|---|---|---|
| [Enroll](https://enroll.sh) ([Show HN](https://news.ycombinator.com/item?id=46449852)), [ansible-clone](https://github.com/jsf0/ansible-clone), Pysa | Reverse-engineer installed packages, services, and configs into Ansible | No explanation of purpose, no dependents/blast-radius analysis, no behavioural verification of the rebuild. |
| [Google Migrate to Containers](https://cloud.google.com/products/cloud-migration/containers), [AWS App2Container](https://aws.amazon.com/blogs/architecture/migrate-your-applications-to-containers-at-scale) | Analyse a running VM, extract the application, and generate container images and manifests | Strong precedent for the rebuild step. Tied to GKE/Cloud Run or AWS targets (App2Container: Java/.NET only); no plain-language purpose explanation or behavioural comparison found. |
| [Azure Migrate dependency analysis](https://learn.microsoft.com/azure/migrate/concepts-dependency-visualization) | Agentless per-process inbound/outbound TCP dependency maps for servers | Strong precedent for the dependents step; Azure-centric and does not explain what the services do. |
| AI SSH agents (e.g. [Infra Agent](https://gitea.com/paoloronco/infra-agent), [OpsKat](https://github.com/opskat/opskat), [ManageLM](https://managelm.com/doc/)) | Natural-language diagnostics and operations over SSH, some with read-only modes and approvals | General-purpose assistants; no structured passport, ground-truth check, or verified rebuild. |
| AI legacy-code tools (e.g. [Workik](https://workik.com/legacy-codebase-documentation-generator), IBM watsonx Code Assistant) | Explain and document legacy source code | Work on repositories, not on a running server's runtime evidence. |
| Manual archaeology + scream test | Eventually finds out what matters | Slow, risky, and depends on whoever still remembers. |

**Why would this user choose our approach?** Hypothesis: it combines discovery, plain-language purpose, dependents, and a verified rebuild in one provider-neutral open-source tool. Most individual steps already exist (Google, AWS, Azure, Enroll), so the difference is the combination and the target, not any single capability.

## 4. Smallest working demo

**Demo story:** A "legacy box" with nginx, a PHP app, Postgres, and a forgotten cron job that emails invoices every night.

1. **Before:** The server has no documentation; the naive cleanup plan would remove the "unused" cron script.
2. **Intervention:** Run the collector; the passport flags the invoice job as business-critical (it reads the billing tables and talks to the mail relay), lists the clients connecting to Postgres, and masks a plaintext password found in a config.
3. **After:** The generated Compose rebuild starts; probes confirm the web app returns the same pages and the invoice job produces the same output against fixture data.

- **Must build:** (1) read-only collector script; (2) AI passport generator with secret masking; (3) rebuild generator + side-by-side comparison probes.
- **Out of scope today:** Windows servers, full fleet discovery, automatic decommissioning, live data migration.
- **Success metric:** Target: the passport identifies all services and scheduled jobs planted in the demo box (ground truth known), and the rebuild passes the comparison probes. Goals, not measurements.
- **Failure case:** Unknown or unreadable components are listed as "unexplained" with raw evidence; the tool never claims a component is safe to remove.
- **Demo fallback:** A prebuilt evidence bundle from the demo box and a recorded model response, clearly labelled as replay; the rebuild and probes run live.

## 5. Feasibility on the supplied Linux VM

| Dependency | Proposed approach | Available / Unverified / Blocked |
|---|---|---|
| Data and telemetry | Synthetic legacy box built by us (container or VM) with known ground truth | Unverified: box must be built. |
| Model and inference | Mistral API or local model via Ollama for summarising evidence and generating Compose | Unverified: API key, context size for large evidence bundles, VM RAM. |
| Infrastructure and permissions | Docker on the VM for the legacy box and the rebuild | Unverified: Docker rights. |
| Libraries and integrations | Bash/Python collector, Python + Streamlit UI | Unverified: install on VM; permissive licences. |

**Rough effort and split:** Demo box, collector, AI passport, rebuild + probes, UI + pitch. Hardest integration: generating a rebuild that behaves like the original.
**Biggest blocker:** Large evidence bundles exceeding model context; mitigate by pre-filtering (only changed configs, running units, active sockets).

Keep credentials out of this file. Confirm API access separately from chat subscriptions or VM login access.

## 6. Fastest validation

- **Riskiest assumption:** The model can reliably infer purpose and dependents from collector output without hallucinating components.
- **Quick experiment:** Build the demo box, run the collector, and check whether the model identifies all planted services and the hidden cron job (precision/recall against ground truth).
- **Continue if:** All planted components are found and no invented components appear.
- **Simplify or park if:** Results are unreliable; keep the deterministic collector + passport template and use AI only for explaining scripts.

## 7. Team decision

Initial AI-assisted assessment against the [official criteria](../../../00_Context/challenge-and-guidelines.md); provisional, not a team vote.

| Criterion | Score | Reason |
|---|---|---|
| Innovation | 3 | Discovery, dependency maps, and VM-to-container rebuilds already exist from hyperscalers; only the AI purpose explanation and provider-neutral combination are new. |
| Applicability | 4 | Universal sysadmin pain; first step of any migration to Leaseweb. |
| Technical complexity and quality | 4 | Collector, AI analysis, rebuild, and behavioural comparison. |
| Presentation and clarity | 4 | "We found the invoice job before you deleted it" is memorable. |
| **Total** | **15/20** | |

**Decision:** Explore  
**Reason and next action:** Build the demo box first and run the ground-truth experiment; owner unassigned.
