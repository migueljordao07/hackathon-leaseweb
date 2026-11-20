# Top 3 Ideas: Final Synthesis of All Team Proposals

**Proposed by:** Diogo (AI-assisted synthesis) · **Status:** Proposal for team decision
**Date:** 20 November 2026 (written at ~11:15)
**Inputs:** every card in `01_Research/01_Ideias/` (Carolina 01; Diogo 01–06; Francisco 01–03; Miguel 01–05; Ricardo 00-Final and 01–05), the duplicates in the root `01_Ideias/`, the [team briefing](../../ai-cloud-infrastructure-team-briefing.md), the ideas discussed in chat during the morning, and a same-day market check (sources at the end).

> **Honesty rule for this document.** "Not found" means not found in roughly 45 targeted web searches on 20 November 2026. It does not prove that nothing similar exists. Every number we show on stage must be computed by our code from a cited source.

---

## 0. TL;DR

| Rank | Idea | What it does, in one sentence (no jargon) | Innovation grade (0–20) | Jury score (/20) | Decision score (/30) |
|:-:|---|---|:-:|:-:|:-:|
| **#1** | **SkyShift Exit Test** | Takes an app that runs on Amazon, moves it to a European cloud in minutes, and proves live that it works the same and no longer sends data to the US. | **13** | **18** | **26** |
| #2 | **Bill-Shock Replay** | Before a code change is accepted, replays realistic traffic and shows in euros how much that change will add to the cloud bill, then proves the fix. | 11 | 15 | 23 |
| #3 | **Airlock** | Before an AI assistant is allowed to touch a real server, rehearses its plan on a copy, shows what would break, and only lets it proceed with proof. | 10 | 16 | 23 |

**Recommendation:** build **#1**. If the 30-minute validation test (section 8) fails, switch to **#2**, which needs no Docker, no cloud credentials, and no external target. #2 and #3 tie on the decision score; #2 wins the tie on innovation grade and on feasibility today.

---

## 1. What the hackathon asks for

**Challenge (from the [official brief](../../../00_Context/challenge-and-guidelines.md)):** use AI to make cloud infrastructure smarter, safer, and more efficient. Themes of particular interest to the jury:

1. **AI-assisted cloud infrastructure:** a tool or use case shown in a demo.
2. **Hyperscaler alternatives / sovereignty:** tooling that replaces a locking-in hyperscaler service, or makes migrating to a sovereign alternative easier.
3. **Security:** smarter tools to spot, mitigate, or prevent security issues, possibly with AI.

**Jury criteria (equal weight, 1–5 each):** Innovation · Applicability (ideally shown with a prototype) · Technical complexity (quality, use of AI and cloud infrastructure) · Presentation & clarity. Live demos are appreciated and their functioning is scored.

**Hard constraints today:** team of 5 · one supplied Linux VM · code freeze 15:15 · 5-minute pitch at 15:45 · open licence (Apache-2.0) · public repository · no secrets in Git · no dependency on unverified cloud credentials, root/iptables tricks, or multi-day builds.

