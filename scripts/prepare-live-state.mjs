import { readFileSync } from "node:fs";
import { randomBytes } from "node:crypto";
import { resolve } from "node:path";
import { createAccount, createClient } from "genlayer-js";
import { studionet } from "genlayer-js/chains";
import { TransactionStatus } from "genlayer-js/types";

const CONTRACT = "0x2aB48F7021Bdda0435e5284D805235E8b16A8f18";
const MODE = process.argv[2] || "status";
const ATTO = 10n ** 18n;

const rootEnv = readFileSync(resolve(process.cwd(), "../.env"), "utf8");
const envValue = (name) =>
  rootEnv
    .split(/\r?\n/)
    .find((line) => line.startsWith(`${name}=`))
    ?.slice(name.length + 1)
    .trim();

const creatorKey = envValue("GENLAYER_PRIVATE_KEY_0");
if (!creatorKey) throw new Error("GENLAYER_PRIVATE_KEY_0 is missing");

const makeClient = (privateKey) => {
  const account = createAccount(privateKey);
  return createClient({
    chain: studionet,
    account,
  });
};

const creatorClient = makeClient(creatorKey);

const retryRpc = async (operation, attempts = 30) => {
  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    try {
      return await operation();
    } catch (error) {
      const message = String(error?.details || error?.message || error);
      if (!message.includes("Server busy") || attempt === attempts) throw error;
      await new Promise((resolveDelay) => setTimeout(resolveDelay, attempt * 2_000));
    }
  }
};

const leaderReceipt = (receipt) =>
  receipt?.consensus_data?.leader_receipt?.[0] ||
  receipt?.consensusData?.leaderReceipt?.[0];

const requireSuccess = (receipt, label) => {
  const leader = leaderReceipt(receipt);
  const result = leader?.execution_result || leader?.executionResult;
  if (result === "SUCCESS") return;

  const detail =
    leader?.genvm_result?.error_description ||
    leader?.genvm_result?.stderr ||
    leader?.result?.payload?.readable ||
    JSON.stringify(leader || receipt);
  throw new Error(`${label}: ${detail}`);
};

const send = async (client, functionName, args, value, label) => {
  const hash = await retryRpc(() =>
    client.writeContract({
      address: CONTRACT,
      functionName,
      args,
      value,
    }),
  );
  console.log(`submitted ${label} ${hash}`);
  const receipt = await client.waitForTransactionReceipt({
    hash,
    status: TransactionStatus.ACCEPTED,
    interval: 3_000,
    retries: 160,
  });
  requireSuccess(receipt, label);
  console.log(`accepted ${label}`);
  return receipt;
};

const read = (client, functionName, args = []) =>
  retryRpc(() =>
    client.readContract({
      address: CONTRACT,
      functionName,
      args,
      jsonSafeReturn: true,
    }),
  );

const snapshot = async (client = creatorClient) => {
  const projects = await read(client, "get_projects");
  const details = [];
  for (const project of projects) {
    const milestones = await read(client, "get_milestones", [project.id]);
    const disputes = await read(client, "get_disputes", [project.id]);
    const tranches = await read(client, "get_tranches", [project.id]);
    const proposals = await read(client, "get_proposals", [project.id]);
    details.push({ project, milestones, disputes, tranches, proposals });
  }
  return details;
};

const printSnapshot = (details) => {
  for (const { project, milestones, disputes, tranches, proposals } of details) {
    console.log(
      [
        project.id,
        project.status,
        `${BigInt(project.funded_amount) / ATTO}/${BigInt(project.funding_goal) / ATTO} GEN`,
        `milestones=${milestones.map((item) => `${item.id}:${item.status}`).join(",")}`,
        `tranches=${tranches.map((item) => `${item.id}:${item.status}`).join(",")}`,
        `proposals=${proposals.map((item) => `${item.id}:${item.status}`).join(",")}`,
        `openDisputes=${disputes.filter((item) => item.status === "OPEN").length}`,
      ].join(" | "),
    );
  }
};

