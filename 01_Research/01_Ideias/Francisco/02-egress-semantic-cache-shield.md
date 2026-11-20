# SovereignEdge: Egress Elimination & Semantic Traffic Shield for European IaaS

> For **enterprises operating hybrid workloads between AWS/GCP and European IaaS (Leaseweb)**, we help **slash exorbitant hyperscaler egress fees and latency** using **real-time AI semantic traffic caching and intelligent bandwidth routing**, improving **operational cost efficiency by up to 70% while keeping data traffic localized in Europe**.

**Proposed by:** Francisco · **Status:** Exploring (High FinOps Value)  
**Theme:** Hyperscaler alternatives / sovereignty & AI-assisted cloud infrastructure  

---

## 1. Problem and user

- **Who encounters this, and when?**  
  CTOs and engineering teams running data-heavy workloads, AI microservices, or hybrid multi-cloud architectures connecting services on AWS/Azure with on-premises or European bare-metal infrastructure (Leaseweb).
- **What goes wrong today?**  
  Hyperscalers weaponize **Data Egress Fees (Data Transfer Out)**: hosting compute on AWS is expensive, but leaving or pulling data out of AWS to European infrastructure costs up to \$0.09 per gigabyte. For companies processing millions of API calls, vector embeddings, or database queries, egress bills become financial traps. Furthermore, traditional HTTP caches (Redis, Varnish) fail because dynamic API payloads include shifting timestamps, request IDs, or slight parameter variations that invalidate exact-match hash keys.
- **Current workaround:**  
  Paying punitive egress bills, attempting brittle custom query caching scripts, or surrendering entirely to single-vendor hyperscaler lock-in.
- **Evidence:**  
  - FinOps Foundation 2026 reports identify egress fees and unpredicted AI API traffic transfer as the fastest-growing source of cloud waste.
  - Leaseweb’s core competitive advantage is providing enterprise-grade, unmetered or high-bandwidth European network transit at a fraction of hyperscaler pricing.

---

## 2. Proposed solution and AI contribution

- **User workflow:**  
  1. **Proxy:** A high-performance reverse proxy running on the Leaseweb Linux VM intercepts outbound API, database, and model inference requests.
  2. **Semantic Reasoning:** Instead of exact-string hashing, a lightweight embedding/similarity model evaluates incoming queries and schemas semantically.
  3. **Local Cache Hit:** If an inbound request is semantically equivalent to a recent query (e.g., retrieving the same customer record or knowledge base segment with minor parameter formatting differences), SovereignEdge fulfills the request from local fast storage on the Leaseweb VM.
  4. **Egress Savings Dashboard:** The system displays live metrics: total megabytes saved from crossing hyperscaler transit, cost savings in Euros, and response latency reduced from ~350ms to <10ms.
- **What AI adds:**  
  Semantic similarity matching on unstructured query payloads, dynamic TTL (Time-To-Live) estimation based on data volatility, and automatic query normalization that standard caching engines cannot achieve.
- **Simple baseline:**  
  Standard Nginx or Redis reverse proxy with exact URI hashing, which scores a <15% hit rate on dynamic API traffic due to changing timestamps and dynamic tokens.
- **Action boundary:**  
  - **Read:** HTTP/REST request bodies and headers passing through the local proxy.
  - **Recommend:** Cache policy adjustments and identified duplicate egress routes.
  - **Change:** Serves cached responses locally; forwards non-cached traffic transparently to the upstream provider with zero protocol alteration.

---

## 3. Existing alternatives and difference

| Alternative or workaround | What it already solves | Our specific difference |
|---|---|---|
| **Cloudflare Workers / CDN Cache** | Edge caching for static assets. | Proprietary US edge provider; does not perform semantic payload similarity on dynamic API queries; subjects metadata to US jurisdiction. |
| **GPTCache (Open Source)** | Semantic caching specifically for OpenAI LLM prompts. | Specialized exclusively for raw prompt tokens; SovereignEdge generalizes semantic caching to arbitrary structured JSON APIs, microservices, and egress data streams. |
| **Standard Redis / Memcached** | Exact key-value in-memory storage. | Zero semantic awareness; a single altered query param (like `?sort=asc` or a timestamp) triggers a full cache miss and costly hyperscaler egress call. |

