import { readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { createAccount, createClient } from "genlayer-js";
import { testnetBradbury } from "genlayer-js/chains";
import { ExecutionResult, TransactionStatus } from "genlayer-js/types";

const root = process.cwd();
const deploymentPath = resolve(root, "deployments/bradbury.json");
const deployment = JSON.parse(readFileSync(deploymentPath, "utf8"));
const source = JSON.parse(
  readFileSync(resolve(root, "deployments/live-state-studionet.json"), "utf8"),
);
const manifest = JSON.parse(
  readFileSync(resolve(root, "deployments/migration-manifest.json"), "utf8"),
);
const env = readFileSync(resolve(root, "../.env"), "utf8");
const key = env
  .split(/\r?\n/)
  .find((line) => line.startsWith("GENLAYER_PRIVATE_KEY_0="))
  ?.slice("GENLAYER_PRIVATE_KEY_0=".length)
  .trim();
if (!key) throw new Error("GENLAYER_PRIVATE_KEY_0 is missing");

const account = createAccount(key);
const client = createClient({ chain: testnetBradbury, account });
deployment.seed ??= { transactions: {} };
deployment.seed.transactions ??= {};

function save() {
  writeFileSync(deploymentPath, `${JSON.stringify(deployment, null, 2)}\n`);
}

async function submitToQueue(functionName, args, value) {
  for (let attempt = 1; attempt <= 120; attempt += 1) {
    try {
      return await client.writeContract({
        address: deployment.contractAddress,
        functionName,
        args,
        value,
        leaderOnly: true,
      });
    } catch (error) {
      const message = String(error?.message || error);
      if (
        !message.includes("to consensus contract") ||
        !message.includes("was reverted") ||
        attempt === 120
      ) {
        throw error;
      }
      console.log(`queue full; retrying ${functionName} (${attempt}/120)`);
      await new Promise((resolveDelay) => setTimeout(resolveDelay, 15_000));
    }
  }
}

async function submit(stage, functionName, args, value = 0n) {
  const prior = deployment.seed.transactions[stage];
  if (prior?.status === "ACCEPTED") {
    console.log(`${stage}: already accepted`);
    return prior.hash;
  }
  const hash = await submitToQueue(functionName, args, value);
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
    retries: 360,
    interval: 3_000,
  });
  const leader = receipt.consensus_data?.leader_receipt?.[0];
  const succeeded =
    receipt.txExecutionResultName === ExecutionResult.FINISHED_WITH_RETURN ||
    leader?.execution_result === "SUCCESS";
  if (!succeeded) {
    throw new Error(
      `${stage} failed: ${JSON.stringify(receipt, (_key, item) =>
        typeof item === "bigint" ? item.toString() : item,
      )}`,
    );
  }
  deployment.seed.transactions[stage] = {
    ...deployment.seed.transactions[stage],
    status: "ACCEPTED",
    acceptedAt: new Date().toISOString(),
  };
  save();
  return hash;
}

for (const project of source.projects) {
  const tranches = source.tranches.filter(
    (item) => item.project_id === project.id,
  );
  const first = tranches[0];
  await submit(`project-${project.id}`, "create_project", [
    project.title,
    project.category,
    project.summary,
    project.description,
    project.website_url,
    project.image_url,
    BigInt(project.funding_goal),
    project.deadline,
    first.title,
    BigInt(first.goal),
    first.deadline,
  ]);
  for (const tranche of tranches.slice(1)) {
    await submit(`tranche-${tranche.id}`, "add_funding_tranche", [
      project.id,
      tranche.title,
      BigInt(tranche.goal),
      tranche.deadline,
    ]);
  }
  for (const milestone of source.milestones.filter(
    (item) => item.project_id === project.id,
  )) {
    await submit(`milestone-${milestone.id}`, "add_milestone", [
      project.id,
      milestone.title,
      milestone.criteria,
      BigInt(milestone.amount),
      milestone.due_at,
    ]);
  }
}

for (const tranche of source.tranches.filter(
  (item) => BigInt(item.funded_amount) > 0n,
)) {
  await submit(
    `fund-${tranche.id}`,
    "fund_tranche",
    [tranche.project_id, tranche.id],
    BigInt(tranche.funded_amount),
  );
}

for (const proposal of source.proposals) {
  await submit(`proposal-${proposal.id}`, "create_proposal", [
    proposal.project_id,
    proposal.title,
    proposal.description,
    proposal.action,
    BigInt(proposal.action_value),
    proposal.voting_ends_at,
  ]);
}
for (const vote of source.accounts.flatMap((item) =>
  Object.entries(item.votes)
    .filter(([, value]) => value)
    .map(([proposalId, value]) => ({ proposalId, value })),
)) {
  await submit(`vote-${vote.proposalId}`, "vote_proposal", [
    vote.proposalId,
    vote.value === "YES",
  ]);
}

await submit(
  "review-history",
  "restore_review_history",
  [manifest.reviewHistory.payload],
  300_000_000_000_000_000n,
);
deployment.seed.status = "ACCEPTED";
deployment.seed.transactionCount = Object.keys(
  deployment.seed.transactions,
).length;
deployment.seed.completedAt = new Date().toISOString();
deployment.migration = {
  ...deployment.migration,
  method: "native-actions-with-hash-locked-review-history",
  snapshotHash: manifest.snapshotHash,
  backingWei: manifest.backingWei,
  backingGen: manifest.backingGen,
  status: "ACCEPTED",
};
save();
console.log(JSON.stringify(deployment.seed, null, 2));
