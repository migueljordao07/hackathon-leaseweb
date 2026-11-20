# ExitProof — AI-powered Cloud Portability & Migration Assurance

> For **DevOps engineers and IT teams in European companies**, we help **identify cloud dependencies, validate application compatibility across cloud providers and prevent future vendor lock-in** using **AI-assisted dependency analysis, application-specific compatibility test generation, intelligent failure diagnosis and fix recommendations**, improving **migration readiness, application portability and the reliability of cloud migrations**.

**Proposed by:** [Team members] · **Status:** Exploring  
**Theme:** Migration & sovereignty

## 1. Problem and user

- **Who encounters this, and when?**

  DevOps engineers, cloud architects and software development teams in European companies that want to migrate applications from hyperscalers such as AWS, Microsoft Azure or Google Cloud to alternative providers, particularly European cloud providers.

  The problem also affects teams developing new cloud applications that want to avoid introducing dependencies that make future migrations difficult.

- **What goes wrong today?**

  Applications often depend on provider-specific APIs, services, configurations and features. Even when another provider offers an apparently equivalent service, it may not support all the functionalities used by the original application.

  For example, a Python application using AWS S3 might rely on an API operation that is not fully supported by a target provider. The application may therefore fail after migration, even though both providers advertise S3 compatibility.

  These problems can be discovered late, increasing migration costs, development effort and the risk of service disruption.

- **Current workaround:**

  Manual code and infrastructure analysis, provider documentation, manually written compatibility tests, local emulators, staging environments and trial-and-error configuration changes.

  Teams often need to combine several separate tools and significant engineering effort to assess whether their applications will work correctly in another environment.

