# SRE-Healer: Autonomous Incident RCA & Linux VM Remediation

> For **on-call SREs and systems engineers**, we help **diagnose multi-service production incidents and execute safe remediations** using **AI log correlation and bounded diagnostic command execution on Linux hosts**, improving **Mean Time to Resolution (MTTR) and eliminating alert fatigue**.

**Proposed by:** Ricardo · **Status:** Exploring  
**Theme:** AI-assisted operations  
**Date:** 20 November 2026

Duplicate this file as `NN-short-idea-name.md`. Spend 5-10 minutes on the first pass; use short bullets and mark unknowns explicitly. Use the [team briefing](../../ai-cloud-infrastructure-team-briefing.md) for context.

## 1. Problem and user

- **Who encounters this, and when?** On-call Site Reliability Engineers (SREs), DevOps engineers, and Linux system administrators responding to production outages, crash loops, memory leaks, or database connection saturation at 3 AM.
- **What goes wrong today?** When an infrastructure component fails, engineers are inundated with a storm of secondary alerts (e.g. high CPU, HTTP 502, disk queue full, deadlocks). Finding the root cause requires manually jumping between `journalctl`, Docker logs, network sockets (`netstat`/`ss`), and process lists (`ps`/`top`), leading to prolonged service downtime.
- **Current workaround:** Static runbooks (wikis), searching StackOverflow/internal Slack, and executing ad-hoc terminal commands with high risk of human error during high-stress outages.
- **Evidence:** ITBench-AA benchmark results demonstrate that contemporary offline LLM diagnostic pipelines achieve only ~56.2% precision on complex Kubernetes/infrastructure incidents. Commercial tools like AWS DevOps Agent (GA March 2026) advertise fast investigation, but autonomous real-time remediation on generic Linux/bare-metal environments remains an unsolved frontier.

## 2. Proposed solution and AI contribution

- **User workflow:** A service on the Linux VM fails (e.g., memory leak triggers OOM or process lockup) $\rightarrow$ SRE-Healer daemon detects the failure or is invoked via CLI $\rightarrow$ Agent runs non-destructive diagnostic probes (reads logs, checks open ports, memory footprints), correlates symptoms, determines root cause, and proposes a bounded remediation plan $\rightarrow$ Operator approves with one click (or autonomous mode is enabled for pre-authorized safe actions), restoring service health.
- **What AI adds:** Multi-source correlation and hypothesis testing. Rather than relying on rigid if-then alert rules, the agent synthesizes application logs, OS kernel events (`dmesg`), and network state to deduce the underlying root cause, explaining the incident in concise natural language with cited evidence.
- **Simple baseline:** A fixed bash script or systemd watchdog that restarts a service whenever health checks fail.
- **Action boundary:** Bounded execution sandbox. The agent can freely execute whitelisted read-only diagnostic commands (`systemctl status`, `docker logs`, `ss`, `free -m`, `ps aux`), but any mutating command (`kill`, `systemctl restart`, config edits) requires operator approval or strict containment.

## 3. Existing alternatives and difference

| Alternative or workaround | What it already solves | Our specific difference |
|---|---|---|
| HolmesGPT / K8sGPT | Open-source Kubernetes and system investigation CLI using LLMs | HolmesGPT focuses primarily on Kubernetes clusters. SRE-Healer focuses specifically on single-node Linux VMs / bare-metal hosts (like the Leaseweb hackathon environment) with an integrated local human-in-the-loop repair loop. |
| Datadog / New Relic Watchdog | Anomaly detection alerts and APM trace correlation | Commercial SaaS requires extensive agent setup and proprietary licensing; SRE-Healer is lightweight, open-source, and executes real remediation commands directly on the host. |

**Why would this user choose our approach?** SREs get an intelligent co-pilot directly in their Linux terminal that diagnoses chaotic system crashes and safely fixes them in seconds.

## 4. Smallest working demo

**Demo story:** An active web service running in Docker on the Leaseweb Linux VM crashes due to an unhandled file descriptor leak and memory spike. The live demo presenter shows the failing service, invokes SRE-Healer, watches the agent deduce the cause from `dmesg` and app logs, and executes the fix live on stage.

