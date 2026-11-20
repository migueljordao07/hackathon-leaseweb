# Research Plan: AI for Cloud Infrastructure

**Purpose:** prepare a shared briefing for the five-person InfraHack team, giving everyone enough context to brainstorm useful, distinctive ideas that can become a working demo in one day.

**Research snapshot:** 20 November 2026. **Future briefing:** approximately 1,500-2,000 words, readable in 10-12 minutes, with a compact source list. This document defines the research; it does not present findings or select a project.

## 1. Questions the briefing must answer

1. Where does AI already help cloud infrastructure teams, and what evidence separates working capabilities from announcements?
2. Which operational problems remain painful despite existing tools?
3. Where does AI add value over scripts, rules, dashboards, and conventional automation?
4. Which opportunities fit the challenge's interests: AI-assisted operations, security, and hyperscaler alternatives or sovereignty?
5. What could we demonstrate credibly on one Linux VM before 15:45, and explain within a five-minute pitch?

Use the [official challenge](../00_Context/challenge-and-guidelines.md) and [team context](../00_Context/team.md) as constraints throughout. Keep the briefing accessible to teammates with different levels of cloud experience.

## 2. Scope and research tracks

Start with **AI for operating cloud infrastructure**. Cover **infrastructure for AI** only where it affects deployment, cost, privacy, or feasibility. Prioritize practical workflows over model architecture, GPU training, and broad market forecasts.

| Track | Questions to investigate | Material to bring into the briefing |
|---|---|---|
| Foundations and recent changes | What are the roles of VMs, containers, Kubernetes, infrastructure as code, and observability? How do traditional AIOps, generative copilots, and agents differ? What changed in the last 12-18 months? | A short glossary and a map from observation to diagnosis, recommendation, and action. Separate established capabilities, recent releases, and experimental work. |
| Operations and reliability | How is AI used for alert triage, log analysis, incident diagnosis, runbook retrieval, and remediation? What breaks when telemetry or system context is incomplete? | One concrete operator workflow, representative existing tools, a documented limitation, and measurable outcomes such as diagnosis time or diagnostic accuracy. |
| Security and data protection | Where can AI help with configuration review, identity permissions, vulnerability prioritization, secret exposure, backup validation, or recovery? How can malicious logs or documents manipulate an agent? | A realistic failure scenario, available inputs, the AI contribution, and boundaries for safe action. Include recovery correctness rather than assuming a successful backup means successful restoration. |
| Cost and resource efficiency | Where do forecasting, rightsizing, scheduling, and waste detection benefit from AI? When would thresholds or simple statistics perform just as well? | A workflow with a non-AI baseline and an explicit metric. Separate estimated savings from measured results and consider inference cost. |
| Migration and sovereignty | What creates lock-in: APIs, managed services, identity, data formats, egress, or operational dependencies? Could AI help inventory, explain incompatibilities, translate configurations, or validate a migration? | A small migration journey and a candidate alternative. Distinguish hosting location, control of data, provider dependence, and model/API dependence. Verify relevant Leaseweb interfaces and deployment options. |

For each applied track, investigate **one commercial example and one open-source or self-hosted example** where available. Use these to understand workflows and gaps; avoid turning the briefing into a product catalogue.

## 3. Sources and search strategy

Prefer primary sources: product documentation, release notes, public repositories, reproducible evaluations, original research, and engineering postmortems. Use vendor case studies as attributed claims; seek independent evidence before accepting performance or adoption claims. Use commentary to discover questions, then trace technical claims to their original source.

Suggested source families to investigate, without assuming their current features:

- Cloud providers' operational AI documentation, including AWS, Azure, Google Cloud, and Leaseweb.
- CNCF projects and operator tooling; observability documentation around OpenTelemetry, Prometheus, and Grafana.
- Infrastructure and portability projects such as OpenTofu, OpenStack, Kubernetes, and compatible object storage implementations.
- FinOps Foundation material, original incident reports, security advisories, and research on agent reliability and prompt injection.

Run searches in English. Start with queries such as:

