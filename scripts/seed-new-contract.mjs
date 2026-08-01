import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { createAccount, createClient } from "genlayer-js";
import { testnetBradbury } from "genlayer-js/chains";
import { ExecutionResult, TransactionStatus } from "genlayer-js/types";

const root = process.cwd();
const env = readFileSync(resolve(root, "../.env"), "utf8");
const key = env
  .split(/\r?\n/)
  .find((line) => line.startsWith("GENLAYER_PRIVATE_KEY_0="))
  ?.split("=")[1]
  ?.trim();
if (!key) throw new Error("GENLAYER_PRIVATE_KEY_0 is missing");

const account = createAccount(key);
const client = createClient({ chain: testnetBradbury, account });

const deployment = JSON.parse(
  readFileSync(resolve(root, "deployments/bradbury.json"), "utf8"),
);
const contractAddress = deployment.contractAddress;
console.log(`Seeding contract: ${contractAddress}`);

const now = Math.floor(Date.now() / 1000);
const ONE_DAY = 86400;
const ONE_HOUR = 3600;

async function writeContract(functionName, args, value = 0n, label = "") {
  console.log(`  → ${label || functionName}...`);

  let hash;
  for (let attempt = 1; attempt <= 20; attempt++) {
    try {
      hash = await client.writeContract({
        address: contractAddress,
        functionName,
        args,
        value,
      });
      break;
    } catch (err) {
      const msg = err?.details || err?.message || "";
      if (msg.includes("backpressure") || msg.includes("PubdataLimit")) {
        console.log(`    [attempt ${attempt}] network busy, retrying in 15s...`);
        await new Promise((r) => setTimeout(r, 15_000));
        continue;
      }
      throw err;
    }
  }
  if (!hash) throw new Error(`${functionName} failed after 20 attempts`);

  const receipt = await client.waitForTransactionReceipt({
    hash,
    status: TransactionStatus.FINALIZED,
    retries: 240,
    interval: 3_000,
  });
  const success =
    receipt.txExecutionResultName === ExecutionResult.FINISHED_WITH_RETURN ||
    receipt.consensus_data?.leader_receipt?.[0]?.execution_result === "SUCCESS";
  if (!success) {
    console.error(`    ✗ Failed: ${JSON.stringify(receipt)}`);
    throw new Error(`${functionName} failed`);
  }
  console.log(`    ✓ ${hash.slice(0, 10)}...`);
  return receipt;
}

async function readContract(functionName, args = []) {
  return await client.readContract({
    address: contractAddress,
    functionName,
    args,
    jsonSafeReturn: true,
  });
}

