# Security and Data Protection: Research Notes

Snapshot and access date: **20 November 2026**. Primary-source desk research; no products installed or benchmarks reproduced. Examples below describe capabilities, not proof of operational effectiveness.

## SEC-01: Commercial AI alert triage

- **Source:** Microsoft Learn, [Deploy AI agents in Microsoft Defender](https://learn.microsoft.com/en-us/defender-xdr/security-copilot-agents-defender). Last updated **12 November 2026**.
- **Locator:** Security Alert Triage Agent (Preview), permissions/licensing table; prerequisites.
- **Short evidence:** "cloud and identity alerts (preview)".
- **Verified capability:** The agent classifies supported alerts, explains verdicts, and accepts analyst feedback. Email/collaboration triage is generally available; cloud/identity triage is preview. Access requires a provisioned Security Copilot workspace with capacity, relevant Defender products, and permissions including alert management. Setup requires Security Administrator.
- **Limit:** Documentation establishes features and access requirements, not cloud-alert accuracy. It is a managed Microsoft workflow, not a standalone Linux component. No independent cloud-alert evaluation established here.

## SEC-02: Existing deterministic configuration scanning

- **Source:** Aqua Security, [Trivy misconfiguration scanning](https://trivy.dev/docs/latest/guide/scanner/misconfiguration/). Living documentation; publication/update date not displayed.
- **Locator:** Misconfiguration Scanning; Scan raw configurations; External connectivity.
- **Short evidence:** "built-in checks to detect configuration issues".
- **Verified capability:** Trivy checks Docker, Kubernetes, Terraform, and other infrastructure-as-code files; custom checks are possible. Misconfiguration scanning must be enabled explicitly for image/filesystem/repository commands. Its common representation cannot expose every resource or attribute to checks. Checks bundles require internet access unless offline operation is prepared.
- **Baseline:** Run deterministic checks on known-bad configurations; compare AI-assisted prioritization or proposed fixes against the scanner's original findings and a rescan. Do not call the scanner itself generative AI.

## SEC-03: Scanner reuse and deployment

- **Source:** Aqua Security, [Trivy repository](https://github.com/aquasecurity/trivy). Living main branch; no immutable release pinned in this research.
- **Locator:** License; Quick Start; scanner/target lists.
- **Short evidence:** "Apache-2.0 license".
- **Verified capability:** The project provides scanners for known vulnerabilities, misconfigurations, secrets, and software licenses. It supports binary or container deployment and filesystem/repository inputs. A local configuration fixture can therefore provide a demonstration input without production cloud credentials.
- **Limit:** Pin and inspect an actual release before building. No installation, resource test, or license audit of transitive dependencies was performed.

## SEC-04: Untrusted operational context can steer agents

- **Source:** OWASP GenAI Security Project, [LLM01:2025 Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/). **2025 edition**; page publication date not displayed.
- **Locator:** Indirect Prompt Injections; Prevention and Mitigation Strategies, items 4-7.
- **Short evidence:** "minimum necessary for its intended operations".
- **Verified guidance:** External files or websites can carry instructions that influence an LLM. Retrieval-augmented generation does not remove this risk. OWASP recommends privilege limits, deterministic validation, approval for privileged actions, segregation of external content, and adversarial testing.
- **Application/inference:** Treat logs, runbooks, and scanner descriptions as untrusted data. Let code enforce allowed operations; do not depend on a prompt alone to prevent dangerous execution. A malicious-log demonstration tests this boundary, not universal immunity.

## SEC-05: Measured benefits exist, within narrow experiments

- **Source:** James Bono, Microsoft, [Randomized Controlled Trials for Phishing Triage Agent](https://arxiv.org/html/2511.13860v1), arXiv v1 submitted **17 November 2025**.
- **Locator:** Introduction; Methodology; Abstract.
- **Short evidence:** "167 external security analysts".
- **Research result:** The Microsoft-authored study compared manual and assisted phishing triage using curated email artifacts and synthetic false agent verdicts. It reports up to 6.5 times more true positives per analyst minute; queue prioritization explains most estimated productivity gains. Some outcomes combine measured analyst behavior with a modeled protocol that hides benign-classified items.
- **Limit:** This is vendor-authored, task-specific evidence, not an independent test of autonomous cloud remediation. Do not generalize its headline to infrastructure security or describe the modeled productivity factor as a blanket production result.

## SEC-06: Restoration has an existing non-AI baseline

- **Source:** AWS, [Restore testing validation](https://docs.aws.amazon.com/aws-backup/latest/devguide/restore-testing-validation.html). Living developer documentation; date not displayed.
- **Locator:** Set up validation workflow.
- **Short evidence:** "validation that runs when a restore testing job completes".
- **Verified capability:** AWS Backup can trigger a custom validation workflow through EventBridge after restoration; a documented example is an EC2 health endpoint check. The workflow reports validation status separately.
- **Implication:** Automated restoration testing is established functionality and does not inherently require AI. For a local demo, deterministic integrity and application checks should decide whether recovery worked. AI could explain a failed check or propose additional tests; that added value remains a team hypothesis.

## Evidence-backed problem areas to discuss

These are **team hypotheses**, not findings that no competing product exists:

1. **Context-aware fix review:** operators receive scanner findings, but still need to understand impact and whether a proposed change removes the issue without breaking the application. Demonstrate one local IaC/configuration case, show evidence, apply an approved patch, and rescan. Measure correct fixes and regressions against scanner-only guidance.
2. **A constrained incident assistant:** an agent consumes normal and malicious operational text. Demonstrate whether untrusted content can trigger a prohibited action; compare an unrestricted prototype with code-enforced read-only/allowlisted tools. Measure blocked unauthorized attempts and retained diagnostic usefulness. OWASP supports the threat model, not guaranteed defense success.
3. **Recovery evidence:** a successful restore job can still require application validation. Restore a small disposable service or database, run deterministic checks, then ask AI to explain a deliberately failed test. Measure detection and explanation correctness; explicitly compare against a scripted recovery checklist.

## Coverage limits

No current CVE catalogue, regulated-compliance conclusion, population-wide security adoption estimate, or production accuracy guarantee is inferred. Microsoft preview access and license availability are unverified for the team. Trivy's current release and actual Linux resource needs must be checked before implementation. Recovery and constrained-tool designs can be demonstrated locally, but usefulness and novelty require testing and competitor comparison.
