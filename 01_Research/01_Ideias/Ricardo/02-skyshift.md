# SkyShift: Hyperscaler-to-Sovereign Cloud Migration & IaC Transpiler

> For **infrastructure teams trapped in AWS or Azure vendor lock-in**, we help **translate proprietary cloud configurations (Terraform/CloudFormation) into European sovereign cloud architectures (Leaseweb/OpenStack)** using **AI-guided semantic schema translation and cost-saving estimation**, improving **migration velocity from weeks to minutes while cutting egress and compute costs**.

**Proposed by:** Ricardo · **Status:** Shortlisted  
**Theme:** Migration & sovereignty  
**Date:** 20 November 2026

Duplicate this file as `NN-short-idea-name.md`. Spend 5-10 minutes on the first pass; use short bullets and mark unknowns explicitly. Use the [team briefing](../../ai-cloud-infrastructure-team-briefing.md) for context.

## 1. Problem and user

- **Who encounters this, and when?** CTOs, DevOps leads, and infrastructure engineers who want to migrate workloads away from AWS/Azure to European providers (such as Leaseweb or OpenStack-based sovereign private clouds) to cut costs and comply with European sovereignty requirements.
- **What goes wrong today?** Even though the EU Data Act eliminates switching egress fees by 2027, architectural lock-in remains immense. Translating AWS-specific VPCs, security groups, EC2 instance types, and proprietary S3/RDS declarations into generic OpenStack or Leaseweb configurations requires manual refactoring of hundreds of Terraform lines, risking misconfiguration, security regressions, and unexpected downtime.
- **Current workaround:** Manual line-by-line rewrite by senior cloud architects, or hiring expensive cloud migration consultants with engagements lasting months.
- **Evidence:** AWS Transform for VMware (GA May 2025) and October 2026 updates show massive investments in automating migration *into* AWS, but hyperscalers offer zero tooling to migrate *out* into independent European infrastructure. OpenTofu documentation confirms that while the IaC engine is open, resource declarations remain tightly coupled to proprietary provider schemas.

## 2. Proposed solution and AI contribution

- **User workflow:** Operator inputs an existing AWS Terraform project (e.g. EC2 instance + VPC + Security Group + RDS/S3) $\rightarrow$ SkyShift's semantic translation agent analyzes the architecture and maps proprietary resources to Leaseweb / OpenStack primitives $\rightarrow$ Outputs verified, ready-to-deploy sovereign Terraform manifests, accompanied by an executive cost & sovereignty comparison report.
- **What AI adds:** Beyond simple 1:1 resource lookup tables, LLMs understand composite architectures (e.g., recognizing that an AWS ALB + Target Group + EC2 Autoscaling Group can be mapped to an HAProxy / Keepalived or Leaseweb Load Balancer configuration) and adapt network CIDRs, disk attach points, and cloud-init scripts.
- **Simple baseline:** A static regex/lookup dictionary mapping `t3.medium` $\rightarrow$ `s2.c2m4` and replacing `aws_instance` with `openstack_compute_instance_v2`.
- **Action boundary:** Reads input Terraform/HCL; produces translated HCL code and cost estimation summaries. Does not automatically execute destructive actions on the source cloud.

## 3. Existing alternatives and difference

| Alternative or workaround | What it already solves | Our specific difference |
|---|---|---|
| AWS Transform / Azure Migrate | Automated migration of VMware and on-prem workloads *into* their respective proprietary clouds | **Market Gap:** Hyperscaler tools are strictly one-way to capture workloads. No dedicated automated tool exists in the market to transpile AWS/Azure Terraform directly to European sovereign cloud providers (Leaseweb/OpenStack). Engineers currently do this manually or paste into generic chat interfaces. |
| Terraformer / Infracost | Terraformer imports existing cloud state into HCL; Infracost estimates AWS/GCP bills | SkyShift combines cross-provider schema transpilation with an instant Leaseweb cost-benefit projection. |

**Why would this user choose our approach?** Provides an immediate, low-friction path to escape hyperscaler lock-in, generating production-grade European sovereign cloud manifests in seconds.

## 4. Smallest working demo