// Project definitions
const projects = [
  {
    title: "Open Climate Data Atlas",
    category: "Climate",
    summary: "A comprehensive, publicly accessible atlas of climate datasets with interactive visualizations and API access for researchers worldwide.",
    description: "This project builds an open-access climate data platform that aggregates satellite observations, ground station measurements, and model outputs into a unified, queryable atlas. The platform will provide interactive visualizations, standardized APIs, and downloadable datasets to accelerate climate research and public understanding of environmental change. All code and data will be released under open licenses with full documentation and reproducibility packages.",
    website_url: "https://github.com/example/climate-atlas",
    image_url: "",
    funding_goal: 5n * 10n ** 18n, // 5 GEN
    deadline: now + 90 * ONE_DAY,
    tranches: [
      { title: "Data pipeline and infrastructure", goal: 2n * 10n ** 18n, deadline: now + 30 * ONE_DAY },
      { title: "Visualization and API layer", goal: 3n * 10n ** 18n, deadline: now + 60 * ONE_DAY },
    ],
    milestones: [
      { title: "Data ingestion pipeline operational", criteria: "A working ETL pipeline that ingests at least 3 public climate datasets (NOAA, ERA5, MODIS) with automated quality checks, deduplication, and storage in a queryable format. Includes monitoring dashboards and error handling for failed ingestions.", amount: 2n * 10n ** 18n, due: now + 30 * ONE_DAY },
      { title: "Interactive atlas with public API", criteria: "A web-based interactive atlas with map visualizations, time-series charts, and filtering capabilities. A REST API with endpoints for dataset queries, metadata retrieval, and data downloads. Full API documentation with examples and a developer quickstart guide.", amount: 3n * 10n ** 18n, due: now + 60 * ONE_DAY },
    ],
  },
  {
    title: "Civic Transparency Ledger",
    category: "Governance",
    summary: "An open platform tracking municipal spending with searchable databases, trend analysis, and citizen alert systems for anomalous expenditures.",
    description: "This project creates a transparent, auditable ledger of municipal government spending that aggregates public budget data, procurement records, and expenditure reports. The platform will provide searchable databases, trend analysis tools, and automated alert systems for citizens and journalists to monitor public fund usage. All data will be cross-referenced with official government sources and released under open data licenses with full provenance tracking.",
    website_url: "https://github.com/example/civic-ledger",
    image_url: "",
    funding_goal: 3n * 10n ** 18n,
    deadline: now + 60 * ONE_DAY,
    tranches: [
      { title: "Initial development", goal: 3n * 10n ** 18n, deadline: now + 45 * ONE_DAY },
    ],
    milestones: [
      { title: "Data aggregation and search", criteria: "A system that aggregates spending data from at least 5 municipal sources with full-text search, category filtering, and date range queries. Includes data validation, deduplication, and provenance tracking showing the original source of each record.", amount: 15n * 10n ** 17n, due: now + 30 * ONE_DAY },
      { title: "Analytics and alert system", criteria: "Trend analysis dashboards showing spending patterns over time with comparative views. An automated alert system that flags anomalous expenditures (unusual amounts, new vendors, off-cycle payments) with email notifications for subscribed citizens. Public API for third-party integrations.", amount: 15n * 10n ** 17n, due: now + 45 * ONE_DAY },
    ],
  },
  {
    title: "Open Source Security Audit Toolkit",
    category: "Security",
    summary: "A comprehensive suite of automated security scanning tools for open source projects with vulnerability detection, dependency analysis, and compliance reporting.",
    description: "This project develops an integrated security audit toolkit that combines static analysis, dependency scanning, and compliance checking into a unified platform. The toolkit will provide automated vulnerability detection, software composition analysis, license compliance verification, and detailed reporting for open source maintainers. All tools will be released as open source with extensive documentation, integration guides, and examples for popular CI/CD platforms.",
    website_url: "https://github.com/example/security-toolkit",
    image_url: "",
    funding_goal: 4n * 10n ** 18n,
    deadline: now + 75 * ONE_DAY,
    tranches: [
      { title: "Core scanning engine", goal: 4n * 10n ** 18n, deadline: now + 60 * ONE_DAY },
    ],
    milestones: [
      { title: "Vulnerability scanner MVP", criteria: "A command-line tool that scans repositories for known vulnerabilities (CVEs) in dependencies, with support for npm, pip, and Go modules. Generates detailed reports with severity ratings, affected versions, and remediation guidance. Includes a test suite with sample vulnerable projects demonstrating detection capabilities.", amount: 2n * 10n ** 18n, due: now + 30 * ONE_DAY },
      { title: "Compliance and license checker", criteria: "A license compliance analyzer that identifies all dependencies and their licenses, flags incompatible license combinations, and generates compliance reports. Supports SPDX license identifiers and provides recommendations for license conflicts. Includes integration examples for GitHub Actions and GitLab CI.", amount: 2n * 10n ** 18n, due: now + 60 * ONE_DAY },
    ],
  },
  {
    title: "Decentralized Research Archive",
    category: "Research",
    summary: "A peer-to-peer archive for scientific publications with persistent identifiers, version control, and citation tracking independent of traditional publishers.",
    description: "This project builds a decentralized archive system for scientific research that operates independently of traditional publishers. The platform will provide persistent identifiers, version control for research artifacts, citation tracking, and open access to publications. Using peer-to-peer storage and blockchain-based provenance, the archive ensures long-term preservation and accessibility of scientific knowledge without centralized control or paywalls.",
    website_url: "https://github.com/example/research-archive",
    image_url: "",
    funding_goal: 6n * 10n ** 18n,
    deadline: now + 120 * ONE_DAY,
    tranches: [
      { title: "Storage and identifier layer", goal: 3n * 10n ** 18n, deadline: now + 45 * ONE_DAY },
      { title: "Discovery and citation system", goal: 3n * 10n ** 18n, deadline: now + 90 * ONE_DAY },
    ],
    milestones: [
      { title: "P2P storage with persistent IDs", criteria: "A working peer-to-peer storage system that accepts research documents (PDF, LaTeX, datasets) and assigns persistent, content-addressed identifiers. Documents are replicated across multiple nodes with availability monitoring. Includes a command-line client for uploading and retrieving documents with cryptographic verification.", amount: 3n * 10n ** 18n, due: now + 45 * ONE_DAY },
      { title: "Search and citation tracking", criteria: "A web-based discovery interface with full-text search, metadata filtering, and author profiles. A citation tracking system that monitors references between archived documents and generates citation graphs. Includes DOI-like identifier resolution and integration with existing academic search engines via OAI-PMH protocol.", amount: 3n * 10n ** 18n, due: now + 90 * ONE_DAY },
    ],
  },
  {
    title: "Public Health Data Commons",
    category: "Health",
    summary: "An open platform aggregating public health datasets with privacy-preserving analytics, epidemiological modeling tools, and policy impact tracking.",
    description: "This project creates a unified platform for public health data that aggregates epidemiological datasets, demographic statistics, and health outcome metrics from public sources. The platform will provide privacy-preserving analytics tools, epidemiological modeling capabilities, and policy impact tracking to support evidence-based public health decisions. All tools will be open source with comprehensive documentation and examples for health researchers and policy analysts.",
    website_url: "https://github.com/example/health-commons",
    image_url: "",
    funding_goal: 5n * 10n ** 18n,
    deadline: now + 100 * ONE_DAY,
    tranches: [
      { title: "Data integration layer", goal: 25n * 10n ** 17n, deadline: now + 40 * ONE_DAY },
      { title: "Analytics and modeling tools", goal: 25n * 10n ** 17n, deadline: now + 80 * ONE_DAY },
    ],
    milestones: [
      { title: "Multi-source data integration", criteria: "A system that integrates health data from at least 4 public sources (CDC, WHO, national health surveys, hospital discharge data) with standardized schemas, quality validation, and temporal alignment. Includes data lineage tracking showing the provenance of each record and automated pipelines for regular updates.", amount: 25n * 10n ** 17n, due: now + 40 * ONE_DAY },
      { title: "Privacy-preserving analytics suite", criteria: "A suite of analytics tools that support epidemiological modeling (SIR/SEIR models, contact tracing simulations) with differential privacy guarantees. Includes visualization dashboards for health metrics, trend analysis, and policy scenario modeling. All tools run locally or in secure enclaves to protect sensitive data with comprehensive documentation.", amount: 25n * 10n ** 17n, due: now + 80 * ONE_DAY },
    ],
  },
];

