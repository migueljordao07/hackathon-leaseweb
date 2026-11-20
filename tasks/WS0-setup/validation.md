# Human VM validation record

Status: CHECKS RUN by agent `claude-3` on the demo VM; human decision pending. Only a human completes WS0-01; values below are sanitized (no credentials, IPs, hostnames or usernames).

## Environment and timebox

Operator: agent `claude-3` on behalf of Miguel (human sign-off below). VM: Ubuntu 26.04.1 LTS, kernel 7.0, x86_64, 32 vCPU, 125 GiB RAM, 86 GB free; Python 3.14.4; git 2.53.0; rclone v1.60.1 (apt); OpenTofu v1.9.1 (release binary); moto 5.2.5 + boto3 1.44.7 in a venv; no Docker (not needed). Outbound HTTPS to github.com, pypi.org, registry.opentofu.org and ip-ranges.amazonaws.com: HTTP 200. Repo commit on VM: 45fbbf8. Checks window: 2026-11-20 14:06–14:16 UTC (VM clock), within the 30-minute timebox. Provider choice: OpenStack (Leaseweb Public Cloud, Keystone v3 at identity.leasewebcloud.com). Secrets loaded only inside processes from a 0600 file outside the repo. Local services bind 127.0.0.1 only (Moto on 5000; probe proxy on an ephemeral loopback port).

## 1. Moto and target put/get/list

Command: `(set -a; . ./vm.env; set +a; venv/bin/python check1.py <ts>)` with explicit boto3 clients for Moto (`http://127.0.0.1:5000`) and the Leaseweb S3 bucket, writing only under `skyshift-gate/<ts>/`.
Time: 14:08:40 UTC. Exit code: 0.
Measured: Moto: put ok, get bytes_equal=True (4109 B), list contains=True, 0.02 s. Leaseweb bucket: put ok, get bytes_equal=True (4109 B), list contains=True, 0.08 s.
Result: **PASS**. Limitation: path-style addressing; single small object. Fallback: self-hosted S3 server on the VM (not needed).

## 2. rclone and SHA-256 of 10 objects

Commands: seed 10 random objects (1000–72271 B, 366355 B total) into Moto; `rclone copy --s3-no-check-bucket src:skyshift-src/skyshift-gate/<ts>/rclone dst:<bucket>/skyshift-gate/<ts>/rclone` (remotes from env vars); then `check2.py verify` lists both sides with pagination and streams every object through hashlib.sha256 (no ETags).
Time: 14:08:56–14:08:57 UTC. Exit codes: rclone 0, verify 0.
Measured: source_count=10 target_count=10 matched=10 missing=0 different=0 extra=0; per-object sizes and SHA-256 equal for obj00..obj09.
Result: **PASS**. Limitation: synthetic objects only; rclone 1.60.1 from Ubuntu archive. Fallback: none needed.

## 3. OpenTofu init and validate

Probe: 10-line `main.tf` with `terraform-provider-openstack/openstack ~> 3.0` and one `openstack_networking_secgroup_v2` resource, in `~/skyshift-gate/tofu` (disposable, outside the repo). No apply.
Time: 14:09:41–14:09:42 UTC.
Measured: `tofu init` exit 0 (registry reachable; installed openstack v3.4.0, signed). `tofu validate` exit 0 ("The configuration is valid"). `tofu plan` exit 0 ("Plan: 1 to add"), BUT a direct Keystone v3 password-auth request with the same credentials returned HTTP 401 using domain `Default`: the plan did not prove authentication (the provider did not need an API call to plan a create).
Result: **init/validate PASS; authenticated plan FAIL (401)**. Limitation: the Leaseweb KB states user/project domain must be the customer ID, which is not in the supplied notes. Fallback: translate with `tofu validate` only; apply stays out of scope.

## 4. EU-hosted model JSON and latency