**Demo story:** An engineer provides an AWS Terraform file containing an EC2 instance, security group, and S3 bucket. SkyShift transpiles it into equivalent Leaseweb / OpenStack HCL, validates the syntax with OpenTofu, and demonstrates that the exact same application can boot up on the local Linux VM / Leaseweb environment for 60% less cost.

1. **Before:** Show an AWS Terraform configuration (`aws_instance`, `aws_security_group`, `aws_s3_bucket`) tied to US infrastructure.
2. **Intervention:** Run `skyshift transpile --source aws --target leaseweb ./aws-stack/`. The AI agent maps dependencies, translates schemas, substitutes S3-compatible endpoints, and outputs clean target HCL.
3. **After:** The generated HCL passes `tofu validate` successfully; the CLI displays a financial diff: "AWS Estimated Cost: €184/mo $\rightarrow$ Leaseweb/Sovereign Cost: €72/mo (61% savings)".

- **Must build:**
  1. HCL extractor and resource mapper (AWS to Leaseweb/OpenStack).
  2. Prompt-driven transpilation engine with structured JSON/HCL outputs.
  3. Syntax validator and cost-differential comparison summary.
- **Out of scope today:** Automatic live data synchronization (petabyte database replication); support for proprietary hyperscaler serverless runtimes (AWS Lambda with proprietary layers).
- **Success metric:** Successfully transpiles a 3-resource AWS Terraform configuration into valid OpenStack/Leaseweb HCL that passes `tofu validate` on the VM without human correction.
- **Failure case:** If the LLM generates unsupported attributes, the validator flags the exact line and provides a documented template fallback for that resource.
- **Demo fallback:** Pre-cached AWS source HCL and verified translated OpenStack/Leaseweb targets.

## 5. Feasibility on the supplied Linux VM

| Dependency | Proposed approach | Available / Unverified / Blocked |
|---|---|---|
| Data and telemetry | Synthetic but realistic AWS Terraform modules (Web tier + DB + Storage) | Available |
| Model and inference | OpenAI / Claude API or local Ollama on VM | Available |
| Infrastructure and permissions | Linux VM with Python 3.10+, OpenTofu CLI installed | Available |
| Libraries and integrations | `python-hcl2`, `jinja2`, `rich`, `opentofu` binary | Available (open-source) |

**Rough effort and split:**
- AST/HCL Parser & Prompt Engineer: 2 people (Miguel & Diogo)
- OpenStack / Leaseweb resource mapping & validation harness: 2 people (Francisco & Ricardo)
- Pitch, cost model, and interactive terminal/web UI: 1 person (Carolina)
- Hardest integration: Handling security group rule translation and egress/ingress port mapping accurately.

**Biggest blocker:** Network connectivity from the Linux VM to external LLM APIs if outbound internet is restricted.

## 6. Fastest validation

- **Riskiest assumption:** That LLM can accurately map AWS security groups and network configurations to OpenStack/Leaseweb provider syntax without creating open security holes.
- **Quick experiment:** Translate an AWS Security Group (`aws_security_group` with port 80/443 ingress) to `openstack_networking_secgroup_rule_v2` using Claude/GPT and run `tofu validate`.
- **Continue if:** Generated HCL passes validation and preserves security boundaries.
- **Simplify or park if:** Complex networking translation fails repeatedly; narrow down to pure compute (EC2 $\rightarrow$ Leaseweb VM) and storage (S3 $\rightarrow$ MinIO/Ceph).

## 7. Team decision

Use the [official criteria](../../../00_Context/challenge-and-guidelines.md). Scores are provisional discussion aids, not jury predictions; score each from 1 to 5 with equal weight.

| Criterion | Score | Reason |
|---|---|---|
| Innovation | 5/5 | Directly tackles the hardest aspect of sovereign cloud adoption: IaC refactoring. |
| Applicability | 5/5 | Direct commercial utility for hosting providers like Leaseweb to acquire enterprise customers. |
| Technical complexity and quality | 4/5 | Real IaC AST parsing, cross-cloud abstraction mapping, and automated validation. |
| Presentation and clarity | 5/5 | Compelling business story: "Drop your AWS code here, save 60%, and run on sovereign European cloud in 2 minutes". |
| **Total** | **19/20** | |

**Decision:** Shortlisted  
**Reason and next action:** Prime contender for the hackathon grand prize given its direct synergy with Leaseweb's core cloud offering. Build a proof-of-concept translation script.
