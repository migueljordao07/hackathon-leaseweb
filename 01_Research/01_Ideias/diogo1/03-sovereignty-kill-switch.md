# Sovereignty Kill-Switch Test

> For **European teams that believe their stack is "sovereign" because it runs in an EU data centre**, we help **discover which non-EU services the application silently depends on and what breaks without them** using **AI to classify observed outbound dependencies by legal jurisdiction and propose EU replacements**, improving **the share of critical workflows proven to run with non-EU endpoints blocked**.

**Proposed by:** Diogo (AI-assisted research) · **Status:** Exploring
**Theme:** Migration & sovereignty / Security & data protection
**Date:** 20 November 2026

## 1. Problem and user

- **Who encounters this, and when?** A CTO, security lead, or platform engineer answering a customer or public-sector questionnaire about CLOUD Act exposure, or preparing a move to a European provider.
- **What goes wrong today?** The servers are in the EU, but login goes through a US identity provider, errors go to a US monitoring SaaS, container images come from a US registry, and an AI feature calls a US LLM API. Nobody has a complete list, and nobody knows which workflows would stop if those services became unavailable or prohibited.
- **Current workaround:** Spreadsheets of declared vendors, website cookie/third-party scanners, or doing nothing.
- **Evidence and source:**
  - Community signal: r/devops post "Your AI agents are sending customer data to OpenAI on every run and your DLP doesn't see it" ([seen via the r_devops Telegram mirror](https://t.me/s/r_devops/31926)); r/BuyFromEU discussions about European companies depending on US clouds ([DeepL thread](https://www.reddit.com/r/BuyFromEU/comments/1ry1irp/deepl_is_shifting_to_aws_for_processing/)). Verify the original threads before quoting them.
  - Practitioners report that even after moving infrastructure, they still depend on US services for chat, billing, and deployment ([fortrabbit](https://blog.fortrabbit.com/us-against-them)); an HN discussion on European company websites notes that sovereignty discussions often start too late in the stack ([HN mirror](https://zeli.app/story/48816612)).
  - On 24 October 2026 AWS disconnected its European Sovereign Cloud for several hours as a provider-side drill; Qovery argues the honest proof is a customer-side severance drill that blocks non-sovereign endpoints in an isolated clone ([Qovery](https://www.qovery.com/blog/7-cloud-sovereignty-tests-run-yourself-after-aws-sovereign-cloud-drill)), described as a manual procedure.
  - Untested assumption: teams want an automated, repeatable version of that drill.

## 2. Proposed solution and AI contribution

- **User workflow:** Run the app in an isolated network where all egress goes through a recording proxy → execute defined workflows (login, upload, checkout, AI feature) → build an inventory of outbound domains → classify each by operator and legal jurisdiction → re-run the same workflows with non-EU-jurisdiction endpoints blocked → report which workflows break, why, and which EU alternatives could replace each dependency.
- **What AI adds:** Mapping unknown domains and CDN hostnames to the real operator and parent company (flagged as "AI-inferred, needs review" when not in the curated catalogue), explaining the business impact of each failure, and proposing concrete EU replacements and config changes.
- **Simple baseline:** Proxy logs plus a static domain → vendor list, with a human deciding jurisdiction and running the blocked test by hand (the manual drill Qovery describes).
- **Action boundary:** Runs only on an isolated copy with fixture data and test accounts. Blocking happens in the test network only; nothing in production is changed. Workflow pass/fail is decided by deterministic probes; jurisdiction calls from the model are labelled and reviewable.

## 3. Existing alternatives and difference

| Alternative or workaround | What it already solves | Our specific difference |
|---|---|---|
| [EgressProof](https://lablab.ai/u/@manges) (hackathon project) | Runs a workflow under restricted egress and reports which step failed and which dependency was observed | Generic egress restriction; we block by legal jurisdiction, classify operators, and propose EU replacements. Closest precedent: must be acknowledged. |
| [Friendly Captcha EU Data Sovereignty Checker](https://friendlycaptcha.com/eu-data-sovereignty-checker/) | Scans a website URL for non-EU third parties and gives a score | Front-end only; no backend egress, no "what breaks" test. |
| [Sovereignty Scan MCP](https://glama.ai/mcp/connectors/io.github.kajaril/sovereignty-scan-mcp), [SUSE Cloud Sovereignty Framework self-assessment](https://www.suse.com/c/from-policy-to-proof-cracking-the-black-box-of-digital-sovereignty) | Classify declared providers or self-assess against the EU framework | Based on declared stacks or questionnaires, not observed runtime behaviour. |
| [Aurva](https://www.aurva.io/external-threat-monitoring) (commercial) | Monitors outbound data flows against residency policies | Monitoring, not a severance drill with workflow tests and replacement plan. |

**Why would this user choose our approach?** Hypothesis: it turns "are we sovereign?" from a questionnaire into a repeatable test with evidence, which buyers and auditors increasingly ask for. Differentiation against EgressProof must be shown clearly in the pitch.

## 4. Smallest working demo

**Demo story:** A European SaaS app hosted in the EU claims to be sovereign.

1. **Before:** All workflows pass with open egress; the vendor spreadsheet lists only the EU hosting provider.
2. **Intervention:** The recording run reveals calls to a US identity provider, a US error-tracking SaaS, a US container registry, and a US LLM API. With non-EU endpoints blocked, login and the AI feature fail; uploads still work.
3. **After:** The report shows the dependency map, the failed workflows with evidence, and suggested EU replacements; after swapping one dependency (e.g. a local/EU LLM endpoint), the re-run passes that workflow.

- **Must build:** (1) isolated network + recording/blocking proxy; (2) jurisdiction classifier (curated catalogue + AI for unknown domains); (3) workflow runner + report with replacement suggestions.
- **Out of scope today:** Full TLS interception, legal advice, production monitoring, automatic code changes.
- **Success metric:** Target: detect every planted external dependency in the demo app and correctly predict which workflows fail when blocked. Goals, not measurements.
- **Failure case:** Unclassifiable domains are shown as "unknown jurisdiction" and treated as blocked in strict mode; the report never labels an app "sovereign", only "passed these workflows under these rules".
- **Demo fallback:** Third-party services simulated by local mocks behind real vendor domain names via local DNS, clearly labelled as simulated; proxy, blocking, and probes run live.

## 5. Feasibility on the supplied Linux VM

| Dependency | Proposed approach | Available / Unverified / Blocked |
|---|---|---|
| Data and telemetry | Demo app with planted dependencies; proxy logs (domains via CONNECT/SNI) | Unverified: demo app and mocks must be built. |
| Model and inference | Mistral API or local model for domain classification and replacement suggestions | Unverified: API key, latency, VM RAM. |
| Infrastructure and permissions | Docker networks with egress forced through a proxy (e.g. Squid/mitmproxy without interception) | Unverified: Docker and iptables rights on the VM; outbound internet from the VM. |
| Libraries and integrations | Python, a forward proxy, curated domain → operator catalogue, Streamlit | Unverified: install on VM; permissive licences. |

**Rough effort and split:** Network/proxy, demo app + mocks, classifier, workflow runner, report/UI + pitch. Hardest integration: forcing all egress through the proxy reliably.
**Biggest blocker:** Missing network privileges on the VM; fallback is running the proxy as an explicit HTTP(S)_PROXY for the app.

Keep credentials out of this file. Confirm API access separately from chat subscriptions or VM login access.

## 6. Fastest validation

- **Riskiest assumption:** Observed egress plus a small catalogue and AI classification is accurate enough to produce a trustworthy jurisdiction map.
- **Quick experiment:** Record egress from the demo app, classify 20 domains with the model, and compare against a hand-made ground truth.
- **Continue if:** At least 18 of 20 domains are classified correctly and blocked workflows fail as predicted.
- **Simplify or park if:** Classification is unreliable; keep a curated catalogue only and use AI for impact explanation and replacement suggestions.

## 7. Team decision

Initial AI-assisted assessment against the [official criteria](../../../00_Context/challenge-and-guidelines.md); provisional, not a team vote.

| Criterion | Score | Reason |
|---|---|---|
| Innovation | 3 | EgressProof and manual severance drills exist; jurisdiction-aware blocking with replacement plans was not found. |
| Applicability | 4 | Strong European demand; fits Leaseweb's sovereignty message. |
| Technical complexity and quality | 4 | Network isolation, proxying, classification, and workflow probes. |
| Presentation and clarity | 5 | Watching login break when US endpoints are cut is very visual. |
| **Total** | **16/20** | |

**Decision:** Explore  
**Reason and next action:** Could be merged into [ExitDrill](./01-exitdrill.md) as a second drill mode; decide after the team compares ideas. Owner unassigned.