**Why would this user choose our approach?**  
It directly capitalizes on Leaseweb's cost-effective European bandwidth to break hyperscaler egress extortion, saving thousands of euros every month on dynamic API and data pipelines.

---

## 4. Smallest working demo

**Demo story:**  
A microservice running on the Leaseweb VM repeatedly queries an external API hosted on AWS that charges per query and egress transfer.

1. **Before:** The client script makes 100 queries with minor semantic variations (e.g., different ordering, identical underlying questions with varied phrasing). Latency averages 400ms per call, and every request registers an egress cost.
2. **Intervention:** The requests route through the SovereignEdge proxy. The local AI module matches semantic intent, normalizes parameters, and caches valid responses locally.
3. **After:** Out of 100 queries, 78 are served locally in 4ms with 0€ egress cost. The live dashboard shows: *"Egress Avoided: 142 MB | Cost Saved: €48.20/hour equivalent | European Data Retention: 100%"*.

- **Must build:**  
  1. A lightweight Python FastAPI reverse proxy routing upstream HTTP calls.
  2. An embedding-based semantic matching layer (using a fast local sentence-transformer or lightweight API).
  3. A real-time dashboard displaying latency diffs, cache hit rates, and cumulative egress savings.
- **Out of scope today:**  
  Complex distributed multi-region cache synchronization, binary protocol gRPC parsing.
- **Success metric:**  
  Achieve >70% cache hit rate on semantically equivalent dynamic queries with <15ms local response time.
- **Failure case:**  
  If the semantic similarity model is uncertain (<85% confidence score), the proxy automatically bypasses the cache and fetches fresh data from upstream to guarantee zero stale data bugs.
- **Demo fallback:**  
  A pre-recorded playback trace of synthetic API requests demonstrating immediate cache acceleration without relying on external upstream APIs.

---

## 5. Feasibility on the supplied Linux VM

| Dependency | Proposed approach | Available / Unverified / Blocked |
|---|---|---|
| Data and telemetry | Synthetic client request generator with realistic API variations | Available |
| Model and inference | Local ONNX / SentenceTransformers embedding runtime or Claude API | Available |
| Infrastructure & permissions | Supplied Linux VM with standard Python runtime | Available |
| Libraries and integrations | Python 3.11, FastAPI, `httpx`, `numpy`, SQLite / local cache | Available |

**Rough effort and split:**  
- *Reverse Proxy Engine (2 people):* Request interception, header handling, upstream forwarding.  
- *Semantic Matching Engine (1 person):* Embedding similarity pipeline, TTL cache eviction.  
- *Dashboard & FinOps Visuals (1 person):* Live stream graph, cost calculator, latency comparison.  
- *Client Traffic Generator & Pitch (1 person):* Realistic query workloads, slides, financial pitch narrative.  

**Biggest blocker:**  
Inference latency of local embedding models on CPU-only VMs. (Mitigated by using lightweight quantized models like `all-MiniLM-L6-v2` via ONNX, achieving <5ms inference on standard CPUs).

---

## 6. Fastest validation

- **Riskiest assumption:**  
  Can an embedding model running on a CPU-only Linux VM perform semantic cache lookups in under 10ms?
- **Quick experiment:**  
  Run a 10-line Python script benchmarking `all-MiniLM-L6-v2` cosine similarity across 50 sample query vectors on the VM.
- **Continue if:**  
  Similarity comparison completes in <10ms.
- **Simplify or park if:**  
  CPU latency exceeds 50ms, negating the caching benefit.

---

## 7. Team decision

| Criterion | Score | Reason |
|---|---|---|
| Innovation | 4.5 | Brings semantic AI caching out of narrow LLM prompt use-cases into broad cloud infrastructure and network egress optimization. |
| Applicability | 5.0 | Directly addresses the #1 financial pain point of multi-cloud engineering: hyperscaler data transfer fees. |
| Technical complexity and quality | 4.5 | Combines high-speed proxy networking, vector similarity, and real-time FinOps math. |
| Presentation and clarity | 4.5 | Extremely easy to understand financially: shows clear euros saved on a live dashboard. |
| **Total** | **18.5 / 20** | |

**Decision:** **Shortlisted / High FinOps Value**  
**Reason and next action:** Excellent complementary project highlighting Leaseweb's network bandwidth superiority.