Measured: the supplied Leaseweb GPU server answers only SSH (port 22); no OpenAI-compatible endpoint on 80/443/3000/5000/7860/8000/8080/11434/30000. Over SSH: Ubuntu 26.04.1, `nvidia-smi` not found (no GPU driver), no model server process listening.
Fallback test (14:15 UTC): `skyshift.llm.complete` with an unreachable endpoint returns `mode: replay`, `status: incomplete` in 0.02 s, with errors "live model transport failed" and "served labelled replay instead; no live model response was used".
Result: **NOT RUN** (no model endpoint exists). Fallback: labelled replay from `fixtures/llm/replay.json`; never presented as a live model call.

## 5. Proxy denial and approved destination

Command: `check5.py` starts `skyshift.sever.EgressProxy` (loopback) with allowlist = the Leaseweb S3 endpoint host:port only, and range data from live published feeds; curl via `HTTPS_PROXY`.
Range provenance (fetched 14:09:29–14:09:30 UTC, 0.5 s, 19002 prefixes): AWS https://ip-ranges.amazonaws.com/ip-ranges.json; Google https://www.gstatic.com/ipranges/cloud.json; Cloudflare https://www.cloudflare.com/ips-v4 and ips-v6; Azure: synthetic committed fixture (the weekly Azure ServiceTags URL could not be resolved).
Time: 14:09:29–14:09:31 UTC. Exit code: 0.
Measured: `s3.eu-central-1.amazonaws.com:443` -> deny "published cloud range (aws)", curl exit 7; `monitoring.eu-central-1.amazonaws.com:443` -> deny "published cloud range (aws)", curl exit 7; Leaseweb S3 endpoint:443 -> allow "approved host and port", HTTP 400 from the S3 service (reachable, unauthenticated request). All three decisions logged in proxy events.
Result: **PASS**. Limitation: enforces only clients honouring HTTPS_PROXY (no firewall); Azure ranges are synthetic. Fallback: none needed.

## Human decision

go-with-fallback (4/5). Checks 1, 2, 3 (init/validate) and 5 PASS; check 4 NOT RUN, labelled replay fallback tested. Authenticated tofu plan FAIL recorded as a limitation (customer ID missing). Signed: Miguel Jordão, 2026-11-20 14:20 UTC.

## Addendum: check 4 re-run live (after the signed decision)

Agent `claude-3`, 14:19–14:24 UTC. The signed decision above is unchanged; this records a later live measurement for human review.
Server: the supplied "GPU server" has **no GPU** (`lspci`: only a virtual Cirrus Logic VGA; 0 NVIDIA devices), so no NVIDIA driver was installed. It is a 48 vCPU AMD EPYC VM with 188 GiB RAM, Ubuntu 26.04.1. Ollama 0.40.16 installed, bound to 127.0.0.1:11434 only (systemd drop-in); reached from the demo VM through an SSH local-forward tunnel (no public model port).
Models (CPU inference): `mistral:7b` -> both requests timed out at the client's 20 s bound, labelled replay served: FAIL for latency. `qwen2.5:3b` -> `skyshift.llm.complete` live, three resources (aws_instance, aws_security_group, aws_s3_bucket) mapped to enumerated target types, schema-valid (client validator and jsonschema): 9.42 s first request, then 6.31 s, 6.62 s, 6.22 s; mode=live, status=ok, errors=[].
Result: **check 4 PASS with `qwen2.5:3b` on CPU** (latency < 10 s; the first request after model load was close to the bound). Limitation: small 3B model on CPU, not GPU, not Mistral 7B; Leaseweb-hosted in the EU per supplied server, jurisdiction not independently verified. Fallback unchanged: labelled replay.

## Addendum: authenticated tofu plan (after the signed decision)

Agent `claude-3`, 15:03–15:05 UTC. Signed decision unchanged. With the Leaseweb customer ID (supplied by Miguel) as OS_USER_DOMAIN_NAME/OS_PROJECT_DOMAIN_NAME: Keystone v3 password auth HTTP 201, catalog includes compute/image/network, region eu-west-3-az1. `openstack flavor list` and `openstack image list` succeeded (smallest flavor lsw.c7a.medium, image Ubuntu 24.04). `tofu plan` with `openstack_images_image_v2` and `openstack_compute_flavor_v2` data sources read both objects from the API (exit 0, "Plan: 1 to add", 15:04:26–15:04:27 UTC). Result: **authenticated plan PASS**; no apply.
