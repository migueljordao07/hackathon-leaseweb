# Ricardo's Hackathon Ideas

Ideas proposed by Ricardo or developed from his research prompts belong in this folder. Each idea card adheres strictly to the official [idea template](../idea-template.md) and addresses key themes of the Leaseweb × Velv hackathon: migration & sovereignty, AI-assisted operations, and security.

The ideas below are ordered by priority and evaluated against market uniqueness and feasibility:

| ID | Idea | Main Question & Focus | Market Uniqueness | Initial Assessment | Relative Effort |
|---|---|---|---|---|---|
| 01 | [SovereignGuard](./01-sovereign-guard.md) | Does our IaC expose data to US CLOUD Act or extraterritorial jurisdiction? | **High (Unserved)** · Existing linters check only geo-regions, not legal sovereignty. | 18/20 | Medium |
| 02 | [SkyShift](./02-skyshift.md) | Can we automatically transpile AWS Terraform into Leaseweb / sovereign cloud HCL? | **High (Unserved)** · Hyperscalers only automate migration *in*, never *out*. | 19/20 | Medium-High |
| 03 | [CloudShrink](./03-cloudshrink.md) | Can an autonomous agent safely identify and prune zombie cloud resources? | **Low (Crowded)** · Heavily addressed by Cloud Custodian, Cast AI, and CSPs. | 16.5/20 | Medium |
| 04 | [SRE-Healer](./04-sre-healer.md) | Can an agent diagnose host-level Linux outages and safely remediate them? | **Medium** · Competing with HolmesGPT and AWS DevOps Agent, but excellent live demo. | 18.5/20 | Medium |
| 05 | [LeastPrivilege AI](./05-least-privilege.md) | Can access logs automatically reduce overly permissive IAM policies to Zero-Trust? | **Low (Covered)** · AWS IAM Access Analyzer already generates policies from CloudTrail. | 15.5/20 | Low-Medium |

## Assessment Summary

- **Top Recommendations for the Hackathon:**
  - **SkyShift (ID 02)** and **SovereignGuard (ID 01)** target completely unaddressed market gaps, align directly with the European sovereignty and EU Data Act themes, and offer immense commercial synergy with Leaseweb's cloud infrastructure business.
  - **SRE-Healer (ID 04)** provides the most dynamic live stage demo (injecting and fixing a crash live on the supplied Leaseweb Linux VM).

Scores are preliminary AI assessments using the four equally weighted [official criteria](../../../00_Context/challenge-and-guidelines.md). They are discussion aids, not jury predictions or team votes.