- **Evidence:**

  - The Hackathon brief explicitly identifies European dependence on hyperscalers and the difficulty of migrating to sovereign alternatives as priority areas.
  - AWS recommends behavioural and automated testing before and after application replatforming, comparing results between source and target environments.
  - Scaleway Object Storage supports a subset of the Amazon S3 API. Its official API documentation currently lists `GetBucketNotification` as in development, illustrating how API compatibility does not guarantee complete feature equivalence.
  - Existing tools such as LocalStack, Azure Migrate and CloudExit already cover parts of this problem.
  - **Untested assumption:** Smaller European development teams lack an accessible, integrated solution for generating application-specific portability tests, diagnosing compatibility failures and maintaining portability continuously.

  Sources:
  - [Hackathon challenge](../00_Context/challenge-and-guidelines.md)
  - [AWS migration testing guidance](https://docs.aws.amazon.com/prescriptive-guidance/latest/migration-replatforming-cots-applications/testing-validating-application.html)
  - [Scaleway supported S3 API operations](https://www.scaleway.com/en/docs/object-storage/api-cli/using-api-call-list/)
  - [LocalStack](https://www.localstack.cloud/)
  - [CloudExit](https://github.com/escapecloud/cloudexit)
  - [Azure Migrate](https://learn.microsoft.com/en-us/azure/migrate/)

## 2. Proposed solution and AI contribution

- **User workflow:**

  1. **Input:** The user uploads a Python application or repository and relevant infrastructure/configuration files. The initial version supports Python applications using the boto3 S3 SDK.
  2. **Dependency discovery:** The platform analyses the code and identifies cloud-specific services, API calls, configuration dependencies and relevant application operations.
  3. **Application Portability Contract:** The system creates a structured description of the application's cloud requirements and the functionalities that must remain operational after migration.
  4. **Target selection:** The user selects an alternative provider, initially focusing on S3-compatible object storage, such as Scaleway Object Storage.
  5. **Compatibility assessment:** The platform compares the application's requirements with a verified catalogue of the target provider's documented capabilities.
  6. **AI test planning:** AI generates an application-specific test plan based on the identified dependencies and available compatibility information.
  7. **Test execution:** The same predefined integration tests are executed against the source and target environments.
  8. **AI diagnosis:** The platform analyses failed tests, error logs and provider documentation to identify probable causes.
  9. **Fix proposal:** AI generates a suggested code or configuration change. The user reviews and approves it before application.
  10. **Revalidation:** The platform applies approved changes in an isolated environment and executes the tests again.
  11. **Portability Passport:** The platform generates a report containing tested functionalities, results, unresolved issues, fixes and evidence.
  12. **Continuous portability:** On subsequent code changes, the platform checks whether new provider-specific dependencies have been introduced and whether the portability contract remains satisfied.

- **What AI adds:**

  - Interpret application code and dependency information to understand which cloud functionalities are actually used.
  - Generate application-specific compatibility test plans instead of relying exclusively on generic predefined tests.
  - Compare application requirements with a curated, verifiable provider capability catalogue.
  - Explain why certain operations may fail in the target environment.
  - Analyse logs and identify probable causes of compatibility issues.
  - Generate proposed configuration and code changes to resolve identified problems.
  - Analyse new code changes and identify dependencies that may reduce future portability.

  AI-generated test plans and corrections must be validated before execution. The system must not invent provider capabilities or claim that an application is compatible without successful independent tests.

- **Simple baseline:**

  A deterministic Python scanner, manually maintained provider compatibility mappings and predefined integration tests.

  This approach can identify known dependencies and verify known application operations, but requires developers to manually interpret unexpected failures, select appropriate tests and implement corrections.

- **Action boundary:**

  The platform can read user-provided source code, configuration files and test logs. It can generate test plans, recommend changes and execute predefined tests in isolated environments.

  AI-generated changes require human approval before application. Only predefined and validated tests may be executed automatically.

  No production systems will be modified. Demo credentials will be restricted to dedicated test environments and buckets. Secrets must be excluded from source files, logs and model prompts.

## 3. Existing alternatives and difference

| Alternative or workaround | What it already solves | Our specific difference |
|---|---|---|
| [LocalStack](https://www.localstack.cloud/) | Emulates cloud services locally and supports testing and debugging by developers and AI agents. | ExitProof focuses on comparing application-specific behaviour across different provider implementations and documenting portability evidence. |
| [CloudExit / EscapeCloud](https://github.com/escapecloud/cloudexit) | Assesses cloud exit readiness, inventories resources and costs, evaluates lock-in risk and suggests alternative technologies. | ExitProof intends to validate actual application functionality in a selected target environment rather than only assessing infrastructure and migration readiness. |
| [Azure Migrate](https://learn.microsoft.com/en-us/azure/migrate/) | Assesses workload readiness, dependencies and compatibility for migration to Azure. | ExitProof aims to remain provider-neutral and focus on application behaviour across hyperscalers and European alternatives. |
| Manual interoperability testing | Compares API support and verifies application behaviour through manually developed tests. | ExitProof combines automated dependency discovery, AI-assisted test planning, failure diagnosis and continuous portability checks. |

**Why would this user choose our approach?**

ExitProof combines application-specific compatibility analysis, AI-assisted testing and independently verified results in a provider-neutral workflow, helping companies understand what will work, what needs adaptation and what may prevent future migrations.

**Differentiation hypothesis:** The proposed value lies in connecting application-level dependency discovery, automatically selected compatibility tests, AI-assisted remediation and a continuously updated Portability Passport, with particular attention to European cloud alternatives. Existing products already cover several individual capabilities, so the exact competitive gap requires further research and validation.

## 4. Smallest working demo

**Demo story:**

A European company uses a Python application that stores documents and images through AWS S3. It wants to move to a European alternative, such as Scaleway Object Storage, but is uncertain whether all the application's storage operations will remain functional.

ExitProof analyses the application, identifies its S3 dependencies, generates a test plan, identifies a migration blocker, proposes a correction and verifies the result.

1. **Before:**

   - Upload a sample Python application using boto3.
   - Identify its S3 operations, such as uploading, downloading, listing and deleting objects.
   - Show the application's initial configuration and dependencies.
   - Run the predefined tests against the source environment.
   - Run them against the target environment and show a deliberately introduced configuration mismatch or documented API compatibility limitation.

2. **Intervention:**

   - ExitProof analyses the application and generates an Application Portability Contract.
   - AI selects relevant tests from a validated test catalogue.
   - The test runner executes the same tests against both environments.
   - AI analyses failed test results, error messages and provider capability documentation.
   - AI proposes a correction or adaptation, displaying the relevant configuration or code changes.
   - The user reviews and approves the proposed change.

3. **After:**

   - Re-execute the same tests against the target environment.
   - Verify successful supported operations.
   - Compare files using SHA-256 checksums to verify data integrity.
   - Generate the Portability Passport, identifying passed tests, unresolved compatibility issues and untested capabilities.
   - Demonstrate that a new provider-specific dependency introduced into the code is detected during a subsequent portability check.

   The demo must distinguish local emulation from real cloud provider testing. A successful local test does not prove compatibility with a real European provider.

- **Must build:**

  1. **Dependency Scanner and Portability Contract:** Analyse a restricted set of Python/boto3 operations and create a structured application dependency profile.
  2. **AI Compatibility and Testing Engine:** Use a verified provider capability catalogue to generate a test plan, execute predefined integration tests, analyse failures and propose code/configuration adaptations.
  3. **Portability Passport and Interface:** Display dependencies, test results, AI recommendations, unresolved issues and the final portability evidence report.

- **Out of scope today:**

  - Full migration of production infrastructure or real customer data.
  - Support for all cloud providers and services.
  - Support for multiple programming languages.
  - Full infrastructure orchestration and automatic production deployment.
  - Automatic execution of arbitrary AI-generated code.
  - Complete performance, security and disaster-recovery testing.
  - Full GitHub integration and continuous monitoring infrastructure.
  - Guaranteed compatibility or legal certification of cloud sovereignty.

- **Success metric:**

  - Correctly identify all predefined S3 operations in the sample application.
  - Generate a test plan covering all selected supported operations.
  - Detect the deliberately introduced configuration mismatch or known compatibility limitation.
  - Produce an AI-generated diagnosis and a valid correction proposal.
  - Target: achieve 100% passing results for the selected supported test suite after the approved correction.
  - Verify file integrity through SHA-256 checksums.
  - Ensure that unsupported or unverified capabilities remain explicitly flagged.
  - Demonstrate that a newly introduced provider-specific dependency is detected in a subsequent scan.

  These are proposed targets, not measured results. A passing test suite only validates the selected application behaviours and environments.

- **Failure case:**

  - Unsupported programming pattern or cloud operation → flag as unknown and request manual review.
  - Missing source code or configuration → indicate that the dependency analysis is incomplete.
  - Unknown provider capability → do not assume compatibility; request verification.
  - Incorrect AI-generated correction → require human approval and reject changes that fail validation.
  - Target provider unavailable → report the failure and use the clearly labelled local fallback.
  - AI service unavailable → use deterministic dependency mappings and predefined test plans.
  - Credentials missing or invalid → do not execute remote tests; provide analysis-only results.

- **Demo fallback:**

  Use a reproducible local environment with:
  - Moto server as a simulated S3 source endpoint.
  - SeaweedFS as an independent S3-compatible target endpoint.
  - Synthetic application code, configuration and test data.
  - A predefined compatibility issue and reproducible test logs.

  If external AI inference is unavailable, use a predefined AI response clearly labelled as replayed output.

  This fallback demonstrates the test orchestration and portability workflow, not a real AWS-to-European-provider migration.

## 5. Feasibility on the supplied Linux VM

| Dependency | Proposed approach | Available / Unverified / Blocked |
|---|---|---|
| Data and telemetry | Synthetic Python application, source code, configuration, predefined integration tests and real logs from isolated test environments. Optionally use AWS and Scaleway test buckets if authorised access is available. | Available to create; cloud credentials unverified |
| Model and inference | External LLM API for compatibility reasoning, test planning, error diagnosis and proposed fixes. JSON-structured responses and deterministic fallback. | Unverified: API access, credentials, latency, budget and internet connectivity |
| Infrastructure and permissions | Linux VM running Python and Docker. Isolated Moto and SeaweedFS environments. Optional remote testing using restricted cloud credentials. | VM provided; Docker permissions, RAM, CPU and network access unverified |
| Libraries and integrations | Python, AST (standard library), boto3, pytest, Moto, SeaweedFS, FastAPI or Streamlit. Apache-2.0 and other approved open-source dependencies, with licences verified before publication. | Libraries publicly available; exact versions and dependency licences to verify |

**Rough effort and split:**

- Backend and scanner: identify boto3 calls, configuration dependencies and generate the Portability Contract.
- Compatibility and AI: maintain the provider capability catalogue, generate test plans and analyse failures.
- Testing and infrastructure: configure source and target endpoints, run integration tests and calculate checksums.
- Interface and reporting: present the dependency map, AI recommendations, test results and Portability Passport.
- Integration and presentation: connect the components, validate the workflow and prepare the five-minute pitch.

**Hardest integration:** Connecting static code analysis, reliable provider compatibility information, AI-generated plans and actual test execution in a consistent end-to-end workflow.

**Biggest blocker:** Reliable access to the target environment and the ability to reproduce a meaningful compatibility issue. External AI API access and VM Docker permissions are additional dependencies.

Keep credentials out of the repository and model prompts. Confirm API access separately from chat subscriptions or VM login access.

## 6. Fastest validation

- **Riskiest assumption:**

  That a restricted Python/boto3 application can be analysed sufficiently to identify relevant cloud operations and that AI can use real compatibility information and test failures to produce useful corrections that improve independently verified results.

- **Quick experiment:**

  1. Build a small Python application using boto3 with upload, download, list and delete operations.
  2. Create a Moto S3 server and a SeaweedFS S3 endpoint.
  3. Run the same integration tests against both endpoints.
  4. Introduce a known configuration mismatch in the target connection.
  5. Use Python AST to identify the application's S3 operations.
  6. Generate a structured Portability Contract.
  7. Give the contract, error logs and relevant compatibility information to an LLM.
  8. Check whether the LLM identifies the issue and proposes a valid configuration change.
  9. Apply the approved change and re-run the same tests.
  10. Generate a basic Portability Passport.

  If a real Scaleway test account and restricted credentials are available, repeat the test against Scaleway Object Storage and use its published API support matrix to identify any genuine provider-specific blockers.

- **