**Sponsor context:** Leaseweb positions itself as a sovereign-by-design European IaaS provider (European Cloud Campus, IPCEI-CIS) and offers an [EC2-compatible API](https://developer.leaseweb.com/api-docs/awsec2wrapper_v1.html), an official [Terraform provider](https://blog.leaseweb.com/?p=8558), and a new Public Cloud manageable through an [OpenStack API](https://kb.leaseweb.com/?p=16080). Its own November 2026 survey found that 89% of businesses face migration barriers and 55% would need more than three months to move critical workloads, or could not move them at all ([Channel Insider](https://www.channelinsider.com/infrastructure/leaseweb-cloud-migration-msp-strategy/)). Velv is a Portuguese nearshore engineering company expanding in AI and data.

---

## 2. Method

1. **Inventory:** every card in the repository plus every idea discussed in chat (section 3).
2. **Clustering:** cards that solve the same problem were merged into one stronger concept; narrow utilities were turned into components of a bigger concept where they add proof or wow.
3. **Market check:** for each concept, the closest open-source and commercial products in 2025–2026.
4. **Scoring:**
   - **Innovation grade (0–20)** = four sub-scores of 0–5: *concept novelty* (is the problem/approach new?), *mechanism novelty* (is the way it works new?), *context novelty* (new target, audience, or setting?), *gap vs. the closest product* (how far is the nearest existing tool?).
   - **Jury score (/20)** = our provisional 1–5 on each official criterion.
   - **Decision score (/30)** = jury score + *feasibility today* (1–5: can 5 people ship a reliable demo on one VM by 15:15?) + *theme and sponsor fit* (1–5: does it hit the brief's themes and Leaseweb's business?).

---

## 3. Full inventory and verdicts

### 3.1 Repository cards

| Card | Merged into | Closest existing tools | Verdict |
|---|---|---|---|
| Ricardo 00-Final SkyShift (unified) | **#1 (base)** | See #1 | Keep as base; apply the corrections in 4.9 |
| Ricardo 02 SkyShift | #1 | Firefly, StackGen, eu-cloud-mcp | Merged |
| Diogo 01 ExitDrill | #1 | EscapeCloud, consultancies | Merged |
| Diogo 04 Sovereign Exit Semantic Auditor | #1 | eu-cloud-mcp, LocalStack | Merged (SDK scan) |
| Carolina 01 ExitProof | #1 | LocalStack, CloudExit, Azure Migrate | Merged: portability contract, same tests on source and target, Portability Passport, continuous checks |
| Ricardo 01 SovereignGuard | #1 (audit step) | EscapeCloud, eu-cloud-mcp, Sovereignty Scan MCP | Standalone parked: static sovereignty scanning already exists |
| Francisco 01 SovereignKernel | #1 (runtime radar) | EgressProof, OpenSnitch, Aurva | Merged without eBPF/iptables |
| Diogo 03 Sovereignty Kill-Switch | #1 (severance drill) | EgressProof (not jurisdiction-aware) | Merged; becomes the centrepiece of #1 |
| Diogo 05 App-to-Infra PR Cost Guard | **#2 (core)** | Infracost, CloudBurn (IaC only) | Merged |
| Francisco 02 Egress Semantic Cache | #2 (as a verified fix) | GPTCache (LLM prompts only) | Standalone parked: semantic caching of arbitrary APIs can return wrong data |
| Ricardo 03 CloudShrink | #2 (verified remediation idea) | Cloud Custodian, AWS Compute Optimizer | Standalone parked: crowded |
| Miguel 05 Change Rehearsal Lab | **#3 (core)** | Upsun propose-and-test (inside its PaaS) | Merged |
| Miguel 01 Operation Outcome Verifier | #3 (and #1 evidence) | Conftest, manual checklists | Merged |
| Miguel 02 Change Impact Reviewer | #3 | Overmind (Terraform blast radius) | Merged |
| Miguel 03 Project Cleanup Planner | #3 (demo scenario) | Tag/prefix scripts | Merged |
| Miguel 04 Stale Plan Detector | #3 (component) | Version/hash guards | Standalone parked: too narrow |
| Francisco 03 BlastShield | #3 | Destructive Command Guard, GuardRail, Termaxa; a GitHub project already named BlastShield | Merged; name must change |
| Ricardo 04 SRE-Healer | #3 (the "agent") | HolmesGPT (works with VMs too), AWS DevOps Agent (GA March 2026, per briefing), Infra Agent | Standalone parked: crowded |
| Diogo 02 Legacy Server Passport | — | Google Migrate to Containers, AWS App2Container, Azure Migrate dependency analysis, Enroll | **Parked** (innovation grade 7) |
| Diogo 06 CVE Reachability & Patch Verifier | — | Aikido (reachability + AutoFix), Endor Labs, Kubescape VEX | **Parked** (innovation grade 6) |
| Ricardo 05 LeastPrivilege AI | — | AWS IAM Access Analyzer policy generation, Cloudsplaining | **Parked** (innovation grade 4; needs AWS credentials) |
| Root `01_Ideias/*.md` | — | — | Older duplicates of Ricardo's cards; ignored |

### 3.2 Ideas discussed in chat (not as cards)

| Idea | Verdict | Reason |
|---|---|---|
| "Cheap LLM managing other AIs" (LLM router) | Component of #1 | Routers already exist (e.g. RouteLLM). Useful inside #1 as a local sanitiser + router so that sensitive data never leaves the VM and only hard cases reach an EU-hosted model. |
| Sovereign AI SRE agent | Parked | HolmesGPT, Aurora, and K8sGPT already support local models. |
| VMware placement advisor | Parked | Sensitive for the sponsor (Leaseweb is a VMware VCSP partner). |
| Backup "restore proof" | Parked | Automated restore verification exists in commercial backup suites; weaker sponsor fit. |

### 3.3 Scoring of the finalists and the strongest parked ideas

| Concept | Innovation grade (0–20) | Innovation | Applicability | Technical | Presentation | **Jury /20** | Feasibility today | Theme/sponsor fit | **Decision /30** |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| **#1 SkyShift Exit Test** | 13 | 4 | 5 | 4 | 5 | **18** | 3 | 5 | **26** |
| **#2 Bill-Shock Replay** | 11 | 4 | 4 | 3 | 4 | **15** | 5 | 3 | **23** |
| **#3 Airlock** | 10 | 3 | 4 | 4 | 5 | **16** | 4 | 3 | **23** |
| Kill-switch as a standalone product | 10 | 3 | 4 | 4 | 5 | 16 | 4 | 4 | 24 (merged into #1) |
| Legacy Server Passport | 7 | 2 | 4 | 4 | 4 | 14 | 4 | 3 | 21 |
| CVE Reachability & Patch Verifier | 6 | 2 | 4 | 4 | 3 | 13 | 3 | 3 | 19 |
| SRE-Healer (standalone) | 5 | 2 | 4 | 3 | 4 | 13 | 3 | 3 | 19 |
| LeastPrivilege AI | 4 | 1 | 3 | 3 | 3 | 10 | 2 | 2 | 14 |

The standalone kill-switch scores well, but it is stronger as the climax of #1 than as a separate project; it is therefore merged rather than listed as a finalist.

---

## 4. Idea #1: SkyShift Exit Test (Sovereignty / hyperscaler exit)

### 4.1 Pitch (no jargon)
"We take an app that runs on Amazon, move it to a European cloud in minutes, and prove live that it works the same and no longer sends data to the US."

### 4.2 What it does
- **Reads** an AWS project (Terraform + Python code using boto3) and scores how locked-in it is.
- **Translates** it into a Leaseweb-ready setup: open-source services that speak the same language as AWS (S3 → MinIO), plus validated Leaseweb Terraform.
- **Runs** the original, unmodified app on the Leaseweb VM, changing only where it connects.
- **Proves** it works: the same tests run against the "before" (emulated AWS) and the "after" (Leaseweb), with checksums.
- **Cuts the US off** (severance drill): blocks every endpoint under US jurisdiction and shows what breaks; the AI explains and proposes a European replacement; the re-run passes.
- **Hands over evidence:** a PASS/FAIL result, a hash-chained evidence file, and a report shaped like a DORA exit plan. Because it returns PASS/FAIL, it can run on every commit, like a unit test for independence.

### 4.3 Who it is for and why it matters
- **Users:** platform and DevOps teams at European companies on AWS; compliance teams that must show a tested exit plan (DORA Art. 28(8) requires exit plans that are documented and sufficiently tested, see the [Orbiq template](https://www.orbiqhq.com/templates/dora-exit-strategy-plan)); Leaseweb's sales and onboarding teams.
- **Problem evidence:**
  - AWS, Azure, and Google hold ~70% of the European cloud market ([TNW](https://thenextweb.com/news/europes-cloud-dependency-political-risk)).
  - The EU Data Act bans switching charges, including migration egress, from 12 January 2027 ([overview](https://ecorpit.com/eu-data-act-cloud-switching-fees-ban-january-2027/)), but zero fees do not remove architectural lock-in.
  - "S3-compatible" does not mean identical: for example, Scaleway lists some S3 operations as still in development ([Scaleway API list](https://www.scaleway.com/en/docs/object-storage/api-cli/using-api-call-list/), cited in Carolina's card).
  - 89% of businesses face migration barriers (Leaseweb survey, see section 1).

### 4.4 How it works (pipeline)
```
AWS repo ──► 1. Scan ──► 2. Translate ──► 3. Run ──► 4. Prove ──► 5. Severance drill ──► 6. Evidence
             python-hcl2  catalogue +      docker      same tests   proxy blocks US       PASS/FAIL,
             + boto3 AST  templates; AI    compose     on Moto      jurisdiction; AI      hash chain,
             → lock-in    only for gaps;   on the VM;  ("before")   explains + swaps;     DORA-shaped
             score        tofu validate    same app.py and MinIO    re-run                report, badge
                                           new endpoint ("after")
```

### 4.5 Built from
Ricardo 00-Final (pipeline, task split) and 01–02 · Carolina 01 (portability contract, same tests on source and target, Moto/SeaweedFS idea, Portability Passport, continuous checks) · Diogo 01, 03, 04 (exit drill, kill-switch, SDK semantics) · Francisco 01 (runtime radar) · Miguel 01 and 05 (outcome verification, rehearsal).

### 4.6 Innovation: what exists and what is new

| Closest existing | What it does | What it lacks |
|---|---|---|
| [EscapeCloud](https://www.einpresswire.com/article/911725797/escapecloud-launches-cloud-exit-readiness-platform-for-operational-resilience-and-digital-sovereignty) (+ open-source [cloudexit](https://github.com/escapecloud/cloudexit)) | Exit-readiness, lock-in, and sovereignty scoring aligned with DORA | Assessment only; nothing is executed |
| [eu-cloud-mcp](https://github.com/moveinfra/eu-cloud-mcp) | Terraform lock-in scan, EU alternatives, prices, egress estimates | Read-only; no Leaseweb; no code, no run |
| [Firefly](https://www.firefly.ai/blog/revolutionizing-cloud-migration-with-fireflys-innovative-iac-generation), [StackGen](https://devops.com/stackgens-new-migration-engine-a-devops-game-changer-for-multi-cloud-transitions/) | AI-assisted IaC translation between clouds | AWS/Azure/GCP only; no verification |
| [Coriolis](https://cloudbase.it/coriolis-getting-started) (open source) | VM lift-and-shift from AWS to OpenStack and others | Moves VMs, not IaC/app behaviour; no sovereignty proof |
| [Qovery agentic migration](https://www.qovery.com/blog/agentic-migration-to-gcp-what-agents-automate) | Agent chain: discover, generate Terraform, validate | Targets GCP and its own platform |
| [EgressProof](https://lablab.ai/u/@manges) (hackathon project) | Runs a workflow under restricted egress, reports the failing step | Not jurisdiction-aware; no migration |
| [ceph/s3-tests](https://github.com/ceph/s3-tests) (MIT) | S3 compatibility test suite (boto3) | A test suite, not a workflow; we reuse a subset |
| [Endava](https://www.endava.com/insights/articles/building-cloud-portability-and-exit-strategies), [Cloudnovi](https://cloudnovi.com/sovereign-cloud/), Deloitte + DEEP, [Leaseweb + WSM](https://www.leaseweb.com/products) | Human-led exit tests and migrations | Manual consulting, weeks of work |

**What is new:** no single product was found that automates *translate → run → cut US endpoints → AI fix → re-run → evidence* for a European target. The concept "test your exit" is known and sold as consulting; the automated, open-source, Leaseweb-targeted closed loop is the innovation.

**Innovation grade 13/20:** concept 2/5 (exit testing is discussed and sold as consulting) · mechanism 4/5 (jurisdiction-aware severance drill inside a migration loop, zero-code-change swap) · context 4/5 (European/Leaseweb target, DORA-shaped evidence) · gap vs. closest product 3/5 (pieces exist separately; Qovery is closest end-to-end but targets GCP).

### 4.7 What AI does vs. what code proves
- **AI:** maps resources that are not in the catalogue; selects the relevant subset of compatibility tests from the boto3 calls found; explains blockers and failures; proposes the European replacement; drafts the exit-plan narrative. Runs on an EU-hosted model (Mistral, whose free tier may train on inputs, so synthetic data only, see [Mistral help](https://help.mistral.ai/en/articles/450104-how-can-i-try-the-api-for-free-with-the-experiment-plan)), with inputs sanitised locally ([CloakLLM](https://github.com/cloakllm/CloakLLM), MIT).
- **Deterministic code:** HCL parsing, catalogue mapping and Jinja2 templates, `tofu validate`, `docker compose up`, s3-tests subset, SHA-256 checksums, proxy allow/deny log, socket inspection against the IP ranges published by AWS, Azure, Google, and Cloudflare, evidence hashing.
- **Rule:** pass/fail is always decided by code, never by the model.

### 4.8 Fit and scalability
- **Themes:** hits all three (AI-assisted infrastructure, sovereignty/hyperscaler exit, security via data-leak detection).
- **For Leaseweb:** an "Exit to Leaseweb" onboarding button: upload Terraform → tested plan → deploy with the Leaseweb provider. Directly addresses the barrier in Leaseweb's own survey.
- **Product growth:** catalogue grows per resource type; more European targets; CI mode on every commit; an "Exit-tested ✓" README badge (date + evidence hash) spreads the tool.

### 4.9 Corrections to Ricardo's 00-Final (apply in code and pitch)
1. No "mathematical guarantee" or "zero leakage enforced": say "these N checks passed". Reading `/proc`/`ss` only detects; the local allowlist proxy is what blocks.
2. Numbers must be computed from cited public price lists. The 00-Final shows €185→€48 (−74%) in one section and €240→€65 (−73%) in another, and an unsourced "78%" market claim.
3. "Production-ready deployment + sovereignty certificate" → "verified migration package + evidence report".
4. Pick one target with the mentors: official Leaseweb provider (`leaseweb_public_cloud_instance`) or the new Public Cloud OpenStack API.
5. Use an EU or local LLM; the 00-Final criticises tools that send code to US AI APIs.
6. Scope today: AWS Terraform + Python/boto3 only (no Azure, no CloudFormation).
7. Add the missing competitors (EscapeCloud, eu-cloud-mcp, Firefly/StackGen, Coriolis, Qovery, EgressProof) to the related-work slide.

### 4.10 Five-minute demo
1. **Problem (40 s):** "89% can't leave." The AWS repo scores 24/100 exit readiness (computed by code, not typed on a slide).
2. **Shift (60 s):** AWS → Leaseweb diff, validated. The same `app.py` starts on the VM with a new endpoint; a check shows the VM's public IP belongs to a Leaseweb network block.
3. **Severance drill (90 s):** cut US endpoints. A hidden telemetry call to an AWS IP turns red and is blocked; the AI explains it and proposes a swap; re-run turns green; parity tests pass on both "before" (Moto) and "after" (MinIO) with identical checksums.
4. **Proof (40 s):** PASS result, DORA-shaped report with hash, badge, and "SkyShift passes its own test" (the drill run on SkyShift itself passes because its LLM is EU-hosted).
5. **Business (50 s):** "Exit to Leaseweb" button, exit testing on every commit, closing line: *"Proving you can leave AWS used to be a consulting project measured in weeks. We turned it into an automated test measured in minutes."*

**Fallback:** a recorded run plus cached model responses, clearly labelled as replay; local probes run live.

### 4.11 MVP today (≈4 hours)
- **Build (3 things):** (1) scanner + catalogue + AI mapper → Compose + validated Leaseweb Terraform; (2) verifier: stack up, same tests on Moto and MinIO, severance drill with proxy and socket radar; (3) one-page web UI + evidence report.
- **Cut:** real Leaseweb deployment (unless an API key exists by 11:30), Azure/CloudFormation, eBPF, PDF export, detailed cost model, Kubernetes, signatures (hash only).
- **Split (follows 00-Final):** Ricardo: scanner/translator + validation · Carolina: fixture app + parity tests (s3-tests subset, Moto vs. MinIO) · Francisco: proxy + radar + IP ranges · Miguel: verifier + evidence chain · Diogo: UI + cost table + pitch + backup video.
- **Biggest risk:** Docker or Terraform-registry access missing on the VM. **Mitigation:** run MinIO and Moto as user-space processes; keep templates as the primary path and validate against an offline schema if the registry is blocked.

### 4.12 Scores
Innovation grade **13/20** · Jury: Innovation 4, Applicability 5, Technical 4, Presentation 5 = **18/20** · Feasibility 3 · Fit 5 · **Decision 26/30**.

---

## 5. Idea #2: Bill-Shock Replay (AI-assisted cloud efficiency)

### 5.1 Pitch (no jargon)
"Before a code change is accepted, we replay realistic traffic and show in euros how much that change will add to the cloud bill, then we prove the fix."

### 5.2 What it does
- Runs the app **before** and **after** a code change side by side on the VM.
- Replays the same synthetic traffic through both versions while a local proxy **measures** bytes sent per destination, external API calls, and log volume.
- **Prices** the difference with public price lists (data transfer, NAT processing, log ingestion), including an AWS vs. Leaseweb comparison.
- The AI **points to the culprit line**, explains why it costs money, and proposes a fix (cache, batching, log level); the replay is re-run to **prove** the saving.

### 5.3 Who it is for and why it matters
- **Users:** platform/DevOps engineers reviewing pull requests, especially AI-generated ones; FinOps teams.
- **Problem evidence:** managing cloud spend is the top challenge for 85% of organisations and wasted spend rose to 29% in 2026 (Flexera 2026 State of the Cloud, see the research plan). Existing pull-request cost tools ([Infracost](https://www.infracost.io/), [CloudBurn](https://cloudburn.io/blog/aws-finops-shift-left)) price infrastructure-as-code diffs only; a change that looks cost-neutral at the infrastructure level can multiply egress by changing response sizes ([DZone](https://dzone.com/articles/runtime-finops-making-cloud-cost-observable)).

### 5.4 How it works
```
PR diff ──► AI: which endpoints/scenarios matter? ──► replay N requests on base and PR (git worktrees)
        ──► metering proxy + log sizes ──► price engine (cited price lists) ──► €/month delta
        ──► AI: culprit + fix ──► re-run ──► proven saving
```

### 5.5 Built from
Diogo 05 (core) · Francisco 02 (caching, only as a fix that is proven by re-measurement) · Ricardo 03 (verified remediation instead of passive dashboards).

### 5.6 Innovation
| Closest existing | What it does | What it lacks |
|---|---|---|
| Infracost, CloudBurn, CostPilot | Price IaC diffs in pull requests | Blind to application-code behaviour |
| OpenCost, runtime FinOps | Measure spend after deployment | Too late; no pre-merge proof |
| Semgrep-style rules | Pattern-match risky code | No topology, no measured bytes, no euros |

**Innovation grade 11/20:** concept 3/5 · mechanism 3/5 (measured pre-merge replay priced in euros) · context 2/5 · gap 3/5.

### 5.7 What AI does vs. what code proves
- **AI:** reads the diff, generates targeted replay scenarios, explains the cost driver, proposes the fix.
- **Code:** counts bytes and calls per destination, measures log growth, applies price formulas, re-measures after the fix. The euro figure never comes from the model.

### 5.8 Fit and scalability
- **Themes:** AI-assisted cloud infrastructure ("more efficient"). Weaker on sovereignty; partly recovered by showing the same change priced on AWS vs. Leaseweb.
- **Growth:** CI gate on every pull request; FinOps for application code; sales argument for providers with included bandwidth.

### 5.9 Five-minute demo
1. **Before:** a "harmless" pull request (debug logging plus a per-item API call) passes tests; IaC cost tools show €0.
2. **Live:** replay of 10,000 requests: egress jumps from tens of MB to GB; log volume explodes; the €/month delta appears with the formula visible.
3. **After:** the AI points to the line and proposes a cache + log-level fix; the re-run returns to baseline. **Fallback:** recorded replay data, labelled as such.

### 5.10 MVP today
- **Build:** (1) fixture app + traffic generator; (2) metering proxy + price engine with cited prices; (3) UI + AI diagnosis/fix.
- **Cut:** GitHub integration, multi-cloud, Kubernetes, real billing APIs.
- **Biggest risk:** monthly extrapolation looks invented. **Mitigation:** show assumptions on screen (requests/day, payload size, unit prices with source) and make them adjustable.

### 5.11 Scores
Innovation grade **11/20** · Jury 4, 4, 3, 4 = **15/20** · Feasibility 5 · Fit 3 · **Decision 23/30**.

---

## 6. Idea #3: Airlock (Security of AI agent actions)

### 6.1 Pitch (no jargon)
"Before an AI assistant is allowed to touch a real server, we rehearse its plan on a copy, show what would break, and only let it proceed with proof."

### 6.2 What it does
- An AI ops agent proposes a plan (for example "free disk space").
- Airlock **copies** the app's data and service (directory + database) to a disposable twin on the same VM and runs the plan there first.
- It **checks invariants** before and after: row counts, file checksums, open ports, service health, HTTP probes, scheduled-job output.
- It **blocks** the plan if an invariant breaks, shows the exact diff, lets the AI revise, and **promotes** only a plan that passes, with an evidence record.

### 6.3 Who it is for and why it matters
- **Users:** teams starting to let AI agents (Claude Code, AWS DevOps Agent, HolmesGPT) act on servers; Leaseweb VM and dedicated-server customers.
- **Problem evidence:** AI agents are judged unreliable at infrastructure operations (Miguel's Reddit source, r/Cloud); the briefing notes that investigation products exist but reliable autonomous repair is not established.

### 6.4 How it works
```
agent plan ──► create twin (copy data dir + DB, alternate port, no root) ──► run plan on twin
           ──► invariant checks (before vs after) ──► FAIL: block + diff + AI revises
                                                   └► PASS: promote to real service + evidence
```

### 6.5 Built from
Miguel 05 (rehearsal, core) · Miguel 01 (outcome verification) · Miguel 02 (impact outside scope) · Miguel 03 (cleanup scenario) · Miguel 04 (state version guard) · Francisco 03 (pre-flight safety) · Ricardo 04 (the agent being supervised).

### 6.6 Innovation
| Closest existing | What it does | What it lacks |
|---|---|---|
| [Destructive Command Guard](https://martech.zone/destructive-command-guard-a-safety-net-for-ai-coding-agents/), [GuardRail](https://www.everydev.ai/tools/guardrail-agent/llms.txt), [Termaxa](https://docs.rs/crate/termaxa/0.19.6) | Block or preview dangerous commands by pattern; Termaxa backs up first | Pattern-based; do not observe the real effect |
| [Overmind](https://github.com/overmindtech/cli) | Blast radius of Terraform changes | Terraform/AWS only |
| [Upsun propose-and-test](https://upsun.com/blog/why-your-ai-needs-a-sandbox) | Agent proves its change in a byte-level clone | Only inside the Upsun PaaS |

**Innovation grade 10/20:** concept 2/5 · mechanism 3/5 (AI-proposed invariants checked by code on a VM twin) · context 3/5 (provider-neutral, plain Linux VMs) · gap 2/5.

### 6.7 What AI does vs. what code proves
- **AI:** plays the agent that proposes the plan; suggests invariants from discovered services; explains the diff; revises the plan.
- **Code:** creates the twin, executes only allowlisted operations, compares checksums/counts/ports/probes, decides block or promote.

### 6.8 Fit and scalability
- **Themes:** security and AI-assisted infrastructure. No direct sovereignty angle.
- **Growth:** a safety layer in front of any infrastructure agent; managed-service offering for VM customers.

### 6.9 Five-minute demo
1. **Before:** the agent is asked to "free disk space"; its plan deletes `/var/lib/app/invoices`, which looks like old logs.
2. **Live:** Airlock runs the plan on the twin: invoices 1,204 → 0, the nightly job fails → blocked, diff shown. The AI revises (rotate logs instead); the twin passes; promoted.
3. **After:** disk freed on the real service; invoice checksums identical. **Fallback:** recorded agent plan; twin and checks run live. Also show a plan that passes first time, so it does not look staged.

### 6.10 MVP today
- **Build:** (1) twin creation; (2) invariant engine + diff; (3) UI with plan, diff, block/promote.
- **Cut:** full VM cloning, Kubernetes, arbitrary shell commands.
- **Biggest risk:** the scenario looks staged. **Mitigation:** two scenarios (one blocked, one passing) and invariants derived live from the running service.

### 6.11 Scores
Innovation grade **10/20** · Jury 3, 4, 4, 5 = **16/20** · Feasibility 4 · Fit 3 · **Decision 23/30**.

---

## 7. Head-to-head

| Criterion (1–5) | #1 SkyShift Exit Test | #2 Bill-Shock Replay | #3 Airlock |
|---|:-:|:-:|:-:|
| Innovation (jury) | 4 | 4 | 3 |
| Applicability | 5 | 4 | 4 |
| Technical complexity | 4 | 3 | 4 |
| Presentation & clarity | 5 | 4 | 5 |
| Feasibility today | 3 | 5 | 4 |
| Theme and Leaseweb fit | 5 | 3 | 3 |
| **Decision score /30** | **26** | **23** | **23** |
| Innovation grade /20 | 13 | 11 | 10 |
| Scalability | High (CI + onboarding funnel) | Medium–high (CI gate) | Medium–high (agent safety layer) |
| Wow moment | Cutting the US off live | Euros appearing for a "harmless" PR | Blocking an agent before it deletes invoices |

---

## 8. Decision and first 30 minutes

**#1 SkyShift Exit Test.** Best fit with the brief and the sponsor, strongest stage moment, and the team already converged on it (three independent cards plus Ricardo's 00-Final and Carolina's ExitProof).

**30-minute validation test before committing (stop at 30 minutes):**
1. On the VM: start MinIO and Moto (Docker or user-space binaries); run boto3 `put`/`get`/`list` against both via `AWS_ENDPOINT_URL`.
2. `tofu init` + `tofu validate` with the chosen Leaseweb target using a 10-line `.tf` (confirms registry access).
3. One Mistral call returning a JSON mapping for three resources in under 10 seconds.
4. Run the fixture app with `HTTPS_PROXY` set to a local allowlist proxy; confirm that a call to an AWS IP is logged and denied.

**Go** if all four pass, or three pass with a fallback for the fourth. Otherwise switch to **#2 Bill-Shock Replay**.

---

## 9. Pitch honesty rules
- Say "the first open-source tool we found", never "the first in the world".
- One related-work slide: "EscapeCloud measures, Firefly translates between the big three, Coriolis moves VMs; we execute and prove on a European target."
- Every on-screen number is computed by our code from a cited source.
- No credentials or secrets in the repository; use a local `.env`.

---

## 10. Sources (checked 20 November 2026)

**Sponsor and context:** [Leaseweb EC2-compatible API](https://developer.leaseweb.com/api-docs/awsec2wrapper_v1.html) · [Leaseweb Terraform provider](https://blog.leaseweb.com/?p=8558) · [Leaseweb Public Cloud (OpenStack API)](https://kb.leaseweb.com/?p=16080) · [Leaseweb survey via Channel Insider](https://www.channelinsider.com/infrastructure/leaseweb-cloud-migration-msp-strategy/) · [Leaseweb + WSM migration](https://www.leaseweb.com/products) · [TNW: 70% EU market share](https://thenextweb.com/news/europes-cloud-dependency-political-risk) · [EU Data Act switching charges](https://ecorpit.com/eu-data-act-cloud-switching-fees-ban-january-2027/) · [DORA exit plan template](https://www.orbiqhq.com/templates/dora-exit-strategy-plan)

**#1 market check:** [EscapeCloud](https://www.einpresswire.com/article/911725797/escapecloud-launches-cloud-exit-readiness-platform-for-operational-resilience-and-digital-sovereignty) · [cloudexit](https://github.com/escapecloud/cloudexit) · [eu-cloud-mcp](https://github.com/moveinfra/eu-cloud-mcp) · [Firefly](https://www.firefly.ai/blog/revolutionizing-cloud-migration-with-fireflys-innovative-iac-generation) · [StackGen](https://devops.com/stackgens-new-migration-engine-a-devops-game-changer-for-multi-cloud-transitions/) · [Coriolis](https://cloudbase.it/coriolis-getting-started) · [Qovery agentic migration](https://www.qovery.com/blog/agentic-migration-to-gcp-what-agents-automate) · [EgressProof](https://lablab.ai/u/@manges) · [ceph/s3-tests](https://github.com/ceph/s3-tests) · [Endava](https://www.endava.com/insights/articles/building-cloud-portability-and-exit-strategies) · [Cloudnovi](https://cloudnovi.com/sovereign-cloud/) · [Scaleway S3 API list](https://www.scaleway.com/en/docs/object-storage/api-cli/using-api-call-list/) · [CloakLLM](https://github.com/cloakllm/CloakLLM) · [Mistral free tier](https://help.mistral.ai/en/articles/450104-how-can-i-try-the-api-for-free-with-the-experiment-plan)

**#2 market check:** [Infracost](https://www.infracost.io/) · [CloudBurn](https://cloudburn.io/blog/aws-finops-shift-left) · [DZone: runtime FinOps](https://dzone.com/articles/runtime-finops-making-cloud-cost-observable)

**#3 market check:** [Destructive Command Guard](https://martech.zone/destructive-command-guard-a-safety-net-for-ai-coding-agents/) · [GuardRail](https://www.everydev.ai/tools/guardrail-agent/llms.txt) · [Termaxa](https://docs.rs/crate/termaxa/0.19.6) · [Overmind](https://github.com/overmindtech/cli) · [Upsun](https://upsun.com/blog/why-your-ai-needs-a-sandbox) · [BlastShield (existing GitHub project)](https://github.com/cdrxyz/blastshield)

**Parked ideas:** [Google Migrate to Containers](https://cloud.google.com/products/cloud-migration/containers) · [Azure Migrate dependency analysis](https://learn.microsoft.com/azure/migrate/concepts-dependency-visualization) · [Enroll](https://enroll.sh) · [Aikido](https://www.aikido.dev/code) · [HolmesGPT](https://github.com/robusta-dev/holmesgpt) · [Sovereignty Scan MCP](https://glama.ai/mcp/connectors/io.github.kajaril/sovereignty-scan-mcp)