1. **Before:** An intentionally broken demo microservice on the VM triggers HTTP 500 errors. `curl http://localhost:8080/health` returns `Connection Refused` or `Internal Error`.
2. **Intervention:** Execute `sre-healer diagnose`. The agent autonomously executes diagnostic commands, highlights the exact kernel log showing the exhaustion of file descriptors/OOM, and presents a 2-step remediation plan (`prune orphaned workers` + `systemctl restart service`).
3. **After:** The operator types `Y` to confirm; the service is restored, and `curl` confirms HTTP 200 within 5 seconds.

- **Must build:**
  1. Diagnostic probe runner with safe execution whitelist.
  2. Investigation reasoning loop that feeds system state into the LLM.
  3. Interactive terminal TUI (using Python `rich` or `Textual`) displaying real-time agent thoughts and the approval prompt.
- **Out of scope today:** Distributed multi-node cluster failover; automated kernel patching.
- **Success metric:** Mean Time to Diagnose (MTTD) < 15 seconds; successfully restores the broken test service on the Linux VM in 100% of demo runs.
- **Failure case:** If the root cause cannot be determined with >80% confidence, the agent clearly states "Uncertain Cause", dumps gathered evidence, and avoids executing blind remediation actions.
- **Demo fallback:** Pre-scripted failure injection scenario and deterministic fallback diagnostic logs.

## 5. Feasibility on the supplied Linux VM

| Dependency | Proposed approach | Available / Unverified / Blocked |
|---|---|---|
| Data and telemetry | Live Linux VM system logs (`journalctl`, `dmesg`, `/proc`, Docker logs) | Available natively on the provided VM |
| Model and inference | External LLM API (Claude / GPT-4o) via API key, or local lightweight Ollama | Available |
| Infrastructure and permissions | Standard sudo / root access on the Linux VM to run system commands | Available on the Leaseweb VM |
| Libraries and integrations | Python 3.10+, `rich`, `pydantic`, `docker` SDK | Available (open-source) |

**Rough effort and split:**
- Broken service fixture & failure injector: 1 person (Diogo)
- Diagnostic probe execution engine & security whitelist: 1 person (Ricardo)
- Prompt reasoning & RCA correlation: 1 person (Miguel)
- TUI / Live Demo orchestration: 2 people (Francisco & Carolina)
- Hardest integration: Sandboxing mutating commands so a rogue prompt never executes destructive commands like `rm -rf /`.

**Biggest blocker:** Latency of multi-turn tool calling over external API during a live 5-minute pitch.

## 6. Fastest validation

- **Riskiest assumption:** That multi-turn tool-calling LLM can accurately pick the right diagnostic commands (`netstat`, `dmesg`) and diagnose a system error within 15 seconds.
- **Quick experiment:** Inject a port conflict error on the VM (`nc -l 8080`), prompt an LLM with the terminal error, and ask for the diagnostic command to identify the blocking PID.
- **Continue if:** Model correctly identifies `lsof -i :8080` or `ss -tulpn` and diagnoses the conflict.
- **Simplify or park if:** Multi-turn loop is too slow (>30s) or unreliable for a live 5-minute pitch.

## 7. Team decision

Use the [official criteria](../../../00_Context/challenge-and-guidelines.md). Scores are provisional discussion aids, not jury predictions; score each from 1 to 5 with equal weight.

| Criterion | Score | Reason |
|---|---|---|
| Innovation | 4/5 | Hands-on Linux AIOps with live interactive remediation. |
| Applicability | 5/5 | High day-to-day relevance for any infrastructure provider and SRE team. |
| Technical complexity and quality | 4.5/5 | Real Linux systems programming, process inspection, and safe agent execution. |
| Presentation and clarity | 5/5 | **The best possible live demo on stage**: injecting a live crash on the Leaseweb VM and watching the AI fix it in front of the jury. |
| **Total** | **18.5/20** | |

**Decision:** Exploring  
**Reason and next action:** Extremely high live demo score. Build a quick test script to inject a crash and verify diagnostic latency.
