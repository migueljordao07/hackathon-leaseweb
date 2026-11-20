# LeastPrivilege AI: Automated Zero-Trust IAM & Security Group Hardening

> For **cloud security engineers and platform administrators**, we help **eliminate wildcard permissions, overly broad security groups, and dormant cloud access** using **AI-driven log-to-policy reduction**, improving **cloud posture security and preventing data exfiltration**.

**Proposed by:** Team · **Status:** Exploring  
**Theme:** Security & data protection

## 1. Problem and user

- **Who encounters this, and when?** Cloud security engineers, SecOps leads, and DevOps practitioners managing sprawling IAM roles, Service Principals, and Security Groups across AWS, Azure, or private clouds.
- **What goes wrong today?** During development and rapid feature deployment, teams routinely grant broad permissions (e.g. `Action: "*"` or `AdministratorAccess`) and open security groups to the entire internet (`0.0.0.0/0`) to "just make things work". Over time, this creates massive "privilege creep" and dormant attack paths that attackers exploit for lateral movement, ransomware, and data exfiltration.
- **Current workaround:** Static IAM analyzers (e.g. AWS IAM Access Analyzer) or generic CSPMs that spit out thousands of low-context alerts without offering automated, verified policy reduction code.
- **Evidence:** Cloud security incident postmortems consistently list over-permissioned IAM credentials and exposed ports (22, 3389, 5432) as the top initial compromise vectors. OWASP Cloud Security and Kubernetes hardening guides stress least-privilege as mandatory for compliance with ISO 27001, SOC2, and NIS2.

## 2. Proposed solution and AI contribution

- **User workflow:** Operator inputs an over-permissive IAM policy JSON or Terraform security group junto with simulated/real access logs (e.g. CloudTrail or VPC Flow Logs) $\rightarrow$ LeastPrivilege AI analyzes which specific actions and IPs were actually used vs. which were granted $\rightarrow$ Generates an optimal, hardened "Zero-Trust" policy that strictly retains required business functions while pruning all wildcard and unused access vectors.
- **What AI adds:** Understanding intent and business logic. Traditional tools struggle with dynamic permissions or complex wildcards; an LLM understands service context (e.g., "This service only needs to read objects from bucket `prod-reports`; the granted `s3:*` and `iam:PassRole` permissions are completely unused and represent a severe privilege escalation risk") and synthesizes precise, minimal policy JSON.
- **Simple baseline:** A deterministic script that greps unique API calls from access logs and matches them to an IAM action whitelist.
- **Action boundary:** Analysis and policy artifact generation only. Proposes updated IAM policy JSONs and Terraform diffs; never revokes live production credentials without explicit administrative approval.

## 3. Existing alternatives and difference

| Alternative or workaround | What it already solves | Our specific difference |
|---|---|---|
| AWS IAM Access Analyzer / Cloudsplaining | Identifies overly broad IAM policies and public resources | Passive scanning; LeastPrivilege AI takes access logs, calculates exact delta, and auto-generates the minimal hardened replacement policy code. |
| Permify / OPA (Open Policy Agent) | Enforces authorization policies at runtime | Requires custom Rego code and pre-planning; LeastPrivilege AI operates retroactively on existing messy cloud code to bring it into compliance. |

**Why would this user choose our approach?** Fixes years of accumulated cloud permission tech debt in minutes without breaking running applications.

## 4. Smallest working demo

**Demo story:** A security engineer presents an overly permissive IAM policy for an analytics worker service (granted full S3, DynamoDB, and IAM access). LeastPrivilege AI analyzes the service's recent access logs, detects that 95% of permissions are dormant (including dangerous escalation paths), and produces a clean, minimal IAM policy and Terraform patch.

1. **Before:** Show a high-risk IAM policy containing `Action: ["s3:*", "iam:*"]` on `Resource: "*"`. Security score is critical (F grade).
2. **Intervention:** Run `least-privilege analyze --policy ./iam-policies/worker.json --logs ./access-logs/audit.jsonl`. The AI agent maps observed calls against granted permissions and highlights high-risk attack surfaces.
3. **After:** The tool outputs a hardened, scoped-down IAM policy JSON with exact bucket ARNs and read-only actions, accompanied by an "Attack Surface Reduction: 94%" scorecard.

- **Must build:**
  1. Policy & log ingestion parser (handling IAM JSON format and audit access logs).
  2. Policy minimization and intent-reasoning engine.
  3. Visual terminal / markdown diff generator showing eliminated permissions.
- **Out of scope today:** Live AWS API sync and automated policy detachment; multi-cloud Azure RBAC cross-compilation.
- **Success metric:** 100% elimination of uncalled high-privilege actions while retaining 100% of legitimate business actions in test fixtures; generation time < 10 seconds.
- **Failure case:** If the log sample is too short to prove usage, the agent flags unobserved actions as "Potentially Dormant - Review Required" rather than aggressively breaking production workflows.
- **Demo fallback:** Static policy JSON and pre-compiled access log fixtures.

## 5. Feasibility on the supplied Linux VM

| Dependency | Proposed approach | Available / Unverified / Blocked |
|---|---|---|
| Data and telemetry | Synthetic IAM policy JSON files and CloudTrail access log JSONL snippets | Available |
| Model and inference | External LLM API (OpenAI / Claude) via API key | Available |
| Infrastructure and permissions | Linux VM running Python 3.10+ | Available |
| Libraries and integrations | Python standard library, `pydantic`, `rich` | Available |

**Rough effort and split:**
- IAM & log parsing fixtures: 1 person (Ricardo)
- Prompt engineering & policy reduction logic: 2 people (Miguel & Francisco)
- Visual diffing & presentation deck: 2 people (Carolina & Diogo)
- Hardest integration: Accurately mapping CloudTrail API call event names to corresponding IAM action names (e.g. `GetObject` $\rightarrow$ `s3:GetObject`).

**Biggest blocker:** Complex IAM condition blocks or cross-account trust relationships exceeding prompt context.

## 6. Fastest validation

- **Riskiest assumption:** That LLM can accurately map logged API operations to strict IAM permission statements without dropping needed edge-case privileges.
- **Quick experiment:** Provide an LLM with 10 logged S3 read events and an `s3:*` policy, asking it to output the minimal policy. Verify if it correctly isolates `s3:GetObject` and `s3:ListBucket`.
- **Continue if:** Model correctly restricts permissions without dropping required read access.
- **Simplify or park if:** Model hallucinates non-existent IAM actions or drops necessary permissions.

## 7. Team decision

| Criterion | Score | Reason |
|---|---|---|
| Innovation | 3.5/5 | Useful AI application to policy generation, though policy generators exist. |
| Applicability | 4.5/5 | Security teams are desperate for automated IAM cleanup tools. |
| Technical complexity and quality | 3.5/5 | Clean JSON-to-JSON transformation and log filtering. |
| Presentation and clarity | 4/5 | Intuitive "Before vs After" attack surface reduction metric. |
| **Total** | **15.5/20** | |

**Decision:** Shortlist  
**Reason and next action:** Solid security idea; easy to build as a backup if the team wants a pure cybersecurity angle.