const fundingTargets = new Map([
  ["PF-0001", "FULL"],
  ["PF-0002", "FULL"],
  ["PF-0003", 8n * ATTO],
  ["PF-0004", 6n * ATTO],
]);

const fundProjects = async () => {
  const details = await snapshot();
  for (const { project, tranches } of details) {
    if (!fundingTargets.has(project.id)) continue;
    const funded = BigInt(project.funded_amount);
    const goal = BigInt(project.funding_goal);
    const configuredTarget = fundingTargets.get(project.id);
    const target = configuredTarget === "FULL" ? goal : configuredTarget;
    if (funded >= target) continue;
    let remaining = target - funded;
    for (const tranche of tranches) {
      if (remaining <= 0n || tranche.status !== "OPEN") continue;
      const available = BigInt(tranche.goal) - BigInt(tranche.funded_amount);
      const amount = remaining < available ? remaining : available;
      if (amount <= 0n) continue;
      await send(
        creatorClient,
        "fund_tranche",
        [project.id, tranche.id],
        amount,
        `fund ${tranche.id}`,
      );
      remaining -= amount;
    }
  }
  printSnapshot(await snapshot());
};

const evidenceByProject = {
  "PF-0001": [
    {
      url: "https://github.com/GenLayerLabs/genlayer-js",
      note:
        "Public source repository documenting the implemented SDK, release history, installation path, and inspectable code used as delivery evidence.",
    },
    {
      url: "https://docs.genlayer.com/",
      note:
        "Public documentation with reproducible setup material, architecture references, and independently accessible implementation guidance.",
    },
  ],
  "PF-0002": [
    {
      url: "https://owasp.org/www-project-dependency-check/",
      note:
        "Public OWASP project page documenting the dependency analysis methodology, supported workflows, source access, and reproducible usage references.",
    },
  ],
};

const evaluateEvidence = async () => {
  let details = await snapshot();
  for (const { project, milestones } of details) {
    const evidence = evidenceByProject[project.id];
    if (!evidence || project.status !== "ACTIVE") continue;

    for (let index = 0; index < Math.min(evidence.length, milestones.length); index += 1) {
      const milestone = milestones[index];
      if (["PENDING", "NEEDS_WORK", "REJECTED"].includes(milestone.status)) {
        await send(
          creatorClient,
          "submit_evidence",
          [project.id, milestone.id, evidence[index].url, evidence[index].note],
          0n,
          `evidence ${milestone.id}`,
        );
      }
      const refreshed = await read(creatorClient, "get_milestones", [project.id]);
      const current = refreshed.find((item) => item.id === milestone.id);
      if (current?.status === "SUBMITTED") {
        await send(
          creatorClient,
          "evaluate_milestone",
          [project.id, milestone.id],
          0n,
          `evaluate ${milestone.id}`,
        );
      }
    }
  }
  details = await snapshot();
  printSnapshot(details);
};

const verifyUnavailableEvidence = async () => {
  const milestones = await read(creatorClient, "get_milestones", ["PF-0001"]);
  const milestone = milestones.find((item) => item.id === "PF-0001-M3");
  if (!milestone) throw new Error("PF-0001-M3 is missing");

  if (["PENDING", "SUBMITTED", "NEEDS_WORK", "REJECTED"].includes(milestone.status)) {
    await send(
      creatorClient,
      "submit_evidence",
      [
        "PF-0001",
        milestone.id,
        "https://test.com",
        "This intentionally unreachable page verifies that consensus records a clear rejection instead of reverting the transaction.",
      ],
      0n,
      `unavailable evidence ${milestone.id}`,
    );
  }
  await send(
    creatorClient,
    "evaluate_milestone",
    ["PF-0001", milestone.id],
    0n,
    `unavailable evaluation ${milestone.id}`,
  );
  printSnapshot(await snapshot());
};

