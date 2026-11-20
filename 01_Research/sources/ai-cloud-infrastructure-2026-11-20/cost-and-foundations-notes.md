# Cost, Efficiency, and Foundations: Evidence Notes

Snapshot and access date: **2026-11-20**. Primary-source desk research only; no product, benchmark, API, or deployment was exercised.

## F1. Telemetry foundations

- **Source:** OpenTelemetry, [Signals](https://opentelemetry.io/docs/concepts/signals/), modified 2026-03-10.
- **Locator:** Signals; Traces; Metrics; Logs.
- **Evidence:** "collect, process, and export" (5 quoted words).
- **Documented capability:** OpenTelemetry handles system/application telemetry. Logs record events, metrics measure runtime behavior, and traces follow requests. It supplies diagnostic inputs, rather than an AI diagnosis or storage backend by itself.
- **Inference:** an assistant needs relevant observations and identifiers to connect symptoms to dependencies. More fluent explanations cannot compensate for absent evidence.

## F2. Practitioner priorities, not an effectiveness benchmark

- **Source:** FinOps Foundation, [State of FinOps 2026](https://data.finops.org/), released 2026-02-19 according to the Foundation's [release announcement](https://www.linuxfoundation.org/press/state-of-finops-survey-ai-value-and-skills-top-priorities-as-finops-matures-across-technology-value-98-manage-ai-90-saas-64-licensing-48-data-center-1).
- **Locator:** About; AI; desired tool capabilities.
- **Evidence:** "Granular monitoring of AI spend" (6 quoted words).
- **Survey result:** the report covers 1,192 respondents; questions use different respondent subsets. It distinguishes managing AI spending from using AI for FinOps. Desired capabilities include detailed AI-spend visibility, architecture costing before deployment, and consolidated technology-cost views.
- **Limit:** the technology-category question combines current management and future plans, while the executive text abbreviates this. Avoid a universal adoption percentage. This is a community survey, not proof of AI savings or a representative census of all cloud users.

## F3. Commercial resource recommendations and their limits

- **Source:** Google Cloud, [Apply machine type recommendations to VM instances](https://docs.cloud.google.com/compute/docs/instances/apply-machine-type-recommendations-for-instances), updated 2026-11-10.
- **Locator:** opening; Limitations and use cases; How machine type recommendations work.
- **Evidence:** "previous 8 days" (3 quoted words).
- **Documented capability:** Compute Engine recommends VM resizing using recent CPU/memory observations. Infrequent monthly peaks and brief spikes can be missed. Recommendation estimates extrapolate a historical period and are not demonstrated savings.
- **Requirements:** Compute Engine resources, monitoring data, and project permissions; optional agent supplies memory detail. This is an existing automated optimization baseline. The inspected page does not establish that a generative LLM is used.
- **Inference:** a workload narrative or suggested resize should be tested against a simple rule and a latency/error constraint, rather than judged by a projected bill alone.

## F4. Open-source cost measurement

- **Sources:** OpenCost [FAQ](https://opencost.io/docs/faq/) and [installation requirements](https://opencost.io/docs/installation/install/), undated living documentation.
- **Locator:** FAQ: What is OpenCost?, payment/license, determination of costs; installation: Requirements.
- **Evidence:** FAQ: "measuring and allocating Kubernetes and cloud infrastructure costs" (9 quoted words); installation: "requires Prometheus" (2 quoted words).
- **Documented capability:** OpenCost is Apache-2.0 software for cost measurement/allocation; the allocation deployment needs Kubernetes and Prometheus. This is an open-source data foundation, not evidence of autonomous AI optimization. Full allocation setup should not be assumed lightweight for an unexamined VM; the separate Docker path does not provide Kubernetes allocation.
- **Limit:** some FAQ version references are historical. No latest-release, install-time, or resource-capacity claim is made.

## Research synthesis

The useful question is whether AI adds explanation, prioritization, or task completion over an existing measurement/optimization baseline. A one-day experiment could use a labeled usage fixture, documented price assumptions, and a fixed resource rule. Compare recommendations with and without AI, keeping estimated cost separate from observed application performance and including model latency/usage. These are proposed evaluation methods, not measured outcomes or proof of an unserved market.