console.log("\n=== Seeding ProofFund with rich project data ===\n");

for (const proj of projects) {
  console.log(`\n📦 Creating project: ${proj.title}`);

  // Create project with first tranche
  const createArgs = [
    proj.title,
    proj.category,
    proj.summary,
    proj.description,
    proj.website_url,
    proj.image_url,
    proj.funding_goal,
    BigInt(proj.deadline),
    proj.tranches[0].title,
    proj.tranches[0].goal,
    BigInt(proj.tranches[0].deadline),
  ];
  await writeContract("create_project", createArgs, 0n, `Create ${proj.title}`);

  // Get project ID (should be PF-0001, PF-0002, etc.)
  const dashData = await readContract("get_dashboard");
  const projectCount = Number(dashData.project_count);
  const projectId = `PF-${String(projectCount).padStart(4, "0")}`;
  console.log(`    Project ID: ${projectId}`);

  // Add additional tranches
  for (let i = 1; i < proj.tranches.length; i++) {
    const t = proj.tranches[i];
    await writeContract(
      "add_funding_tranche",
      [projectId, t.title, t.goal, BigInt(t.deadline)],
      0n,
      `Add tranche ${i + 1}`,
    );
  }

  // Add milestones
  for (const m of proj.milestones) {
    await writeContract(
      "add_milestone",
      [projectId, m.title, m.criteria, m.amount, BigInt(m.due)],
      0n,
      `Add milestone: ${m.title}`,
    );
  }

  // Fund the project (simulate multiple backers)
  const fundingAmount = proj.funding_goal;
  await writeContract(
    "fund_project",
    [projectId],
    fundingAmount,
    `Fund ${proj.funding_goal / 10n ** 18n} GEN`,
  );

  // Submit evidence for first milestone
  const milestones = await readContract("get_milestones", [projectId]);
  if (milestones.length > 0) {
    const milestoneId = milestones[0].id;
    await writeContract(
      "submit_evidence",
      [
        projectId,
        milestoneId,
        proj.website_url,
        `Initial evidence for ${milestones[0].title}. All acceptance criteria have been addressed with comprehensive documentation, working implementations, and test coverage.`,
      ],
      0n,
      `Submit evidence for ${milestones[0].title}`,
    );
  }

  console.log(`  ✓ Project ${projectId} fully seeded`);
}

// Create some governance proposals
console.log("\n=== Creating governance proposals ===\n");

const allProjects = await readContract("get_projects");
const activeProjects = allProjects.filter((p) => p.status === "ACTIVE");

if (activeProjects.length > 0) {
  const proj = activeProjects[0];
  const votingEnd = now + 7 * ONE_DAY;

  await writeContract(
    "create_proposal",
    [
      proj.id,
      "Extend project timeline for quality assurance",
      "The current deadline may be tight for comprehensive testing and documentation. Extending by 30 days would allow more thorough validation of all deliverables and better community feedback integration.",
      "EXTEND_DEADLINE",
      BigInt(Number(proj.deadline) + 30 * ONE_DAY),
      BigInt(votingEnd),
    ],
    0n,
    "Create deadline extension proposal",
  );

  await writeContract(
    "vote_proposal",
    [`${proj.id}-G1`, true],
    0n,
    "Vote YES on proposal",
  );
}

console.log("\n=== Seed complete ===\n");
console.log("New contract address:", contractAddress);
console.log("Projects created:", projects.length);
console.log("Total funded:", projects.reduce((sum, p) => sum + p.funding_goal, 0n) / 10n ** 18n, "GEN");
console.log("\nNext steps:");
console.log("1. Wait for dispute windows to expire on approved milestones");
console.log("2. Call release_approved_milestone to release funds");
console.log("3. Frontend will show rich project data");
