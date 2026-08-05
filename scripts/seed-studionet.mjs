import { readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { createAccount, createClient } from "genlayer-js";
import { studionet } from "genlayer-js/chains";
import { ExecutionResult, TransactionStatus } from "genlayer-js/types";

const root = process.cwd();
const deploymentPath = resolve(root, "deployments/studionet.json");
const deployment = JSON.parse(readFileSync(deploymentPath, "utf8"));
const env = readFileSync(resolve(root, "../.env"), "utf8");
const key = env
  .split(/\r?\n/)
  .find((line) => line.startsWith("GENLAYER_PRIVATE_KEY_0="))
  ?.slice("GENLAYER_PRIVATE_KEY_0=".length)
  .trim();
if (!key) throw new Error("GENLAYER_PRIVATE_KEY_0 is missing");

const account = createAccount(key);
if (deployment.deployer.toLowerCase() !== account.address.toLowerCase()) {
  throw new Error("StudioNet deployment was not created by account 0");
}
const client = createClient({ chain: studionet, account });
const atto = (gen) => BigInt(gen) * 10n ** 18n;
const projectDeadline = 1_814_313_600;
const milestoneDue = 1_806_451_200;
const votingEndsAt = Math.floor(Date.now() / 1000) + 14 * 86_400;
const pilots = [
  {
    title: "ProofFund Settlement Lab",
    category: "Protocol",
    summary: "Exercise evidence-gated capital with delayed release and atomic appeals.",
    description: "A public deployment program for testing ProofFund's complete settlement lifecycle: tranche funding, milestone coverage, validator review, a defined appeal window, atomic dispute outcomes, and proportional recovery of unreleased escrow.",
    website: "https://docs.genlayer.com/",
    image: "https://images.unsplash.com/photo-1484417894907-623942c8ee29",
    goal: 3,
    funding: 3,
    initialTrancheGoal: 1,
    milestone: "Publish the settlement specification",
    criteria: "A public HTTPS source documents the approval hold, both atomic appeal directions, milestone coverage rules, proportional refunds, and the deployed contract interface.",
  },
  {
    title: "Open Source Security Atlas",
    category: "Infrastructure",
    summary: "Map reproducible security signals across critical open-source dependencies.",
    description: "An independent security research program that publishes inspectable dependency cohorts, source provenance, risk methodology, and structured exports so maintainers can reproduce every conclusion rather than trust an opaque score.",
    website: "https://owasp.org/www-project-dependency-check/",
    image: "https://images.unsplash.com/photo-1558494949-ef010cbdcc31",
    goal: 5,
    funding: 1,
    milestone: "Publish the first dependency cohort",
    criteria: "A public HTTPS report lists at least twenty dependencies, explains the risk method, links each source, and provides machine-readable export instructions.",
  },
  {
    title: "Civic Data Commons",
    category: "Public goods",
    summary: "Turn fragmented civic datasets into a documented and reusable public catalog.",
    description: "A public-data initiative organizing civic datasets around provenance, licensing, refresh cadence, ownership, and practical reuse. Every record is designed for independent inspection and correction through durable public evidence.",
    website: "https://data.gov/",
    image: "https://images.unsplash.com/photo-1451187580459-43490279c0fa",
    goal: 6,
    funding: 1,
    milestone: "Release the catalog foundation",
    criteria: "A public catalog contains at least thirty records with source URL, owner, license, refresh cadence, topic, and a documented correction process.",
  },
  {
    title: "Climate Sensor Registry",
    category: "Climate",
    summary: "Create an auditable registry for community-operated environmental sensors.",
    description: "A community infrastructure effort documenting sensor operators, calibration status, geographic coverage, measurement types, and public data endpoints so validator review can distinguish live infrastructure from unsupported claims.",
    website: "https://wmo.int/",
    image: "https://images.unsplash.com/photo-1569163139394-de4e4f43e4e5",
    goal: 4,
    funding: 1,
    milestone: "Verify the first sensor network",
    criteria: "A public registry documents fifteen sensors with region, measurement type, calibration date, operator, data URL, and evidence of recent readings.",
  },
  {
    title: "Accessible Web Toolkit",
    category: "Open source",
    summary: "Ship practical accessibility checks that teams can run before deployment.",
    description: "An open-source delivery program translating established accessibility guidance into runnable checks, documented fixtures, and reproducible reports suitable for independent review by product teams and validators.",
    website: "https://www.w3.org/WAI/standards-guidelines/wcag/",
    image: "https://images.unsplash.com/photo-1559028012-481c04fa702d",
    goal: 7,
    funding: 1,
    milestone: "Deliver the runnable audit toolkit",
    criteria: "A public repository includes setup instructions, ten runnable accessibility checks, passing and failing fixtures, a license, and generated sample output.",
  },
  {
    title: "Reproducibility Index",
    category: "Research",
    summary: "Score whether public research artifacts can be independently reproduced.",
    description: "A research infrastructure project evaluating code, datasets, environment definitions, and execution instructions against a published rubric, with every score linked to evidence that others can independently repeat.",
    website: "https://www.cos.io/products/osf",
    image: "https://images.unsplash.com/photo-1532187863486-abf9dbad1b69",
    goal: 8,
    funding: 1,
    milestone: "Publish the first reproducibility cohort",
    criteria: "A public report evaluates twelve research artifacts using a published rubric, links all sources, explains exclusions, and includes structured results.",
  },
  {
    title: "Local Journalism Archive",
    category: "Public goods",
    summary: "Preserve public-interest local reporting with durable and searchable provenance.",
    description: "An archival program organizing local reporting into a searchable public collection that records original sources, publication context, capture status, topic metadata, and a transparent correction path.",
    website: "https://archive.org/",
    image: "https://images.unsplash.com/photo-1504711434969-e33886168f5c",
    goal: 6,
    funding: 1,
    milestone: "Open the first indexed collection",
    criteria: "A public collection exposes fifty indexed records with source, publication date, topic, archive status, searchable metadata, and correction instructions.",
  },
  {
    title: "Open Credential Map",
    category: "Education",
    summary: "Make public learning credentials comparable through transparent mappings.",
    description: "An education initiative mapping public credentials to skills, issuing requirements, evidence standards, and primary sources without relying on opaque rankings or unverifiable institutional claims.",
    website: "https://www.unesco.org/en/education",
    image: "https://images.unsplash.com/photo-1523050854058-8df90110c9f1",
    goal: 5,
    funding: 0,
    milestone: "Release the initial credential map",
    criteria: "A public map includes twenty credentials with issuer, source URL, requirements, mapped skills, evidence standard, and an explanation of methodology.",
  },
  {
    title: "Humanitarian Logistics Monitor",
    category: "Infrastructure",
    summary: "Track public logistics signals for evidence-based aid coordination.",
    description: "A humanitarian data program assembling public logistics and access signals into a documented operational view focused on source attribution, freshness, uncertainty, and explicit limitations.",
    website: "https://data.humdata.org/",
    image: "https://images.unsplash.com/photo-1593113598332-cd288d649433",
    goal: 9,
    funding: 0,
    milestone: "Publish the operational data view",
    criteria: "A public dashboard documents three logistics signal categories, identifies each source and refresh time, shows uncertainty, and provides a downloadable snapshot.",
  },
];

const plannedFunding = pilots.reduce((total, item) => total + item.funding, 0);
if (plannedFunding > 9) throw new Error("Seed plan exceeds the 9 GEN limit");
deployment.seed ??= { transactions: {}, status: "PENDING", totalFundedWei: "0" };
deployment.seed.transactions ??= {};
const save = () =>
  writeFileSync(deploymentPath, `${JSON.stringify(deployment, null, 2)}\n`);

const isBusy = (error) =>
  /Server busy|rate limit|-32429|-32028|429/i.test(
    String(error?.details || error?.message || error),
  );
async function submit(stage, functionName, args, value = 0n) {
  if (deployment.seed.transactions[stage]?.status === "ACCEPTED") return;
  let hash;
  for (let attempt = 1; attempt <= 30; attempt += 1) {
    try {
      hash = await client.writeContract({
        address: deployment.contractAddress,
        functionName,
        args,
        value,
        leaderOnly: false,
      });
      break;
    } catch (error) {
      if (!isBusy(error) || attempt === 30) throw error;
      await new Promise((resolveDelay) => setTimeout(resolveDelay, 5_000));
    }
  }
  deployment.seed.transactions[stage] = {
    hash,
    status: "SUBMITTED",
    submittedAt: new Date().toISOString(),
  };
  save();
  console.log(`${stage}: ${hash}`);
  const receipt = await client.waitForTransactionReceipt({
    hash,
    status: TransactionStatus.ACCEPTED,
    retries: 120,
    interval: 3_000,
  });
  const leader = receipt.consensus_data?.leader_receipt?.[0];
  const succeeded =
    receipt.txExecutionResultName === ExecutionResult.FINISHED_WITH_RETURN ||
    leader?.execution_result === "SUCCESS";
  if (!succeeded) {
    throw new Error(`${stage} failed: ${JSON.stringify(receipt, (_key, item) =>
      typeof item === "bigint" ? item.toString() : item,
    )}`);
  }
  deployment.seed.transactions[stage].status = "ACCEPTED";
  deployment.seed.transactions[stage].acceptedAt = new Date().toISOString();
  save();
}

for (let index = 0; index < pilots.length; index += 1) {
  const pilot = pilots[index];
  const projectId = `PF-${String(index + 1).padStart(4, "0")}`;
  const initialGoal = pilot.initialTrancheGoal ?? pilot.goal;
  await submit(`project-${projectId}`, "create_project", [
    pilot.title,
    pilot.category,
    pilot.summary,
    pilot.description,
    pilot.website,
    pilot.image,
    atto(pilot.goal),
    projectDeadline,
    "Open accountability tranche",
    atto(initialGoal),
    projectDeadline - 2_592_000,
  ]);
  if (initialGoal < pilot.goal) {
    await submit(`tranche-${projectId}-T2`, "add_funding_tranche", [
      projectId,
      "Verified delivery tranche",
      atto(pilot.goal - initialGoal),
      projectDeadline,
    ]);
  }
  await submit(`milestone-${projectId}-M1`, "add_milestone", [
    projectId,
    pilot.milestone,
    pilot.criteria,
    atto(pilot.goal),
    milestoneDue,
  ]);
}

for (let index = 0; index < pilots.length; index += 1) {
  const pilot = pilots[index];
  if (pilot.funding === 0) continue;
  const projectId = `PF-${String(index + 1).padStart(4, "0")}`;
  if (pilot.initialTrancheGoal && pilot.funding > pilot.initialTrancheGoal) {
    await submit(`fund-${projectId}-T1`, "fund_tranche", [projectId, `${projectId}-T1`], atto(pilot.initialTrancheGoal));
    await submit(`fund-${projectId}-T2`, "fund_tranche", [projectId, `${projectId}-T2`], atto(pilot.funding - pilot.initialTrancheGoal));
  } else {
    await submit(`fund-${projectId}-T1`, "fund_tranche", [projectId, `${projectId}-T1`], atto(pilot.funding));
  }
}

const proposals = [
  ["PF-0001", "Publish monthly escrow reconciliation", "Signal support for a monthly public reconciliation of funded, pending, disputed, refundable, and released escrow across every active ProofFund project."],
  ["PF-0002", "Prioritize machine-readable findings", "Signal that the security atlas should publish stable JSON exports alongside every human-readable dependency cohort and methodology revision."],
  ["PF-0003", "Adopt a seven-day correction target", "Signal support for acknowledging and triaging documented civic catalog corrections within seven calendar days of public submission."],
];
for (let index = 0; index < proposals.length; index += 1) {
  const [projectId, title, description] = proposals[index];
  const proposalId = `${projectId}-G1`;
  await submit(`proposal-${proposalId}`, "create_proposal", [
    projectId,
    title,
    description,
    "SIGNAL",
    0n,
    votingEndsAt,
  ]);
  await submit(`vote-${proposalId}`, "vote_proposal", [proposalId, true]);
}

deployment.seed.status = "ACCEPTED";
deployment.seed.transactionCount = Object.keys(deployment.seed.transactions).length;
deployment.seed.totalFundedWei = atto(plannedFunding).toString();
deployment.seed.totalFundedGen = String(plannedFunding);
deployment.seed.completedAt = new Date().toISOString();
save();
console.log(JSON.stringify(deployment.seed, null, 2));