const openDisputes = async () => {
  const challengerKey = `0x${randomBytes(32).toString("hex")}`;
  const challengerClient = makeClient(challengerKey);
  const details = await snapshot(creatorClient);
  const disputable = details.flatMap(({ project, milestones, disputes }) => {
    const hasOpenFor = new Set(
      disputes.filter((item) => item.status === "OPEN").map((item) => item.milestone_id),
    );
    return milestones
      .filter(
        (milestone) =>
          !hasOpenFor.has(milestone.id) &&
          ["APPROVED", "NEEDS_WORK", "REJECTED"].includes(milestone.status),
      )
      .map((milestone) => ({ project, milestone }));
  });

  if (!disputable.length) {
    printSnapshot(details);
    return;
  }

  const transferHash = await creatorClient.sendTransaction({
    to: challengerClient.account.address,
    value: ATTO,
  });
  console.log(`funded ephemeral challenger ${transferHash}`);

  for (let attempt = 0; attempt < 20; attempt += 1) {
    const balance = await challengerClient.getBalance({
      address: challengerClient.account.address,
    });
    if (balance >= ATTO) break;
    await new Promise((resolveDelay) => setTimeout(resolveDelay, 1_000));
  }

  for (const { project, milestone } of disputable) {
    await send(
      challengerClient,
      "open_dispute",
      [
        project.id,
        milestone.id,
        "The submitted source does not demonstrate every acceptance condition with sufficient project-specific, timestamped, and independently reproducible evidence.",
        "https://docs.genlayer.com/developers/intelligent-contracts",
      ],
      ATTO / 10n,
      `dispute ${milestone.id}`,
    );
  }
  printSnapshot(await snapshot(challengerClient));
};

const governanceSeeds = [
  {
    projectId: "PF-0001",
    title: "Publish a quarterly treasury report",
    description:
      "Signal support for a quarterly public treasury report covering funded tranches, released milestones, open disputes, and remaining protocol obligations.",
  },
  {
    projectId: "PF-0002",
    title: "Prioritize machine-readable security exports",
    description:
      "Signal that the next delivery should prioritize stable machine-readable exports with documented schemas and reproducible generation instructions.",
  },
  {
    projectId: "PF-0003",
    title: "Adopt a public correction response target",
    description:
      "Signal support for publishing and tracking a seven-day response target for documented corrections submitted to the civic data catalog.",
  },
];

const seedGovernance = async () => {
  const votingEndsAt = Math.floor(Date.now() / 1000) + 7 * 86_400;
  for (const seed of governanceSeeds) {
    const project = await read(creatorClient, "get_project", [seed.projectId]);
    if (BigInt(project.funded_amount) === 0n) continue;
    const proposals = await read(creatorClient, "get_proposals", [seed.projectId]);
    let proposal = proposals.find((item) => item.title === seed.title);
    if (!proposal) {
      await send(
        creatorClient,
        "create_proposal",
        [seed.projectId, seed.title, seed.description, "SIGNAL", 0n, votingEndsAt],
        0n,
        `proposal ${seed.projectId}`,
      );
      const updated = await read(creatorClient, "get_proposals", [seed.projectId]);
      proposal = updated.find((item) => item.title === seed.title);
    }
    if (!proposal || proposal.status !== "OPEN") continue;
    const existingVote = await read(
      creatorClient,
      "get_vote",
      [proposal.id, creatorClient.account.address],
    );
    if (!existingVote) {
      await send(
        creatorClient,
        "vote_proposal",
        [proposal.id, true],
        0n,
        `vote ${proposal.id}`,
      );
    }
  }
  printSnapshot(await snapshot());
};

if (MODE === "status") printSnapshot(await snapshot());
else if (MODE === "fund") await fundProjects();
else if (MODE === "evaluate") await evaluateEvidence();
else if (MODE === "dispute") await openDisputes();
else if (MODE === "verify-unavailable") await verifyUnavailableEvidence();
else if (MODE === "governance") await seedGovernance();
else throw new Error(`Unknown mode: ${MODE}`);
