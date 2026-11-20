# Francisco's Hackathon Ideas

Ideas proposed by Francisco or developed from practitioner research on Hacker News, Reddit (`r/devops`, `r/sre`), and hosting community forums (WebHostingTalk/LowEndTalk) on 20 November 2026. 

Each idea card follows the official [idea template](../idea-template.md) and targets the core themes of the **Leaseweb × Velv InfraHack**: European data sovereignty, hyperscaler alternatives, operational safety, and real-time cloud infrastructure engineering.

---

## Strategic Focus: Beyond the "Chatbot & Static Linter Trap"

A critical conclusion from team discussions and market analysis is that **generic terminal chatbots that simply suggest bash commands already exist** (Claude Code, Cursor, and ChatGPT native agents already execute terminal commands and inspect errors). Furthermore, static IaC linters (which only read static Terraform text files) miss dynamic runtime behavior.

Francisco's proposals focus specifically on **Runtime Infrastructure, Kernel Telemetry, and Operational Safety Boundaries**:

| ID | Idea | Main Question & Focus | Market Uniqueness | Initial Assessment | Relative Effort |
|---|---|---|---|---|---|
| 01 | [SovereignKernel](./01-sovereign-kernel-radar.md) | Does our running Linux VM silently leak telemetry, DNS queries, or customer data to US CLOUD Act jurisdictions? | **High (Unserved)** · Existing tools only scan static IaC; none inspect live Linux kernel sockets, DNS leaks, and enforce NIS2 Art. 21 in real time. | **19.5/20** | Medium |
| 02 | [SovereignEdge](./02-egress-semantic-cache-shield.md) | Can we eliminate predatory AWS data egress fees by semantically caching dynamic API queries on Leaseweb infrastructure? | **High (Unserved)** · Traditional caches fail on dynamic query payloads; semantic similarity slashes egress bandwidth costs by up to 70%. | **18.5/20** | Medium |
| 03 | [BlastShield](./03-blastshield-preflight-sandbox.md) | How can an on-call engineer verify the mathematical blast radius of an operational fix before executing it on production servers? | **Medium-High** · Transcends advisory chatbots by using deterministic AST parsing and ephemeral sandbox dry-runs to prevent catastrophic data loss. | **19.0/20** | Medium |

---

## Assessment Summary & Recommendations

- **Top Recommendation for the Hackathon: SovereignKernel (ID 01)**
  - **Why it wins:** It directly attacks the core business and brand proposition of **Leaseweb** as Europe's premier sovereign alternative to AWS. While competitors claim sovereignty based on server location, SovereignKernel mathematically *proves* and enforces it at the Linux network level, generating instant NIS2 Article 21 compliance proof.
  - **Demo dynamic:** Provides a stunning live visual demo on the supplied Linux VM—turning an insecure, telemetry-leaking server into a 100% compliant sovereign bastion in under 30 seconds.
- **Strong FinOps Alternative: SovereignEdge (ID 02)**
  - Capitalizes on Leaseweb’s high-bandwidth, unmetered network transit to break hyperscaler egress lock-in.

---

*Scores are preliminary AI-assisted assessments using the four equally weighted [official criteria](../../../00_Context/challenge-and-guidelines.md) (Innovation, Applicability, Technical Quality, Presentation Clarity). They serve as discussion aids for team alignment.*
