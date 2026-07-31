import assert from "node:assert/strict";
import { readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { createClient } from "genlayer-js";
import { testnetBradbury } from "genlayer-js/chains";

const root = process.cwd();
const deployment = JSON.parse(
  readFileSync(resolve(root, "deployments/bradbury.json"), "utf8"),
);
const source = JSON.parse(
  readFileSync(resolve(root, "deployments/live-state-studionet.json"), "utf8"),
);
const client = createClient({ chain: testnetBradbury });
const read = (functionName, args = []) =>
  client.readContract({
    address: deployment.contractAddress,
    functionName,
    args,
    jsonSafeReturn: true,
  });

const projects = await read("get_projects");
assert.equal(projects.length, 9, "expected 9 Bradbury projects");
for (const expected of source.projects) {
  const actual = projects.find((item) => item.id === expected.id);
  assert.ok(actual, `${expected.id} is missing`);
  for (const key of [
    "title",
    "category",
    "summary",
    "description",
    "website_url",
    "image_url",
    "funding_goal",
    "funded_amount",
    "released_amount",
    "milestone_budget",
    "milestone_count",
    "backer_count",
    "status",
    "deadline",
    "tranche_budget",
    "tranche_count",
    "proposal_count",
  ]) {
    assert.equal(actual[key], expected[key], `${expected.id}.${key} differs`);
  }
}

for (const project of source.projects) {
  assert.deepEqual(
    await read("get_milestones", [project.id]),
    source.milestones.filter((item) => item.project_id === project.id),
    `${project.id} milestones differ`,
  );
  assert.deepEqual(
    await read("get_disputes", [project.id]),
    source.disputes.filter((item) => item.project_id === project.id),
    `${project.id} disputes differ`,
  );
  assert.deepEqual(
    await read("get_tranches", [project.id]),
    source.tranches.filter((item) => item.project_id === project.id),
    `${project.id} tranches differ`,
  );
}

for (const expected of source.proposals) {
  const [actual] = await read("get_proposals", [expected.project_id]);
  for (const key of [
    "id",
    "project_id",
    "proposer",
    "title",
    "description",
    "action",
    "action_value",
    "yes_votes",
    "no_votes",
    "snapshot_weight",
    "quorum",
    "voting_ends_at",
    "status",
    "finalized_at",
  ]) {
    assert.equal(actual[key], expected[key], `${expected.id}.${key} differs`);
  }
}

for (const account of source.accounts) {
  assert.deepEqual(
    await read("get_profile", [account.address]),
    account.profile,
    `${account.address} profile differs`,
  );
}
for (const account of source.accounts) {
  for (const [projectId, amount] of Object.entries(account.contributions)) {
    assert.equal(
      await read("get_contribution", [projectId, account.address]),
      amount,
      `${projectId} contribution differs`,
    );
  }
  for (const [proposalId, vote] of Object.entries(account.votes)) {
    assert.equal(
      await read("get_vote", [proposalId, account.address]),
      vote,
      `${proposalId} vote differs`,
    );
  }
}

const dashboard = await read("get_dashboard");
for (const [key, value] of Object.entries(source.dashboard)) {
  assert.equal(dashboard[key], value, `dashboard.${key} differs`);
}
assert.equal(deployment.seed.transactionCount, 54);
assert.equal(deployment.seed.status, "ACCEPTED");

const verification = {
  verifiedAt: new Date().toISOString(),
  network: "Bradbury",
  chainId: 4221,
  contractAddress: deployment.contractAddress,
  deploymentTransaction: deployment.transactionHash,
  snapshotHash: deployment.migration.snapshotHash,
  transactionCount: deployment.seed.transactionCount,
  exactOperationalStateMatch: true,
  dashboard,
};
writeFileSync(
  resolve(root, "deployments/live-state-bradbury.json"),
  `${JSON.stringify(verification, null, 2)}\n`,
);
console.log(JSON.stringify(verification, null, 2));