| Goal | Example query |
|---|---|
| Operational capabilities | `AI cloud incident investigation agent documentation release notes 2026` |
| Evidence and limits | `cloud operations LLM agent benchmark failure evaluation 2025 2026` |
| Security workflows | `AI infrastructure misconfiguration remediation prompt injection logs evaluation` |
| Efficiency | `AI cloud rightsizing evaluation baseline FinOps 2026` |
| Portability | `AI cloud migration infrastructure as code sovereign cloud open source` |
| Demo feasibility | `Leaseweb API Linux VM documentation monitoring` |

For each promising result, follow up with the product or project name plus `limitations`, `release notes`, `API`, `license`, and `requirements`. Prefer material from the last 12-18 months, retaining older sources for fundamentals. Record publication and access dates; exclude developments after the snapshot date and distinguish preview from general availability.

## 4. Evidence and comparison method

For each example, capture a compact record:

> **Problem and user | Existing solution | AI's actual role | Inputs and permissions | Evidence of benefit | Failure modes | Deployment/API requirements | Remaining gap | Source and date**

Label statements as **verified capability**, **vendor claim**, **research result**, or **team hypothesis**. Corroborate conclusions that drive project selection with independent evidence where possible. State uncertainty when corroboration is unavailable. An announcement proves an announcement; a benchmark result applies to its tested conditions.

Compare examples using the same questions: Does the tool explain or execute? Can users inspect its evidence? What happens when it is wrong? Can it run across providers? Does it require paid access, proprietary telemetry, or special hardware? What does a simple non-AI implementation achieve?

Target 10-15 useful sources across the tracks. Stop expanding a track once its workflow, existing alternatives, main limitation, and hackathon implication are supported. Leave gaps explicit rather than filling them with assumptions.

## 5. Structure of the future briefing

| Section | Approximate length | Intended result |
|---|---|---|
| What matters for this hackathon | 150 words | Five takeaways tied to the challenge. |
| Shared foundations | 200 words | Common vocabulary and an understandable cloud operations workflow. |
| State of the field | 500-650 words | Recent changes and a compact comparison of representative tools across the applied tracks. |
| Limits and open problems | 250-300 words | Evidence quality, reliability, security, data availability, portability, and cost. |
| Opportunities to explore | 250-350 words | Three to five evidence-backed problem areas, each with an affected user and an unmet need. Keep project choice open. |
| Hackathon implications and discussion | 150-250 words | Feasibility constraints, unknowns to check, and brainstorming prompts. |

Put citations beside factual claims and collect links at the end. Expand acronyms on first use. Prefer one concrete example per theme to long lists of terminology.

## 6. Execution and handoff to brainstorming

Suggested timebox: **40 minutes to research and synthesize**, followed by **10-12 minutes of shared reading** and **15 minutes of brainstorming**. Adapt depth to the time remaining in the build window.

1. **Frame, 5 minutes:** confirm the challenge and shared definitions; identify unknown VM resources, network access, model access, and API budget. Subscription access does not establish API availability.
2. **Investigate, 20 minutes:** split the four applied tracks among four teammates; the fifth covers foundations and coordinates sources. Agree ownership when starting rather than assume roles.
3. **Synthesize, 10 minutes:** merge evidence, remove repeated material, and identify three to five unresolved problem areas. Preserve disagreement and uncertainty.
4. **Review, 5 minutes:** check citations, recency, accessible language, challenge coverage, and feasibility. Produce the briefing only when this research is explicitly undertaken.

After reading, ask each teammate to propose one problem using this format:

> For **[user]**, **[infrastructure problem]** causes **[observable impact]**. Existing tools leave **[specific gap]**. AI could help by **[capability]**. We could demonstrate it with **[available input]**, compare against **[baseline]**, and measure **[outcome]**.

Discuss proposals against the four equally weighted judging criteria: innovation, applicability, technical complexity and quality, and presentation clarity. Check feasibility separately: one Linux VM, obtainable data, available model access, reusable dependencies and licenses, and a repeatable demo. Ask whether the demo can show an actual before/after result, including a controlled failure case. Keep GPU availability, cloud credentials, and paid APIs as unknowns until checked.

The research is complete when the team can explain the field's main workflows, distinguish evidence from promises, identify credible gaps, and enter brainstorming with shared context. Building, benchmarking prototypes, and choosing the final project belong to the next step.
